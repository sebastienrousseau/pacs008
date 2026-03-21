"""Tests for IBAN validation (ISO 7064 mod-97-10)."""

import pytest

from pacs008.exceptions import InvalidIBANError
from pacs008.validation.iban_validator import (
    IBAN_LENGTHS,
    validate_iban,
    validate_iban_checksum,
    validate_iban_format,
    validate_iban_safe,
)


class TestValidateIbanFormat:
    """Test IBAN format validation."""

    def test_valid_german_iban(self):
        ok, err = validate_iban_format("DE89370400440532013000")
        assert ok
        assert err == ""

    def test_valid_gb_iban(self):
        ok, err = validate_iban_format("GB29NWBK60161331926819")
        assert ok

    def test_valid_iban_with_spaces(self):
        ok, err = validate_iban_format("DE89 3704 0044 0532 0130 00")
        assert ok

    def test_valid_iban_with_dashes(self):
        ok, err = validate_iban_format("DE89-3704-0044-0532-0130-00")
        assert ok

    def test_valid_lowercase_iban(self):
        ok, err = validate_iban_format("de89370400440532013000")
        assert ok

    def test_empty_iban(self):
        ok, err = validate_iban_format("")
        assert not ok
        assert "empty" in err.lower()

    def test_too_short_iban(self):
        ok, err = validate_iban_format("DE8937040044")
        assert not ok
        assert "15-34" in err

    def test_too_long_iban(self):
        ok, err = validate_iban_format("DE" + "1" * 33)
        assert not ok
        assert "15-34" in err

    def test_invalid_country_code_digits(self):
        ok, err = validate_iban_format("12893704004405320130")
        assert not ok
        assert "country code" in err.lower()

    def test_invalid_check_digits_letters(self):
        ok, err = validate_iban_format("DEAB370400440532013000")
        assert not ok
        assert "check digits" in err.lower()

    def test_invalid_bban_special_chars(self):
        ok, err = validate_iban_format("DE8937040044053201!000")
        assert not ok
        assert "alphanumeric" in err.lower()

    def test_wrong_country_length(self):
        # DE IBAN should be 22 chars, give it 20
        ok, err = validate_iban_format("DE89370400440532013")
        assert not ok
        assert "Invalid IBAN length for DE" in err

    def test_unknown_country_code_passes(self):
        # Unknown country code should pass (future-proof)
        ok, err = validate_iban_format("ZZ12345678901234567")
        assert ok

    def test_swiss_iban(self):
        ok, err = validate_iban_format("CH9300762011623852957")
        assert ok

    def test_french_iban(self):
        ok, err = validate_iban_format("FR7630006000011234567890189")
        assert ok


class TestValidateIbanChecksum:
    """Test ISO 7064 mod-97-10 checksum validation."""

    def test_valid_de_checksum(self):
        ok, err = validate_iban_checksum("DE89370400440532013000")
        assert ok
        assert err == ""

    def test_valid_gb_checksum(self):
        ok, err = validate_iban_checksum("GB29NWBK60161331926819")
        assert ok

    def test_invalid_checksum(self):
        ok, err = validate_iban_checksum("DE00370400440532013000")
        assert not ok
        assert "checksum" in err.lower()

    def test_checksum_with_spaces(self):
        ok, err = validate_iban_checksum("DE89 3704 0044 0532 0130 00")
        assert ok

    def test_valid_nl_checksum(self):
        ok, err = validate_iban_checksum("NL91ABNA0417164300")
        assert ok


class TestValidateIban:
    """Test the main validate_iban entry point."""

    def test_valid_iban_strict(self):
        ok, err = validate_iban("DE89370400440532013000")
        assert ok
        assert err == ""

    def test_valid_iban_non_strict(self):
        ok, err = validate_iban("DE89370400440532013000", strict=False)
        assert ok

    def test_invalid_format_strict_raises(self):
        with pytest.raises(InvalidIBANError) as exc_info:
            validate_iban("", field="debtor_account")
        assert exc_info.value.field == "debtor_account"
        assert exc_info.value.iban == ""
        assert exc_info.value.reason == "Invalid IBAN format"

    def test_invalid_format_non_strict(self):
        ok, err = validate_iban("", strict=False)
        assert not ok

    def test_invalid_checksum_strict_raises(self):
        with pytest.raises(InvalidIBANError) as exc_info:
            validate_iban("DE00370400440532013000")
        assert "checksum" in exc_info.value.reason.lower()

    def test_invalid_checksum_non_strict(self):
        ok, err = validate_iban("DE00370400440532013000", strict=False)
        assert not ok
        assert "checksum" in err.lower()


class TestValidateIbanSafe:
    """Test the safe (no-exception) wrapper."""

    def test_valid_iban(self):
        assert validate_iban_safe("DE89370400440532013000")

    def test_invalid_iban(self):
        assert not validate_iban_safe("")

    def test_invalid_checksum(self):
        assert not validate_iban_safe("DE00370400440532013000")

    def test_with_field_name(self):
        assert validate_iban_safe("GB29NWBK60161331926819", field="creditor")


class TestIbanLengths:
    """Test IBAN_LENGTHS dictionary coverage."""

    def test_known_countries_present(self):
        assert "DE" in IBAN_LENGTHS
        assert "GB" in IBAN_LENGTHS
        assert "FR" in IBAN_LENGTHS
        assert "CH" in IBAN_LENGTHS
        assert "NL" in IBAN_LENGTHS

    def test_de_length(self):
        assert IBAN_LENGTHS["DE"] == 22

    def test_gb_length(self):
        assert IBAN_LENGTHS["GB"] == 22

    def test_no_length(self):
        assert IBAN_LENGTHS["NO"] == 15
