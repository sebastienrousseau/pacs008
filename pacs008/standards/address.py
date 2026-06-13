# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ISO 20022 ``PostalAddress`` model and the November 2026 cliff tooling.

This module exists to address the **largest near-term operational risk**
for any pacs.008 user: on 14 November 2026, fully unstructured postal
addresses are decommissioned across SWIFT CBPR+, HVPS+, TARGET2 RTGS,
CHAPS, Fedwire and Lynx. After that date, every cross-border or
high-value payment with an unstructured-only postal address is rejected
at the rail.

Three address forms are recognised:

- **Structured** — ``TwnNm`` + ``Ctry`` plus structured detail
  (e.g. ``StrtNm``, ``BldgNb``, ``PstCd``). No ``AdrLine``.
- **Hybrid** — ``TwnNm`` + ``Ctry`` plus 1 or 2 ``AdrLine`` lines
  carrying remaining free-form text. This is the form CBPR+ UG2026
  permits as the minimum bar.
- **Unstructured** — ``AdrLine`` only, no ``TwnNm`` or ``Ctry``.
  Rejected by all major schemes from 14 November 2026.

Public surface:

- :class:`PostalAddress` — the ISO 20022 ``PostalAddress27`` element.
- :class:`AddressClassification` — enum returned by ``classify()``.
- :class:`AddressPolicy` — what's allowed under a given scheme/policy.
- :func:`from_unstructured` — country-aware converter that *attempts* to
  upgrade unstructured legacy address lines to hybrid form. Marked
  experimental — banks should audit the output.
- :func:`validate_addresses` — pipeline helper that scans a list of
  payment-row dicts for known address-field prefixes and emits
  validation errors.

References:

- ISO 20022 ``PostalAddress27`` complex type.
- SWIFT CBPR+ UG2026 (rulebook in force 14 November 2026).
- SWIFT HVPS+ UG2026 collection (Swift, due December 2026).
- ECB T2-0170 — *Upgrade of T2 messages to ISO MR 2026* (October 2025).
- Bank of England — *Mandating ISO 20022 enhanced data in CHAPS*.
- Federal Reserve — *Fedwire ISO 20022 Implementation Center*.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

# Cliff date — 14 November 2026 across SWIFT CBPR+, HVPS+, T2 RTGS,
# CHAPS, Fedwire, Lynx. Fedwire's specific cutover is 16 November 2026
# but the SWIFT date is the binding global deadline.
NOV_2026_CLIFF: date = date(2026, 11, 14)


class AddressClassification(Enum):
    """ISO 20022 / SWIFT CBPR+ UG2026 address classification."""

    UNSTRUCTURED = "unstructured"
    HYBRID = "hybrid"
    STRUCTURED = "structured"


class AddressPolicy(Enum):
    """Validation policy for postal addresses.

    Used by :meth:`PostalAddress.validate` and :func:`validate_addresses`
    to decide whether a given classification is acceptable.
    """

    UNSTRUCTURED_OK = "unstructured_ok"
    """Permits any classification. Generic / pre-cliff default."""

    HYBRID_OR_STRUCTURED = "hybrid_or_structured"
    """Rejects ``UNSTRUCTURED``. The November 14, 2026 cliff default for
    CBPR+, HVPS+, T2 RTGS, CHAPS, Fedwire and Lynx."""

    STRUCTURED_ONLY = "structured_only"
    """Requires full structured form (``TwnNm`` + ``Ctry`` + no
    ``AdrLine``). Strictest option — used by some HVPS+ scheme variants
    and by jurisdictions enforcing the November 2027 structured-remit
    deadline early."""


class Severity(Enum):
    """Severity of an address validation finding."""

    BLOCK = "block"
    """Reject the payment — the rail will not accept it."""

    WARN = "warn"
    """Accept but flag for review — will be rejected after a future
    cliff date."""

    INFO = "info"
    """Informational; no action required."""


# ISO 20022 PostalAddress27 max-length constants (per the message
# definition). These are the *base* maxima; scheme profiles may tighten
# them further.
_MAX_DEPT = 70
_MAX_SUB_DEPT = 70
_MAX_STRT_NM = 70
_MAX_BLDG_NB = 16
_MAX_BLDG_NM = 35
_MAX_FLR = 70
_MAX_PST_BX = 16
_MAX_ROOM = 70
_MAX_PST_CD = 16
_MAX_TWN_NM = 35
_MAX_TWN_LCTN_NM = 35
_MAX_DSTRCT_NM = 35
_MAX_CTRY_SUB_DVSN = 35
_MAX_ADR_LINE = 70
_MAX_ADR_LINE_COUNT = 7
_MAX_HYBRID_ADR_LINE_COUNT = 2  # CBPR+ UG2026 cap on hybrid AdrLine


_STRUCTURED_FIELD_NAMES: tuple[str, ...] = (
    "dept",
    "sub_dept",
    "strt_nm",
    "bldg_nb",
    "bldg_nm",
    "flr",
    "pst_bx",
    "room",
    "pst_cd",
    "twn_nm",
    "twn_lctn_nm",
    "dstrct_nm",
    "ctry_sub_dvsn",
    "ctry",
)


@dataclass(frozen=True)
class PostalAddress:
    """ISO 20022 ``PostalAddress27`` element.

    All fields are optional per the schema. Validity for a given scheme
    is determined by :meth:`classify` together with
    :meth:`validate`. Field names use snake_case translations of the
    ISO 20022 XML element names (``StrtNm`` → ``strt_nm``, etc.).
    """

    dept: str | None = None
    sub_dept: str | None = None
    strt_nm: str | None = None
    bldg_nb: str | None = None
    bldg_nm: str | None = None
    flr: str | None = None
    pst_bx: str | None = None
    room: str | None = None
    pst_cd: str | None = None
    twn_nm: str | None = None
    twn_lctn_nm: str | None = None
    dstrct_nm: str | None = None
    ctry_sub_dvsn: str | None = None
    ctry: str | None = None
    adr_line: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.ctry is not None:
            if not _is_iso_3166_1_alpha_2(self.ctry):
                raise ValueError(
                    "ctry must be ISO 3166-1 alpha-2 (e.g. 'GB', 'US'); "
                    f"got {self.ctry!r}"
                )

        # Coerce list/iterable AdrLine input to tuple for hashability.
        if not isinstance(self.adr_line, tuple):
            object.__setattr__(self, "adr_line", tuple(self.adr_line))

        if len(self.adr_line) > _MAX_ADR_LINE_COUNT:
            raise ValueError(
                f"adr_line permits up to {_MAX_ADR_LINE_COUNT} occurrences; "
                f"got {len(self.adr_line)}"
            )

        for i, line in enumerate(self.adr_line):
            if not isinstance(line, str):
                raise TypeError(
                    f"adr_line[{i}] must be str; got {type(line).__name__}"
                )
            if len(line) > _MAX_ADR_LINE:
                raise ValueError(
                    f"adr_line[{i}] exceeds {_MAX_ADR_LINE}-char max "
                    f"({len(line)} chars)"
                )

        # Per-field max-length checks.
        _check_max(self.dept, _MAX_DEPT, "dept")
        _check_max(self.sub_dept, _MAX_SUB_DEPT, "sub_dept")
        _check_max(self.strt_nm, _MAX_STRT_NM, "strt_nm")
        _check_max(self.bldg_nb, _MAX_BLDG_NB, "bldg_nb")
        _check_max(self.bldg_nm, _MAX_BLDG_NM, "bldg_nm")
        _check_max(self.flr, _MAX_FLR, "flr")
        _check_max(self.pst_bx, _MAX_PST_BX, "pst_bx")
        _check_max(self.room, _MAX_ROOM, "room")
        _check_max(self.pst_cd, _MAX_PST_CD, "pst_cd")
        _check_max(self.twn_nm, _MAX_TWN_NM, "twn_nm")
        _check_max(self.twn_lctn_nm, _MAX_TWN_LCTN_NM, "twn_lctn_nm")
        _check_max(self.dstrct_nm, _MAX_DSTRCT_NM, "dstrct_nm")
        _check_max(self.ctry_sub_dvsn, _MAX_CTRY_SUB_DVSN, "ctry_sub_dvsn")

    @property
    def has_structured_fields(self) -> bool:
        """``True`` if any structured field is populated."""
        return any(
            getattr(self, name) is not None for name in _STRUCTURED_FIELD_NAMES
        )

    def classify(self) -> AddressClassification:
        """Return the address's classification per CBPR+ UG2026.

        - ``STRUCTURED`` — ``twn_nm`` + ``ctry`` present **and** at least
          one other structured field, **and** zero ``adr_line``.
        - ``HYBRID`` — ``twn_nm`` + ``ctry`` present and 1..2
          ``adr_line``.
        - ``UNSTRUCTURED`` — everything else (typically ``adr_line``
          only, no ``twn_nm``/``ctry``).
        """
        has_twn_ctry = self.twn_nm is not None and self.ctry is not None
        n_adr_line = len(self.adr_line)

        if has_twn_ctry and n_adr_line == 0:
            return AddressClassification.STRUCTURED
        if has_twn_ctry and 1 <= n_adr_line <= _MAX_HYBRID_ADR_LINE_COUNT:
            return AddressClassification.HYBRID
        return AddressClassification.UNSTRUCTURED

    def is_structured(self) -> bool:
        """Return True iff :meth:`classify` is :attr:`AddressClassification.STRUCTURED`."""
        return self.classify() is AddressClassification.STRUCTURED

    def is_hybrid(self) -> bool:
        """Return True iff :meth:`classify` is :attr:`AddressClassification.HYBRID`."""
        return self.classify() is AddressClassification.HYBRID

    def is_unstructured(self) -> bool:
        """Return True iff :meth:`classify` is :attr:`AddressClassification.UNSTRUCTURED`."""
        return self.classify() is AddressClassification.UNSTRUCTURED

    def validate(
        self,
        policy: AddressPolicy,
        today: date | None = None,
    ) -> str | None:
        """Validate against ``policy``.

        Returns ``None`` if the address is acceptable, otherwise a
        human-readable rejection reason. ``today`` is the reference date
        used to phrase cliff-related errors; defaults to
        :func:`datetime.date.today`.
        """
        classification = self.classify()
        ref_date = today if today is not None else date.today()

        if policy is AddressPolicy.UNSTRUCTURED_OK:
            return None

        if policy is AddressPolicy.STRUCTURED_ONLY:
            if classification is AddressClassification.STRUCTURED:
                return None
            return (
                "STRUCTURED_ONLY policy requires twn_nm + ctry plus other "
                "structured fields and no adr_line; "
                f"got {classification.value}"
            )

        if policy is AddressPolicy.HYBRID_OR_STRUCTURED:
            if classification is AddressClassification.UNSTRUCTURED:
                cliff_phrase = (
                    "in force from "
                    if ref_date < NOV_2026_CLIFF
                    else "in force since "
                )
                return (
                    "HYBRID_OR_STRUCTURED policy rejects unstructured "
                    "address; twn_nm and ctry are required (SWIFT CBPR+ "
                    f"UG2026, {cliff_phrase}"
                    f"{NOV_2026_CLIFF.isoformat()})"
                )
            return None

        # Unknown policy — be permissive so a forward-compatible policy
        # value never blocks a payment by accident.
        return None


# ---------------------------------------------------------------------------
# Country-aware unstructured -> hybrid conversion
# ---------------------------------------------------------------------------


_UK_POSTCODE = re.compile(
    r"\b([A-Z]{1,2}[0-9][A-Z0-9]?)\s*([0-9][A-Z]{2})\b",
    re.IGNORECASE,
)
_DE_POSTCODE = re.compile(r"\b(\d{5})\s+([^\d]{2,})")
_FR_POSTCODE = re.compile(r"\b(\d{5})\s+([^\d]{2,})")
_US_STATE_ZIP = re.compile(
    r"\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b",
)
_JP_POSTCODE = re.compile(r"(?:〒\s*)?(\d{3}-\d{4})\b")

_US_STATES: frozenset[str] = frozenset(
    {
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    }
)


def from_unstructured(
    adr_lines: Sequence[str],
    country_hint: str,
) -> PostalAddress:
    """Convert legacy unstructured address lines to a hybrid form.

    **Experimental.** Country-aware heuristics for ``GB``, ``US``,
    ``DE``, ``FR`` and ``JP``. For any other country, the input lines
    pass through with the country hint applied and the last line
    promoted to ``twn_nm`` as a best-effort guess. Banks should audit
    the conversion before submitting downstream — keep both the
    original and the derived address in your audit trail.

    Args:
        adr_lines: Original address lines from legacy data (empty
            strings and whitespace-only lines are skipped).
        country_hint: ISO 3166-1 alpha-2 country code (e.g. ``"GB"``).

    Returns:
        A :class:`PostalAddress` in hybrid form (``twn_nm`` + ``ctry``
        + up to 2 ``adr_line`` entries). May classify as
        ``UNSTRUCTURED`` if the input is too sparse to identify a town.

    Raises:
        ValueError: if ``country_hint`` is not a valid ISO 3166-1
            alpha-2 code.
    """
    if not _is_iso_3166_1_alpha_2(country_hint):
        raise ValueError(
            "country_hint must be ISO 3166-1 alpha-2 (e.g. 'GB', 'US'); "
            f"got {country_hint!r}"
        )

    cleaned = [line.strip() for line in adr_lines if line and line.strip()]
    if not cleaned:
        return PostalAddress(ctry=country_hint)

    handlers = {
        "GB": _from_unstructured_gb,
        "US": _from_unstructured_us,
        "DE": _from_unstructured_de,
        "FR": _from_unstructured_fr,
        "JP": _from_unstructured_jp,
    }
    handler = handlers.get(country_hint, _from_unstructured_fallback)
    return handler(cleaned, country_hint)


def _from_unstructured_gb(lines: list[str], country: str) -> PostalAddress:
    """UK heuristic: find UK postcode, take preceding/same-line text as town."""
    pst_cd: str | None = None
    twn_nm: str | None = None
    remaining: list[str] = []

    for i, line in enumerate(lines):
        match = _UK_POSTCODE.search(line)
        if match:
            pst_cd = f"{match.group(1).upper()} {match.group(2).upper()}"
            same_line_rest = (
                line[: match.start()] + line[match.end() :]
            ).strip(" ,;")
            if same_line_rest:
                twn_nm = same_line_rest
                remaining = [ln for j, ln in enumerate(lines) if j != i]
            elif i > 0:
                twn_nm = lines[i - 1]
                remaining = [
                    ln for j, ln in enumerate(lines) if j != i and j != i - 1
                ]
            else:
                remaining = lines[i + 1 :]
            break

    if pst_cd is None:
        twn_nm = lines[-1]
        remaining = lines[:-1]

    return PostalAddress(
        twn_nm=_clip(twn_nm, _MAX_TWN_NM),
        pst_cd=_clip(pst_cd, _MAX_PST_CD),
        ctry=country,
        adr_line=_pack_adr_lines(remaining),
    )


def _from_unstructured_us(lines: list[str], country: str) -> PostalAddress:
    """US heuristic: find 'STATE ZIP' anchor, take preceding chunk as town."""
    pst_cd: str | None = None
    twn_nm: str | None = None
    ctry_sub_dvsn: str | None = None
    remaining: list[str] = []

    for i, line in enumerate(lines):
        match = _US_STATE_ZIP.search(line)
        if match and match.group(1) in _US_STATES:
            ctry_sub_dvsn = match.group(1)
            pst_cd = match.group(2)
            before = line[: match.start()].rstrip(" ,;")
            if before:
                # e.g. "Cambridge, MA 02139" -> town = "Cambridge"
                town_candidate = before.split(",")[-1].strip()
                if town_candidate:
                    twn_nm = town_candidate
                    rest_of_line = ",".join(before.split(",")[:-1]).strip()
                    line_remainder = [rest_of_line] if rest_of_line else []
                    remaining = [
                        ln for j, ln in enumerate(lines) if j != i
                    ] + line_remainder
                else:
                    remaining = [ln for j, ln in enumerate(lines) if j != i]
            elif i > 0:
                twn_nm = lines[i - 1]
                remaining = [
                    ln for j, ln in enumerate(lines) if j != i and j != i - 1
                ]
            else:
                remaining = lines[i + 1 :]
            break

    if pst_cd is None:
        twn_nm = lines[-1]
        remaining = lines[:-1]

    return PostalAddress(
        twn_nm=_clip(twn_nm, _MAX_TWN_NM),
        pst_cd=_clip(pst_cd, _MAX_PST_CD),
        ctry_sub_dvsn=_clip(ctry_sub_dvsn, _MAX_CTRY_SUB_DVSN),
        ctry=country,
        adr_line=_pack_adr_lines(remaining),
    )


def _from_unstructured_de(lines: list[str], country: str) -> PostalAddress:
    """DE heuristic: 5-digit PLZ followed by Ort on the same line."""
    return _from_unstructured_continental(lines, country, _DE_POSTCODE)


def _from_unstructured_fr(lines: list[str], country: str) -> PostalAddress:
    """FR heuristic: 5-digit code postal followed by Ville on the same line."""
    return _from_unstructured_continental(lines, country, _FR_POSTCODE)


def _from_unstructured_continental(
    lines: list[str],
    country: str,
    pattern: re.Pattern[str],
) -> PostalAddress:
    """Shared DE/FR heuristic (and friends): '<5 digits> <town name>'."""
    pst_cd: str | None = None
    twn_nm: str | None = None
    remaining: list[str] = []

    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            pst_cd = match.group(1)
            twn_nm = match.group(2).strip()
            remaining = [ln for j, ln in enumerate(lines) if j != i]
            break

    if pst_cd is None:
        twn_nm = lines[-1]
        remaining = lines[:-1]

    return PostalAddress(
        twn_nm=_clip(twn_nm, _MAX_TWN_NM),
        pst_cd=_clip(pst_cd, _MAX_PST_CD),
        ctry=country,
        adr_line=_pack_adr_lines(remaining),
    )


def _from_unstructured_jp(lines: list[str], country: str) -> PostalAddress:
    """JP heuristic: '〒NNN-NNNN' postcode anchor; rest treated as town."""
    pst_cd: str | None = None
    twn_nm: str | None = None
    remaining: list[str] = []

    for i, line in enumerate(lines):
        match = _JP_POSTCODE.search(line)
        if match:
            pst_cd = match.group(1)
            same_line_rest = (
                line[: match.start()] + line[match.end() :]
            ).strip(" ,;")
            if same_line_rest:
                twn_nm = same_line_rest
                remaining = [ln for j, ln in enumerate(lines) if j != i]
            elif i + 1 < len(lines):
                twn_nm = lines[i + 1]
                remaining = [
                    ln for j, ln in enumerate(lines) if j != i and j != i + 1
                ]
            else:
                remaining = lines[:i]
            break

    if pst_cd is None:
        twn_nm = lines[-1]
        remaining = lines[:-1]

    return PostalAddress(
        twn_nm=_clip(twn_nm, _MAX_TWN_NM),
        pst_cd=_clip(pst_cd, _MAX_PST_CD),
        ctry=country,
        adr_line=_pack_adr_lines(remaining),
    )


def _from_unstructured_fallback(
    lines: list[str], country: str
) -> PostalAddress:
    """Best-effort fallback for countries without dedicated heuristics."""
    twn_nm = lines[-1] if lines else None
    remaining = lines[:-1] if twn_nm else []
    return PostalAddress(
        twn_nm=_clip(twn_nm, _MAX_TWN_NM),
        ctry=country,
        adr_line=_pack_adr_lines(remaining),
    )


# ---------------------------------------------------------------------------
# Pipeline validator
# ---------------------------------------------------------------------------


# Recognised address-field prefixes in payment-row dicts. Each prefix
# corresponds to a party whose ``PstlAdr`` appears in pacs.008 messages.
_PARTY_PREFIXES: tuple[str, ...] = (
    "debtor",
    "creditor",
    "debtor_agent",
    "creditor_agent",
    "ultimate_debtor",
    "ultimate_creditor",
)

# Snake-case suffixes (column names) for each PostalAddress field. The
# tuple ordering matches PostalAddress's field definitions.
_ADDRESS_SUFFIXES: tuple[str, ...] = (
    "dept",
    "sub_dept",
    "strt_nm",
    "bldg_nb",
    "bldg_nm",
    "flr",
    "pst_bx",
    "room",
    "pst_cd",
    "twn_nm",
    "twn_lctn_nm",
    "dstrct_nm",
    "ctry_sub_dvsn",
    "ctry",
)


@dataclass(frozen=True)
class AddressValidationError:
    """A single address validation finding."""

    row: int
    """Zero-based index into the input payment_data list."""

    party: str
    """Party prefix the address belongs to (e.g. ``"debtor"``)."""

    severity: Severity
    """Severity of the finding."""

    message: str
    """Human-readable description, suitable for CLI/API surface."""

    classification: AddressClassification
    """Classification of the offending address."""


def validate_addresses(
    payment_data: Sequence[dict[str, Any]],
    policy: AddressPolicy,
    today: date | None = None,
) -> list[AddressValidationError]:
    """Validate addresses across a list of payment-row dicts.

    Recognises columns of the form ``{party}_address_{field}`` where
    ``party`` is one of ``debtor``, ``creditor``, ``debtor_agent``,
    ``creditor_agent``, ``ultimate_debtor``, ``ultimate_creditor`` and
    ``field`` is one of the snake_case ``PostalAddress`` fields
    (``strt_nm``, ``twn_nm``, ``ctry``, …) or ``adr_line_0`` through
    ``adr_line_6``.

    Rows where a party has no recognised address columns are skipped
    (no address to validate).

    Args:
        payment_data: List of dictionaries representing payment rows.
        policy: Address policy to enforce.
        today: Reference date for cliff-related error wording (defaults
            to :func:`datetime.date.today`).

    Returns:
        A list of :class:`AddressValidationError`, one per offending
        ``(row, party)`` pair. Empty list if everything passes.
    """
    errors: list[AddressValidationError] = []

    for row_idx, row in enumerate(payment_data):
        for party in _PARTY_PREFIXES:
            address = _extract_party_address(row, party)
            if address is None:
                continue
            reason = address.validate(policy, today=today)
            if reason is None:
                continue
            errors.append(
                AddressValidationError(
                    row=row_idx,
                    party=party,
                    severity=Severity.BLOCK,
                    message=reason,
                    classification=address.classify(),
                )
            )

    return errors


def _extract_party_address(
    row: dict[str, Any], party_prefix: str
) -> PostalAddress | None:
    """Extract a PostalAddress for ``party_prefix`` from a row dict.

    Returns ``None`` if no recognised address columns are present for
    this party (so the validator skips parties whose address wasn't
    supplied).
    """
    fields: dict[str, Any] = {}

    for suffix in _ADDRESS_SUFFIXES:
        key = f"{party_prefix}_address_{suffix}"
        value = row.get(key)
        if value not in (None, ""):
            fields[suffix] = str(value)

    adr_lines: list[str] = []
    for i in range(_MAX_ADR_LINE_COUNT):
        key = f"{party_prefix}_address_adr_line_{i}"
        value = row.get(key)
        if value not in (None, ""):
            adr_lines.append(str(value))

    if not fields and not adr_lines:
        return None

    return PostalAddress(adr_line=tuple(adr_lines), **fields)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_iso_3166_1_alpha_2(value: str) -> bool:
    return value in _ISO_3166_1_ALPHA_2


# ISO 3166-1 alpha-2 country codes (as of 2025-12, with active codes and
# user-assigned exceptions excluded). Source: ISO 3166 Maintenance Agency.
_ISO_3166_1_ALPHA_2: frozenset[str] = frozenset(
    {
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    }
)


def _check_max(value: str | None, maximum: int, name: str) -> None:
    if value is not None and len(value) > maximum:
        raise ValueError(
            f"{name} exceeds {maximum}-char ISO 20022 max "
            f"({len(value)} chars)"
        )


def _clip(value: str | None, maximum: int) -> str | None:
    if value is None:
        return None
    return value[:maximum]


def _pack_adr_lines(remaining: Sequence[str]) -> tuple[str, ...]:
    """Pack remaining lines into the hybrid ``AdrLine`` cap (≤2 lines)."""
    cleaned = [line.strip() for line in remaining if line and line.strip()]
    return tuple(
        line[:_MAX_ADR_LINE] for line in cleaned[:_MAX_HYBRID_ADR_LINE_COUNT]
    )
