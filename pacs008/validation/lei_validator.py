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

"""LEI (Legal Entity Identifier) validator.

Implements ISO 17442 format validation and ISO 7064 mod-97-10 checksum
verification for the 20-character GLEIF-issued LEI.

The LEI is increasingly mandatory in payments messaging: the Bank of
England has mandated LEI in CHAPS FI-to-FI transfers as part of its
RTGS Renewal Programme, the ECB and Federal Reserve are signalling
similar moves, and CPMI's February 2026 harmonisation report names
LEI as the preferred cross-border identifier.

LEI structure (ISO 17442-1:2020):

==========  ===================  =====================================
Positions    Content              Notes
==========  ===================  =====================================
1-4          LOU prefix           Local Operating Unit (alphanumeric)
5-6          Reserved             Alphanumeric (originally ``"00"``;
                                  the 2020 revision relaxed this — LOUs
                                  now use these positions at their
                                  discretion, and real-world GLEIF data
                                  rarely has ``"00"`` here)
7-18         Entity identifier    Alphanumeric, assigned by the LOU
19-20        Check digits         ISO 7064 mod-97-10, numeric
==========  ===================  =====================================

Verification algorithm:

1. Confirm the value is exactly 20 characters, all ``[A-Z0-9]``.
2. Confirm positions 19-20 are digits.
3. Convert each character to a numeric string (digits stay, ``A=10``
   through ``Z=35``).
4. Treat the concatenated digit string as a big integer.
5. The value modulo 97 must equal 1.

Note on positions 5-6:
    The original ISO 17442:2012 specification required these to be
    ``"00"``. Real-world LEIs issued before and after the 2020 revision
    routinely use other values (e.g. Apple's LEI is
    ``HWUPKR0MPOU8FGXBT394`` — positions 5-6 are ``"KR"``). This
    validator therefore does not enforce the ``"00"`` rule, matching
    GLEIF's verification reference implementation.

Example::

    >>> from pacs008.validation.lei_validator import validate_lei
    >>> is_valid, error = validate_lei("529900T8BM49AURSDO55", strict=False)
    >>> assert is_valid

References:

- ISO 17442-1:2020 — Financial services. Legal entity identifier (LEI).
- ISO 7064 — Check character systems.
- GLEIF Common Data File Format.
"""

from __future__ import annotations

from pacs008.exceptions import InvalidLEIError

# Length and position constants from ISO 17442.
_LEI_LENGTH = 20
_CHECK_DIGIT_START = 18  # positions 19-20


def validate_lei_format(lei: str) -> tuple[bool, str]:
    """Validate LEI structural form (length + character set + reserved).

    Performs everything except the mod-97-10 checksum, which is the job
    of :func:`validate_lei_checksum`.

    Args:
        lei: LEI string to validate.

    Returns:
        Tuple of ``(is_valid, error_message)``. ``error_message`` is
        empty on success.
    """
    if not isinstance(lei, str):
        return False, f"LEI must be a string; got {type(lei).__name__}"

    if len(lei) != _LEI_LENGTH:
        return (
            False,
            f"LEI must be exactly {_LEI_LENGTH} characters; "
            f"got {len(lei)}",
        )

    if not lei.isascii() or not lei.isalnum():
        return False, "LEI must be ASCII alphanumeric only"

    if lei != lei.upper():
        return False, "LEI must be uppercase"

    check_digits = lei[_CHECK_DIGIT_START:]
    if not check_digits.isdigit():
        return (
            False,
            "LEI check digits (positions 19-20) must be numeric; "
            f"got {check_digits!r}",
        )

    return True, ""


def validate_lei_checksum(lei: str) -> tuple[bool, str]:
    """Verify the ISO 7064 mod-97-10 checksum on a syntactically valid LEI.

    Assumes the input has already passed :func:`validate_lei_format`.
    Pass-through on a malformed input is undefined.

    Args:
        lei: LEI string.

    Returns:
        Tuple of ``(is_valid, error_message)``.
    """
    numeric = _lei_to_numeric(lei)
    if numeric is None:
        return False, "LEI contains non-alphanumeric characters"

    try:
        remainder = int(numeric) % 97
    except ValueError as exc:
        return False, f"Invalid numeric LEI representation: {exc}"

    if remainder != 1:
        return (
            False,
            "LEI checksum validation failed "
            f"(mod 97 = {remainder}, expected 1)",
        )

    return True, ""


def validate_lei(
    lei: str,
    field: str | None = None,
    strict: bool = True,
) -> tuple[bool, str]:
    """Validate LEI format and ISO 7064 mod-97-10 checksum.

    Args:
        lei: LEI string.
        field: Optional field name for error reporting (e.g.
            ``"debtor_lei"``).
        strict: If ``True``, raise :class:`InvalidLEIError` on failure.
            If ``False``, return a ``(False, message)`` tuple.

    Returns:
        Tuple of ``(is_valid, error_message)``. In strict mode an
        exception is raised before the tuple is returned on failure.

    Raises:
        InvalidLEIError: If ``strict=True`` and the LEI is invalid.

    Example:
        >>> # Non-strict
        >>> is_valid, error = validate_lei(
        ...     "529900T8BM49AURSDO55", strict=False
        ... )
        >>> assert is_valid
        >>>
        >>> # Strict
        >>> try:
        ...     validate_lei("INVALID")
        ... except InvalidLEIError as e:
        ...     print(f"Invalid: {e}")
    """
    is_valid, error = validate_lei_format(lei)
    if not is_valid:
        if strict:
            raise InvalidLEIError(
                message=error,
                lei=lei,
                field=field,
                reason="Invalid LEI format",
            )
        return False, error

    is_valid, error = validate_lei_checksum(lei)
    if not is_valid:
        if strict:
            raise InvalidLEIError(
                message=error,
                lei=lei,
                field=field,
                reason="Invalid LEI checksum (ISO 7064 mod-97-10)",
            )
        return False, error

    return True, ""


def validate_lei_safe(lei: str, field: str | None = None) -> bool:
    """Validate LEI returning ``True``/``False`` (never raises).

    Convenience wrapper for :func:`validate_lei` with ``strict=False``.

    Args:
        lei: LEI string.
        field: Optional field name (unused; kept for API symmetry with
            :func:`pacs008.validation.iban_validator.validate_iban_safe`).

    Returns:
        ``True`` if valid; ``False`` otherwise.
    """
    is_valid, _ = validate_lei(lei, field=field, strict=False)
    return is_valid


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

# Party prefixes whose LEI we recognise in payment-row dicts.
_PARTY_PREFIXES: tuple[str, ...] = (
    "debtor",
    "creditor",
    "debtor_agent",
    "creditor_agent",
    "ultimate_debtor",
    "ultimate_creditor",
)


class LEIValidationError:
    """A single LEI validation finding from :func:`validate_leis`."""

    __slots__ = ("row", "party", "field", "value", "reason")

    def __init__(
        self,
        row: int,
        party: str,
        field: str,
        value: str,
        reason: str,
    ) -> None:
        """Initialise a LEI finding with row, party prefix, field, value + reason."""
        self.row = row
        self.party = party
        self.field = field
        self.value = value
        self.reason = reason

    def __repr__(self) -> str:
        return (
            f"LEIValidationError(row={self.row}, party={self.party!r}, "
            f"field={self.field!r}, reason={self.reason!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LEIValidationError):
            return NotImplemented
        return (
            self.row == other.row
            and self.party == other.party
            and self.field == other.field
            and self.value == other.value
            and self.reason == other.reason
        )

    def __hash__(self) -> int:
        return hash((self.row, self.party, self.field, self.value))


def validate_leis(
    payment_data: list[dict[str, object]],
    required_parties: tuple[str, ...] | None = None,
) -> list[LEIValidationError]:
    """Validate LEI fields across a list of payment-row dicts.

    Recognises columns of the form ``{party}_lei`` where ``party`` is
    one of ``debtor``, ``creditor``, ``debtor_agent``,
    ``creditor_agent``, ``ultimate_debtor`` or ``ultimate_creditor``.

    By default, LEIs are OPTIONAL — rows without an LEI column for a
    given party are skipped silently. Pass ``required_parties`` to
    enforce presence (e.g. ``("debtor_agent", "creditor_agent")`` under
    the CHAPS scheme, where FI LEIs are mandated by the Bank of
    England).

    Args:
        payment_data: List of dictionaries representing payment rows.
        required_parties: Tuple of party prefixes whose LEI must be
            present and valid. ``None`` (the default) means all LEIs
            are optional.

    Returns:
        List of :class:`LEIValidationError` for each offending
        ``(row, party)`` pair. Empty list if everything passes.
    """
    required = required_parties or ()
    errors: list[LEIValidationError] = []

    for row_idx, row in enumerate(payment_data):
        for party in _PARTY_PREFIXES:
            field_name = f"{party}_lei"
            raw_value = row.get(field_name)

            if raw_value in (None, ""):
                if party in required:
                    errors.append(
                        LEIValidationError(
                            row=row_idx,
                            party=party,
                            field=field_name,
                            value="",
                            reason=(
                                f"{field_name} is required for this scheme "
                                "(missing or empty)"
                            ),
                        )
                    )
                continue

            value = str(raw_value)
            is_valid, error = validate_lei(
                value, field=field_name, strict=False
            )
            if not is_valid:
                errors.append(
                    LEIValidationError(
                        row=row_idx,
                        party=party,
                        field=field_name,
                        value=value,
                        reason=error,
                    )
                )

    return errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lei_to_numeric(lei: str) -> str | None:
    """Convert LEI alphanumerics to digits per ISO 7064 (A=10..Z=35).

    Returns ``None`` if any character is outside ``[A-Z0-9]``.
    """
    parts: list[str] = []
    for char in lei:
        if char.isdigit():
            parts.append(char)
        elif "A" <= char <= "Z":
            parts.append(str(ord(char) - ord("A") + 10))
        else:
            return None
    return "".join(parts)
