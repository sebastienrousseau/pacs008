"""Tests for pacs008.exceptions module."""

from pacs008.exceptions import (
    ConfigurationError,
    DataSourceError,
    InvalidBICError,
    InvalidIBANError,
    MissingRequiredFieldError,
    Pacs008Error,
    PaymentValidationError,
    SchemaValidationError,
    XMLGenerationError,
)


def test_pacs008_error_hierarchy():
    assert issubclass(PaymentValidationError, Pacs008Error)
    assert issubclass(XMLGenerationError, Pacs008Error)
    assert issubclass(ConfigurationError, Pacs008Error)
    assert issubclass(DataSourceError, Pacs008Error)
    assert issubclass(SchemaValidationError, Pacs008Error)


def test_payment_validation_error_field():
    e = PaymentValidationError("bad field", field="amount")
    assert e.field == "amount"
    assert str(e) == "bad field"


def test_invalid_iban_error():
    e = InvalidIBANError("bad iban", iban="XX00", field="debtor_iban")
    assert e.iban == "XX00"
    assert e.field == "debtor_iban"


def test_invalid_bic_error():
    e = InvalidBICError("bad bic", bic="XXXX", field="debtor_bic")
    assert e.bic == "XXXX"
    assert e.field == "debtor_bic"


def test_missing_required_field_error():
    e = MissingRequiredFieldError(
        "missing",
        field="debtor_name",
        row_number=3,
        required_fields=["debtor_name", "creditor_name"],
    )
    assert e.field == "debtor_name"
    assert e.row_number == 3
    assert "creditor_name" in e.required_fields


def test_schema_validation_error():
    e = SchemaValidationError("schema fail", errors=["err1", "err2"])
    assert len(e.errors) == 2
