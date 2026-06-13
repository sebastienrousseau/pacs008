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

"""Tests for the LEI (Legal Entity Identifier) validator."""

from __future__ import annotations

import pytest

from pacs008.exceptions import InvalidLEIError
from pacs008.validation.lei_validator import (
    LEIValidationError,
    validate_lei,
    validate_lei_checksum,
    validate_lei_format,
    validate_lei_safe,
    validate_leis,
)

# Real, publicly-published GLEIF LEIs (issuer + entity verifiable at
# search.gleif.org). These act as a fixture set for the validator.
# Picked to span LOU prefixes and include digits + letters in the
# entity-specific section.
VALID_GLEIS = (
    "HWUPKR0MPOU8FGXBT394",  # Apple Inc.
    "7H6GLXDRUGQFU57RNE97",  # JPMorgan Chase Bank, NA
    "INR2EJN1ERAN0W5ZP974",  # Microsoft Corporation
    "529900T8BM49AURSDO55",  # Bloomberg LP
    "784F5XWPLTWKTBV3E584",  # Goldman Sachs Group, Inc.
    "54930043XZGB27CTOV49",  # Tesla, Inc.
    "9DJT3UXIJIZJI4WXO774",  # Bank of America Corp
    "6SHGI4ZSSLCXXQSBB395",  # Citigroup Inc.
    "PBLD0EJDB5FWOLXP3B76",  # Wells Fargo & Co
)


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------


class TestValidateLEIFormat:
    @pytest.mark.parametrize("lei", VALID_GLEIS)
    def test_real_gleif_lei_passes_format(self, lei):
        is_valid, error = validate_lei_format(lei)
        assert is_valid, error
        assert error == ""

    def test_non_string_input_rejected(self):
        is_valid, error = validate_lei_format(12345)  # type: ignore[arg-type]
        assert not is_valid
        assert "must be a string" in error

    def test_wrong_length_rejected(self):
        is_valid, error = validate_lei_format("TOOSHORT")
        assert not is_valid
        assert "exactly 20" in error

    def test_21_chars_rejected(self):
        is_valid, error = validate_lei_format("X" * 21)
        assert not is_valid
        assert "exactly 20" in error

    def test_non_ascii_rejected(self):
        # Replace one char with a non-ASCII alphanumeric
        lei = "H" + "Ñ" + "UPKR0MPOU8FGXBT394"
        is_valid, error = validate_lei_format(lei)
        assert not is_valid
        assert "ASCII" in error

    def test_special_chars_rejected(self):
        # Hyphen breaks alphanumeric
        lei = "HWUPKR0MPOU8FGXBT39-"
        is_valid, error = validate_lei_format(lei)
        assert not is_valid

    def test_lowercase_rejected(self):
        is_valid, error = validate_lei_format("hwupkr0mpou8fgxbt394")
        assert not is_valid
        assert "uppercase" in error

    def test_non_numeric_check_digits_rejected(self):
        # Replace check digits with letters
        lei = "HWUPKR0MPOU8FGXBT3AB"
        is_valid, error = validate_lei_format(lei)
        assert not is_valid
        assert "check digits" in error

    def test_format_does_not_enforce_old_00_rule(self):
        # Real LEIs do NOT have "00" at positions 5-6 — the 2020
        # revision relaxed this. Reject mode would block real GLEIF
        # data, so we must accept.
        lei = "HWUPKR0MPOU8FGXBT394"
        assert lei[4:6] == "KR"  # confirm fixture is what we think
        is_valid, _ = validate_lei_format(lei)
        assert is_valid


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


class TestValidateLEIChecksum:
    @pytest.mark.parametrize("lei", VALID_GLEIS)
    def test_real_gleif_lei_passes_checksum(self, lei):
        is_valid, error = validate_lei_checksum(lei)
        assert is_valid, error

    def test_flipped_check_digit_fails(self):
        # Take a valid LEI and bump the last digit
        lei = "HWUPKR0MPOU8FGXBT394"
        broken = lei[:-1] + ("5" if lei[-1] != "5" else "6")
        is_valid, error = validate_lei_checksum(broken)
        assert not is_valid
        assert "mod 97" in error

    def test_all_zeros_fails(self):
        # Boundary: "0" * 20 → 0 % 97 = 0, not 1
        is_valid, error = validate_lei_checksum("0" * 20)
        assert not is_valid


# ---------------------------------------------------------------------------
# Strict / non-strict entry points
# ---------------------------------------------------------------------------


class TestValidateLEI:
    @pytest.mark.parametrize("lei", VALID_GLEIS)
    def test_strict_passes_for_valid(self, lei):
        is_valid, error = validate_lei(lei)
        assert is_valid
        assert error == ""

    def test_strict_raises_invalid_format(self):
        with pytest.raises(InvalidLEIError) as excinfo:
            validate_lei("TOO_SHORT")
        assert excinfo.value.reason == "Invalid LEI format"
        assert excinfo.value.lei == "TOO_SHORT"

    def test_strict_raises_invalid_checksum(self):
        broken = "HWUPKR0MPOU8FGXBT395"
        with pytest.raises(InvalidLEIError) as excinfo:
            validate_lei(broken)
        assert (
            excinfo.value.reason == "Invalid LEI checksum (ISO 7064 mod-97-10)"
        )
        assert excinfo.value.lei == broken

    def test_field_attached_to_exception(self):
        with pytest.raises(InvalidLEIError) as excinfo:
            validate_lei("BAD", field="debtor_lei")
        assert excinfo.value.field == "debtor_lei"

    def test_non_strict_returns_tuple_for_bad_format(self):
        is_valid, error = validate_lei("BAD", strict=False)
        assert not is_valid
        assert error  # non-empty


class TestValidateLEISafe:
    @pytest.mark.parametrize("lei", VALID_GLEIS)
    def test_safe_true_for_valid(self, lei):
        assert validate_lei_safe(lei)

    def test_safe_false_for_invalid(self):
        assert not validate_lei_safe("INVALID")

    def test_safe_false_for_bad_checksum(self):
        assert not validate_lei_safe("HWUPKR0MPOU8FGXBT395")

    def test_safe_accepts_field_kwarg(self):
        assert validate_lei_safe("HWUPKR0MPOU8FGXBT394", field="debtor_lei")


# ---------------------------------------------------------------------------
# Pipeline helper: validate_leis
# ---------------------------------------------------------------------------


class TestValidateLEIs:
    def test_empty_input_returns_empty(self):
        assert validate_leis([]) == []

    def test_row_without_lei_columns_skipped(self):
        rows = [{"debtor_name": "Bob", "creditor_name": "Alice"}]
        assert validate_leis(rows) == []

    def test_valid_lei_passes(self):
        rows = [{"debtor_lei": "HWUPKR0MPOU8FGXBT394"}]
        assert validate_leis(rows) == []

    def test_invalid_lei_flagged(self):
        rows = [{"creditor_lei": "GARBAGE"}]
        errors = validate_leis(rows)
        assert len(errors) == 1
        err = errors[0]
        assert err.row == 0
        assert err.party == "creditor"
        assert err.field == "creditor_lei"
        assert err.value == "GARBAGE"

    def test_missing_optional_lei_is_silent(self):
        rows = [{"debtor_lei": "", "creditor_lei": None}]
        assert validate_leis(rows) == []

    def test_required_party_missing_lei_flagged(self):
        rows = [{"debtor_name": "Bob"}]  # no debtor_lei at all
        errors = validate_leis(rows, required_parties=("debtor",))
        assert len(errors) == 1
        assert errors[0].party == "debtor"
        assert "required for this scheme" in errors[0].reason

    def test_required_party_with_valid_lei_passes(self):
        rows = [{"debtor_lei": "HWUPKR0MPOU8FGXBT394"}]
        assert validate_leis(rows, required_parties=("debtor",)) == []

    def test_required_party_with_invalid_lei_flagged_for_format(self):
        rows = [{"debtor_lei": "NONSENSE"}]
        errors = validate_leis(rows, required_parties=("debtor",))
        assert len(errors) == 1
        # The reason comes from the format / checksum validator, not the
        # "required" missing-field path.
        assert "required" not in errors[0].reason

    def test_agent_and_ultimate_parties_recognised(self):
        rows = [
            {
                "debtor_agent_lei": "INVALID1",
                "ultimate_creditor_lei": "INVALID2",
            }
        ]
        errors = validate_leis(rows)
        parties = sorted(e.party for e in errors)
        assert parties == ["debtor_agent", "ultimate_creditor"]

    def test_multiple_rows_aggregated(self):
        rows = [
            {"debtor_lei": "HWUPKR0MPOU8FGXBT394"},  # ok
            {"debtor_lei": "BAD"},  # bad
            {"debtor_lei": "INR2EJN1ERAN0W5ZP974"},  # ok
            {"debtor_lei": "ALSO_BAD"},  # bad
        ]
        errors = validate_leis(rows)
        assert sorted(e.row for e in errors) == [1, 3]


class TestLEIValidationErrorDataclass:
    def test_repr_human_readable(self):
        err = LEIValidationError(
            row=0,
            party="debtor",
            field="debtor_lei",
            value="X",
            reason="why",
        )
        s = repr(err)
        assert "debtor_lei" in s
        assert "why" in s

    def test_equality_and_hashable(self):
        a = LEIValidationError(0, "debtor", "debtor_lei", "X", "r")
        b = LEIValidationError(0, "debtor", "debtor_lei", "X", "r")
        c = LEIValidationError(0, "debtor", "debtor_lei", "X", "OTHER")
        assert a == b
        assert hash(a) == hash(b)
        assert a != c
        assert a != "not an error"
