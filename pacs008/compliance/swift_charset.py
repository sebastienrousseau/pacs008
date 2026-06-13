"""SWIFT character set validation and field length enforcement.

Banks reject messages not because they fail XSD validation, but because
they violate SWIFT Usage Guidelines (CBPR+, Target2). This module
prevents "silent rejections" by cleansing data before XML generation.

The SWIFT X Character Set (ISO 15022, used by CBPR+ and SEPA-EPC) allows:
  a-z A-Z 0-9 / - ? : ( ) . , ' + { } CR LF Space

The broader SWIFT Z Character Set (used by some Fedwire profiles) extends
X with the Latin-1 supplement (accented Latin characters, common symbols).

This module supports both via the ``charset`` parameter. Scheme profiles
expose a :attr:`~pacs008.profiles.base.SchemeProfile.charset` property
that picks the right one automatically.

Cleansing modes:

- ``policy="cleanse"`` (default) — transliterate non-charset characters,
  falling through explicit map → NFKD decomposition → ``anyascii`` for
  non-Latin scripts → single space as last resort. Whitespace runs are
  collapsed.
- ``policy="reject"`` — raise :class:`PaymentValidationError` on the
  first non-charset character. For institutions that prefer hard
  failure over silent cleansing.

Field length limits follow ISO 20022 pacs.008 element definitions:
  - Nm (Name): max 140 characters
  - Id (Identifiers): max 35 characters
  - Ustrd (Unstructured remittance): max 140 characters
  - IBAN: max 34 characters
  - BIC: 8 or 11 characters
  - Currency: exactly 3 characters

Example:
    >>> from pacs008.compliance import cleanse_data
    >>> raw = [{"debtor_name": "Müller & Söhne™", "msg_id": "X" * 50}]
    >>> clean = cleanse_data(raw)
    >>> clean[0]["debtor_name"]  # non-SWIFT chars replaced
    'Mueller . Soehne TM'
    >>> len(clean[0]["msg_id"])  # truncated to 35
    35
"""

import re
import unicodedata
from typing import Any, Callable, Optional

from pacs008.exceptions import PaymentValidationError

# anyascii is a ~150KB resident-memory hit at import time. Defer the
# import to first use of the non-Latin transliteration fallback —
# callers that only deal with Latin-script payments never pay the cost.
_anyascii_impl: Optional[Callable[[str], str]] = None


def _anyascii(char: str) -> str:
    """Lazy proxy for :func:`anyascii.anyascii` — imported on first use."""
    global _anyascii_impl
    if _anyascii_impl is None:
        from anyascii import anyascii as _impl

        _anyascii_impl = _impl
    return _anyascii_impl(char)


# SWIFT X Character Set (ISO 15022 / MT standard, CBPR+, SEPA-EPC).
# Characters allowed in SWIFT FIN messages.
SWIFT_X_CHARSET = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "/-?:().,'+{} \r\n"
)

# SWIFT Z Character Set — extends X with Latin-1 supplement and the
# additional ASCII printables commonly accepted by Fedwire ISO 20022
# and a handful of legacy reporting (camt.053/054) profiles.
SWIFT_Z_CHARSET: frozenset[str] = frozenset(SWIFT_X_CHARSET) | frozenset(
    # Additional ASCII printables permitted by Z.
    '!"#$%&*;<=>@[\\]^_`|~'
    # Latin-1 supplement: accented vowels and common diacritics.
    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞß"
    "àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ"
)

# ISO 20022 pacs.008 field length limits
FIELD_MAX_LENGTHS: dict[str, int] = {
    "msg_id": 35,
    "end_to_end_id": 35,
    "tx_id": 35,
    "instr_id": 35,
    "clr_sys_ref": 35,
    "uetr": 36,
    "mandate_id": 35,
    "debtor_name": 140,
    "creditor_name": 140,
    "ultimate_debtor_name": 140,
    "ultimate_creditor_name": 140,
    "debtor_account_iban": 34,
    "creditor_account_iban": 34,
    "debtor_agent_bic": 11,
    "creditor_agent_bic": 11,
    "intermediary_agent1_bic": 11,
    "intermediary_agent2_bic": 11,
    "intermediary_agent3_bic": 11,
    "prvs_instg_agt_bic": 11,
    "prvs_instg_agt1_bic": 11,
    "prvs_instg_agt2_bic": 11,
    "prvs_instg_agt3_bic": 11,
    "instg_agt_bic": 11,
    "instd_agt_bic": 11,
    "chrgs_inf_agt_bic": 11,
    "interbank_settlement_currency": 3,
    "instd_currency": 3,
    "chrgs_inf_ccy": 3,
    "charge_bearer": 4,
    "settlement_method": 4,
    "sttlm_prty": 4,
    "purpose_cd": 4,
    "instr_for_cdtr_agt_cd": 4,
    "pmt_tp_inf_svc_lvl_cd": 4,
    "pmt_tp_inf_ctgy_purp_cd": 4,
    "instr_for_cdtr_agt_inf": 140,
    "instr_for_nxt_agt_inf": 140,
    "remittance_information": 140,
    "rgltry_rptg_authrty_nm": 140,
    "rgltry_rptg_inf": 140,
    "rgltry_rptg_cd": 10,
    "rgltry_rptg_authrty_ctry": 2,
    "rgltry_rptg_dbt_cdt_rptg_ind": 4,
}

# Unicode → ASCII transliteration map for common banking characters
_TRANSLITERATION: dict[str, str] = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "Ä": "Ae",
    "Ö": "Oe",
    "Ü": "Ue",
    "á": "a",
    "à": "a",
    "â": "a",
    "ã": "a",
    "å": "a",
    "é": "e",
    "è": "e",
    "ê": "e",
    "ë": "e",
    "í": "i",
    "ì": "i",
    "î": "i",
    "ï": "i",
    "ó": "o",
    "ò": "o",
    "ô": "o",
    "õ": "o",
    "ú": "u",
    "ù": "u",
    "û": "u",
    "ñ": "n",
    "ç": "c",
    "Á": "A",
    "À": "A",
    "Â": "A",
    "Ã": "A",
    "Å": "A",
    "É": "E",
    "È": "E",
    "Ê": "E",
    "Ë": "E",
    "Í": "I",
    "Ì": "I",
    "Î": "I",
    "Ï": "I",
    "Ó": "O",
    "Ò": "O",
    "Ô": "O",
    "Õ": "O",
    "Ú": "U",
    "Ù": "U",
    "Û": "U",
    "Ñ": "N",
    "Ç": "C",
    "æ": "ae",
    "Æ": "AE",
    "ø": "o",
    "Ø": "O",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "™": ".",
    "©": ".",
    "®": ".",
    "&": ".",
    "@": ".",
    "#": ".",
    "!": ".",
    ";": ".",
    "=": ".",
    "*": ".",
    "~": ".",
    "[": "(",
    "]": ")",
    "{": "(",
    "}": ")",
    "\\": "/",
    "|": "/",
    "^": ".",
    "_": "-",
    '"': "'",
    "`": "'",
}


class ComplianceViolation:
    """Represents a single SWIFT compliance violation."""

    def __init__(
        self,
        field: str,
        violation_type: str,
        original_value: str,
        corrected_value: Optional[str] = None,
        message: str = "",
    ) -> None:
        """Initialise a violation record with field/type/values."""
        self.field = field
        self.violation_type = violation_type
        self.original_value = original_value
        self.corrected_value = corrected_value
        self.message = message

    def __repr__(self) -> str:
        return (
            f"ComplianceViolation(field={self.field!r}, "
            f"type={self.violation_type!r})"
        )


class ComplianceReport:
    """Aggregated report of all compliance violations found and corrected."""

    def __init__(self) -> None:
        """Initialise an empty compliance report."""
        self.violations: list[ComplianceViolation] = []
        self.rows_processed: int = 0
        self.rows_modified: int = 0

    @property
    def is_clean(self) -> bool:
        """True if no violations were found."""
        return len(self.violations) == 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def add(self, violation: ComplianceViolation) -> None:
        """Append a single violation to the report."""
        self.violations.append(violation)

    def summary(self) -> str:
        """Human-readable summary."""
        if self.is_clean:
            return f"All {self.rows_processed} rows are SWIFT-compliant."
        return (
            f"{self.violation_count} violations found across "
            f"{self.rows_modified}/{self.rows_processed} rows. "
            f"All auto-corrected."
        )


def _transliterate(
    char: str,
    charset: frozenset[str] = SWIFT_X_CHARSET,
) -> str:
    """Transliterate a single character to a charset-safe equivalent.

    Resolution order:

    1. Pass-through if ``char`` is already in ``charset``.
    2. Explicit map (German/Romance accented letters).
    3. Unicode NFKD decomposition (strips combining marks).
    4. ``anyascii`` for non-Latin scripts (Cyrillic, Greek, CJK,
       Arabic, Hebrew, Devanagari, …).
    5. Single space as last resort.

    Step 4 was added in v0.0.2 — previously, characters outside the
    German/Romance explicit map fell straight through to ``"."``,
    silently destroying e.g. Cyrillic or Japanese names.
    """
    if char in charset:
        return char

    # 1) Explicit map covers the common German/Romance accented letters
    #    and a handful of symbol substitutions.
    if char in _TRANSLITERATION:
        mapped = _TRANSLITERATION[char]
        if all(c in charset for c in mapped):
            return mapped

    # 2) NFKD decomposition strips combining marks (good for stray
    #    accented characters that aren't in the explicit map).
    decomposed = unicodedata.normalize("NFKD", char)
    nfkd = "".join(c for c in decomposed if c in charset)
    if nfkd:
        return nfkd

    # 3) anyascii covers non-Latin scripts robustly. "Москва" -> "Moskva",
    #    "東京" -> "DongJing", etc. Lazily imported so Latin-only callers
    #    never pay the import cost.
    ascii_form = _anyascii(char)
    filtered = "".join(c for c in ascii_form if c in charset)
    if filtered:
        return filtered

    # 4) Last resort: single space. Period was a bad choice because it's
    #    a valid SWIFT-X character and pollutes downstream parsing of
    #    sentinel-suffixed names like "Smith Jr.".
    return " "


def validate_swift_charset(
    value: str,
    charset: frozenset[str] = SWIFT_X_CHARSET,
) -> list[tuple[int, str]]:
    """Check a string for characters outside ``charset``.

    Args:
        value: String to validate.
        charset: Target character set (default :data:`SWIFT_X_CHARSET`;
            pass :data:`SWIFT_Z_CHARSET` for Fedwire-style profiles).

    Returns:
        List of ``(position, character)`` tuples for invalid characters.
        Empty list means the string is compliant.
    """
    return [(i, c) for i, c in enumerate(value) if c not in charset]


def cleanse_string(
    value: str,
    charset: frozenset[str] = SWIFT_X_CHARSET,
    policy: str = "cleanse",
) -> str:
    """Transliterate a string to ``charset``.

    Args:
        value: Input string (may contain Unicode).
        charset: Target character set (default :data:`SWIFT_X_CHARSET`).
        policy: ``"cleanse"`` (default) transliterates non-charset
            characters following the resolution order in
            :func:`_transliterate`. ``"reject"`` raises
            :class:`pacs008.exceptions.PaymentValidationError` on the
            first non-charset character — for institutions that prefer
            hard failure over silent cleansing.

    Returns:
        Charset-safe string. Whitespace runs of two or more spaces are
        collapsed to a single space.

    Raises:
        PaymentValidationError: If ``policy="reject"`` and any
            character is outside ``charset``.
        ValueError: If ``policy`` is not ``"cleanse"`` or ``"reject"``.
    """
    if policy not in ("cleanse", "reject"):
        raise ValueError(
            f"policy must be 'cleanse' or 'reject'; got {policy!r}"
        )

    if policy == "reject":
        for i, char in enumerate(value):
            if char not in charset:
                raise PaymentValidationError(
                    f"Position {i}: character {char!r} "
                    f"(U+{ord(char):04X}) is outside the target "
                    f"character set"
                )
        return value

    cleansed = "".join(_transliterate(c, charset) for c in value)
    # Collapse runs of horizontal whitespace (don't touch CR/LF).
    return re.sub(r"  +", " ", cleansed)


def enforce_field_lengths(
    row: dict[str, Any],
    max_lengths: Optional[dict[str, int]] = None,
) -> tuple[dict[str, Any], list[ComplianceViolation]]:
    """Truncate fields that exceed ISO 20022 maximum lengths.

    Args:
        row: Payment data dictionary.
        max_lengths: Custom max lengths. Defaults to ISO 20022 pacs.008 limits.

    Returns:
        Tuple of (corrected_row, list_of_violations).
    """
    lengths = max_lengths or FIELD_MAX_LENGTHS
    violations: list[ComplianceViolation] = []
    corrected = dict(row)

    for field, max_len in lengths.items():
        value = corrected.get(field)
        if value is None:
            continue
        str_value = str(value)
        if len(str_value) > max_len:
            truncated = str_value[:max_len]
            violations.append(
                ComplianceViolation(
                    field=field,
                    violation_type="field_length",
                    original_value=str_value,
                    corrected_value=truncated,
                    message=(
                        f"Truncated from {len(str_value)} to "
                        f"{max_len} characters"
                    ),
                )
            )
            corrected[field] = truncated

    return corrected, violations


# Fields that contain free-text and need charset cleansing
_TEXT_FIELDS = {
    "debtor_name",
    "creditor_name",
    "ultimate_debtor_name",
    "ultimate_creditor_name",
    "remittance_information",
    "instr_for_cdtr_agt_inf",
    "instr_for_nxt_agt_inf",
    "rgltry_rptg_authrty_nm",
    "rgltry_rptg_inf",
}


def cleanse_data(
    data: list[dict[str, Any]],
    enforce_lengths: bool = True,
    cleanse_charset: bool = True,
    charset: frozenset[str] = SWIFT_X_CHARSET,
    policy: str = "cleanse",
) -> list[dict[str, Any]]:
    """Cleanse payment data for SWIFT compliance.

    Applies two passes:

    1. Character-set cleansing (transliterate non-charset chars in text
       fields).
    2. Field-length enforcement (truncate to ISO 20022 limits).

    Args:
        data: List of payment data dictionaries.
        enforce_lengths: Whether to truncate oversized fields.
        cleanse_charset: Whether to transliterate non-charset characters.
        charset: Target character set. Defaults to :data:`SWIFT_X_CHARSET`
            (used by CBPR+ and SEPA-EPC). Pass :data:`SWIFT_Z_CHARSET`
            for Fedwire-style profiles. Scheme profiles expose the
            right charset via their ``charset`` property.
        policy: ``"cleanse"`` to transliterate (default); ``"reject"``
            to raise :class:`PaymentValidationError` on any non-charset
            character.

    Returns:
        Cleansed data ready for XML generation.
    """
    cleansed: list[dict[str, Any]] = []

    for row in data:
        corrected = dict(row)

        # Pass 1: Charset cleansing on text fields
        if cleanse_charset:
            for field in _TEXT_FIELDS:
                value = corrected.get(field)
                if value and isinstance(value, str):
                    corrected[field] = cleanse_string(
                        value, charset=charset, policy=policy
                    )

        # Pass 2: Field length enforcement
        if enforce_lengths:
            corrected, _ = enforce_field_lengths(corrected)

        cleansed.append(corrected)

    return cleansed


def cleanse_data_with_report(
    data: list[dict[str, Any]],
    enforce_lengths: bool = True,
    cleanse_charset: bool = True,
    charset: frozenset[str] = SWIFT_X_CHARSET,
    policy: str = "cleanse",
) -> tuple[list[dict[str, Any]], ComplianceReport]:
    """Cleanse payment data and return a detailed compliance report.

    Same as :func:`cleanse_data` but also returns a
    :class:`ComplianceReport` capturing every violation found and
    corrected.

    Args:
        data: List of payment data dictionaries.
        enforce_lengths: Whether to truncate oversized fields.
        cleanse_charset: Whether to transliterate non-charset characters.
        charset: Target character set.
        policy: ``"cleanse"`` or ``"reject"`` (see :func:`cleanse_string`).

    Returns:
        Tuple of ``(cleansed_data, compliance_report)``.
    """
    report = ComplianceReport()
    report.rows_processed = len(data)
    cleansed: list[dict[str, Any]] = []

    for row in data:
        corrected = dict(row)
        row_modified = False

        # Pass 1: Charset cleansing
        if cleanse_charset:
            for field in _TEXT_FIELDS:
                value = corrected.get(field)
                if value and isinstance(value, str):
                    cleaned = cleanse_string(
                        value, charset=charset, policy=policy
                    )
                    if cleaned != value:
                        report.add(
                            ComplianceViolation(
                                field=field,
                                violation_type="charset",
                                original_value=value,
                                corrected_value=cleaned,
                                message="Non-SWIFT characters replaced",
                            )
                        )
                        corrected[field] = cleaned
                        row_modified = True

        # Pass 2: Field length enforcement
        if enforce_lengths:
            corrected, length_violations = enforce_field_lengths(corrected)
            if length_violations:
                report.violations.extend(length_violations)
                row_modified = True

        if row_modified:
            report.rows_modified += 1

        cleansed.append(corrected)

    return cleansed, report
