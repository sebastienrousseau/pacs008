"""Tests for BIC/SWIFT code validation (ISO 9362)."""

import pytest

from pacs008.exceptions import InvalidBICError
from pacs008.validation.bic_validator import (
    VALID_COUNTRY_CODES,
    validate_bic,
    validate_bic_format,
    validate_bic_safe,
)


class TestValidateBicFormat:
    """Test BIC format validation per ISO 9362."""

    def test_valid_8char_bic(self):
        ok, err = validate_bic_format("DEUTDEFF")
        assert ok
        assert err == ""

    def test_valid_11char_bic(self):
        ok, err = validate_bic_format("DEUTDEFF500")
        assert ok

    def test_valid_bic_with_spaces(self):
        ok, err = validate_bic_format("DEUT DE FF")
        assert ok

    def test_valid_lowercase_bic(self):
        ok, err = validate_bic_format("deutdeff")
        assert ok

    def test_empty_bic(self):
        ok, err = validate_bic_format("")
        assert not ok
        assert "empty" in err.lower()

    def test_wrong_length_6(self):
        ok, err = validate_bic_format("DEUTDE")
        assert not ok
        assert "8 or 11" in err

    def test_wrong_length_9(self):
        ok, err = validate_bic_format("DEUTDEFF5")
        assert not ok
        assert "8 or 11" in err

    def test_invalid_bank_code_digits(self):
        ok, err = validate_bic_format("1234DEFF")
        assert not ok
        assert "bank code" in err.lower()

    def test_invalid_country_code_digits(self):
        ok, err = validate_bic_format("DEUT12FF")
        assert not ok
        assert "country code" in err.lower()

    def test_invalid_location_code_special(self):
        ok, err = validate_bic_format("DEUTDE!!")
        assert not ok
        assert "location code" in err.lower()

    def test_invalid_branch_code_special(self):
        ok, err = validate_bic_format("DEUTDEFF!!!")
        assert not ok
        assert "branch code" in err.lower()

    def test_invalid_country_code_unknown(self):
        ok, err = validate_bic_format("DEUTXXFF")
        assert not ok
        assert "not a valid ISO 3166-1" in err

    def test_valid_us_bic(self):
        ok, err = validate_bic_format("CHASUS33")
        assert ok

    def test_valid_jp_bic(self):
        ok, err = validate_bic_format("BOTKJPJT")
        assert ok

    def test_bic_with_dashes(self):
        ok, err = validate_bic_format("DEUT-DE-FF")
        assert ok


class TestValidateBic:
    """Test the main validate_bic entry point."""

    def test_valid_bic_strict(self):
        ok, err = validate_bic("DEUTDEFF")
        assert ok
        assert err == ""

    def test_valid_bic_non_strict(self):
        ok, err = validate_bic("COBADEFF", strict=False)
        assert ok

    def test_invalid_bic_strict_raises(self):
        with pytest.raises(InvalidBICError) as exc_info:
            validate_bic("INVALID", field="debtor_agent")
        assert exc_info.value.field == "debtor_agent"
        assert exc_info.value.bic == "INVALID"
        assert "ISO 9362" in exc_info.value.reason

    def test_invalid_bic_non_strict(self):
        ok, err = validate_bic("", strict=False)
        assert not ok

    def test_empty_bic_strict_raises(self):
        with pytest.raises(InvalidBICError):
            validate_bic("")


class TestValidateBicSafe:
    """Test the safe (no-exception) wrapper."""

    def test_valid_bic(self):
        assert validate_bic_safe("DEUTDEFF")

    def test_invalid_bic(self):
        assert not validate_bic_safe("")

    def test_invalid_format(self):
        assert not validate_bic_safe("TOOLONG123456")

    def test_with_field_name(self):
        assert validate_bic_safe("COBADEFF", field="creditor_agent")


class TestValidCountryCodes:
    """Test VALID_COUNTRY_CODES set."""

    def test_sepa_countries_present(self):
        for cc in ["DE", "FR", "GB", "NL", "AT", "BE", "IT", "ES"]:
            assert cc in VALID_COUNTRY_CODES

    def test_major_financial_centers(self):
        for cc in ["US", "JP", "HK", "SG", "CH"]:
            assert cc in VALID_COUNTRY_CODES
