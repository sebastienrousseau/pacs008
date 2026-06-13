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

"""VoP (Verification of Payee) result model and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class VoPMatchResult(Enum):
    """Canonical VoP match outcomes per the EPC Rulebook."""

    MATCH = "MATCH"
    """The creditor name and IBAN match exactly."""

    CLOSE_MATCH = "CLOSE_MATCH"
    """The match is fuzzy — the PSP returned a "close match" with
    the suggested correction."""

    NO_MATCH = "NO_MATCH"
    """The IBAN does not match the supplied name. Initiation should
    be paused for confirmation."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    """VoP does not apply — e.g. corporate one-leg-out, B2B with
    explicit opt-out, or non-eurozone (pre-July-2027) traffic."""

    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    """The VoP service returned an error or timeout. EPC rulebook
    permits proceeding under specific conditions; the PSP must
    document the fallback."""


_VOP_FIELD_RESULT = "vop_result"
_VOP_FIELD_NAME_COMPARED = "vop_name_compared"
_VOP_FIELD_IBAN = "vop_iban"
_VOP_FIELD_REASON_CODE = "vop_reason_code"
_VOP_FIELD_PERFORMED_AT = "vop_performed_at"


@dataclass(frozen=True)
class VoPResult:
    """A single VoP match outcome.

    Attributes:
        result: The :class:`VoPMatchResult`.
        name_compared: The creditor name actually sent to the VoP
            service (after any canonical normalisation by the PSP).
        iban: The creditor IBAN checked.
        reason_code: Optional PSP-supplied reason code, useful for
            CLOSE_MATCH / NO_MATCH outcomes (e.g.
            ``"NAME_MISMATCH"``, ``"IBAN_INVALID"``).
        suggested_name: Optional name the VoP service returned as
            the registered holder of the IBAN. Populated on
            CLOSE_MATCH; rarely present on NO_MATCH for
            privacy/AML reasons.
        performed_at: ISO 8601 timestamp the check was performed
            at. Used by audit and fraud monitoring.
    """

    result: VoPMatchResult
    name_compared: str
    iban: str
    reason_code: str | None = None
    suggested_name: str | None = None
    performed_at: str | None = None

    def __post_init__(self) -> None:
        if self.performed_at is not None:
            # Best-effort parse just to surface obvious errors at
            # construction time; we don't reformat.
            try:
                datetime.fromisoformat(self.performed_at)
            except ValueError as exc:
                raise ValueError(
                    "performed_at must be an ISO 8601 timestamp; "
                    f"got {self.performed_at!r}"
                ) from exc

    @property
    def is_blocking(self) -> bool:
        """``True`` if the result would normally block initiation."""
        return self.result is VoPMatchResult.NO_MATCH

    @property
    def is_proceed(self) -> bool:
        """``True`` if the result permits unattended initiation."""
        return self.result in (
            VoPMatchResult.MATCH,
            VoPMatchResult.NOT_APPLICABLE,
        )


def embed_in_row(row: dict[str, Any], vop: VoPResult) -> dict[str, Any]:
    """Inject a :class:`VoPResult` into a payment-row dict.

    The result is stored under canonical column names so downstream
    code (SCT Inst profile validation, XML serialisation in v0.1.0)
    can read it back uniformly.

    Args:
        row: Existing payment row.
        vop: The result to embed.

    Returns:
        A new dict with the VoP fields populated. The input row is
        not mutated.
    """
    out = dict(row)
    out[_VOP_FIELD_RESULT] = vop.result.value
    out[_VOP_FIELD_NAME_COMPARED] = vop.name_compared
    out[_VOP_FIELD_IBAN] = vop.iban
    if vop.reason_code is not None:
        out[_VOP_FIELD_REASON_CODE] = vop.reason_code
    if vop.performed_at is not None:
        out[_VOP_FIELD_PERFORMED_AT] = vop.performed_at
    if vop.suggested_name is not None:
        out["vop_suggested_name"] = vop.suggested_name
    return out


def extract_from_row(row: dict[str, Any]) -> VoPResult | None:
    """Reverse of :func:`embed_in_row` — extract a VoP result if present.

    Returns ``None`` if no ``vop_result`` column is present.
    Raises ``ValueError`` if the result string is not a recognised
    :class:`VoPMatchResult` member.
    """
    raw = row.get(_VOP_FIELD_RESULT)
    if raw in (None, ""):
        return None

    try:
        result = VoPMatchResult(str(raw))
    except ValueError as exc:
        raise ValueError(
            f"unrecognised vop_result {raw!r}; expected one of "
            f"{[m.value for m in VoPMatchResult]}"
        ) from exc

    return VoPResult(
        result=result,
        name_compared=str(row.get(_VOP_FIELD_NAME_COMPARED) or ""),
        iban=str(row.get(_VOP_FIELD_IBAN) or ""),
        reason_code=_optional_str(row.get(_VOP_FIELD_REASON_CODE)),
        suggested_name=_optional_str(row.get("vop_suggested_name")),
        performed_at=_optional_str(row.get(_VOP_FIELD_PERFORMED_AT)),
    )


@dataclass(frozen=True)
class VoPValidationError:
    """A single VoP-related validation finding."""

    row: int
    field: str
    rule: str
    message: str


# 9 October 2025 — eurozone VoP becomes mandatory per the EPC scheme.
_VOP_EUROZONE_MANDATE_DATE = date(2025, 10, 9)


def validate_vop_results(
    payment_data: list[dict[str, Any]],
    today: date | None = None,
) -> list[VoPValidationError]:
    """Validate VoP coverage and outcomes across a payment batch.

    Args:
        payment_data: Payment-row dicts.
        today: Reference date for the mandate check. Defaults to
            :func:`datetime.date.today`. After 2025-10-09, rows
            without a VoP result are flagged. Before that date,
            missing VoP is silently allowed.

    Returns:
        List of :class:`VoPValidationError` findings.
    """
    ref = today if today is not None else date.today()
    enforce_required = ref >= _VOP_EUROZONE_MANDATE_DATE

    errors: list[VoPValidationError] = []
    for row_idx, row in enumerate(payment_data):
        try:
            result = extract_from_row(row)
        except ValueError as exc:
            errors.append(
                VoPValidationError(
                    row=row_idx,
                    field=_VOP_FIELD_RESULT,
                    rule="vop_result_unrecognised",
                    message=str(exc),
                )
            )
            continue

        if result is None:
            if enforce_required:
                errors.append(
                    VoPValidationError(
                        row=row_idx,
                        field=_VOP_FIELD_RESULT,
                        rule="vop_required",
                        message=(
                            "VoP result is mandatory for SEPA payments "
                            f"(eurozone mandate in force from "
                            f"{_VOP_EUROZONE_MANDATE_DATE.isoformat()})"
                        ),
                    )
                )
            continue

        if result.is_blocking:
            errors.append(
                VoPValidationError(
                    row=row_idx,
                    field=_VOP_FIELD_RESULT,
                    rule="vop_blocking",
                    message=(
                        f"VoP returned {result.result.value} for "
                        f"IBAN {result.iban!r}: initiation must be "
                        "paused for confirmation"
                    ),
                )
            )

    return errors


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
