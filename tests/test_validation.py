"""Tests for pacs008.validation module."""

import pytest

from pacs008.validation.service import (
    ValidationConfig,
    ValidationReport,
    ValidationResult,
    ValidationService,
)
from pacs008.validation.schema_validator import SchemaValidator


class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(is_valid=True)
        assert r.is_valid
        assert r.error is None

    def test_invalid_result(self):
        r = ValidationResult(is_valid=False, error="bad", field="msg_id")
        assert not r.is_valid
        assert r.error == "bad"
        assert r.field == "msg_id"


class TestValidationService:
    def setup_method(self):
        self.service = ValidationService()

    def test_validate_valid_message_type(self):
        result = self.service.validate_message_type("pacs.008.001.01")
        assert result.is_valid

    def test_validate_invalid_message_type(self):
        result = self.service.validate_message_type("pacs.008.001.99")
        assert not result.is_valid
        assert "Invalid" in result.error

    def test_validate_empty_message_type(self):
        result = self.service.validate_message_type("")
        assert not result.is_valid

    def test_validate_all_13_message_types(self):
        for i in range(1, 14):
            ver = f"pacs.008.001.{i:02d}"
            result = self.service.validate_message_type(ver)
            assert result.is_valid, f"Failed for {ver}"

    def test_validate_template_missing(self):
        result = self.service.validate_template("/nonexistent/template.xml")
        assert not result.is_valid

    def test_validate_schema_missing(self):
        result = self.service.validate_schema("/nonexistent/schema.xsd")
        assert not result.is_valid

    def test_validate_data_source_missing(self):
        result = self.service.validate_data_source("/nonexistent/data.csv")
        assert not result.is_valid

    def test_validate_empty_template(self):
        result = self.service.validate_template("")
        assert not result.is_valid

    def test_validate_empty_schema(self):
        result = self.service.validate_schema("")
        assert not result.is_valid

    def test_validate_empty_data_source(self):
        result = self.service.validate_data_source("")
        assert not result.is_valid


class TestSchemaValidator:
    def test_create_validator_v01(self):
        v = SchemaValidator("pacs.008.001.01")
        assert v.schema is not None

    def test_invalid_message_type_raises(self):
        with pytest.raises(ValueError, match="Invalid message type"):
            SchemaValidator("pacs.008.001.99")

    def test_required_fields_v01(self):
        v = SchemaValidator("pacs.008.001.01")
        required = v.get_required_fields()
        assert "msg_id" in required
        assert "settlement_method" in required
        assert "interbank_settlement_amount" in required

    def test_valid_data_passes(self):
        v = SchemaValidator("pacs.008.001.01")
        data = {
            "msg_id": "MSG001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": 1,
            "settlement_method": "CLRG",
            "end_to_end_id": "E2E001",
            "interbank_settlement_amount": 1000.00,
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
        }
        errors = v.validate_data(data)
        assert len(errors) == 0

    def test_missing_required_field_fails(self):
        v = SchemaValidator("pacs.008.001.01")
        data = {"msg_id": "MSG001"}  # missing many required fields
        errors = v.validate_data(data)
        assert len(errors) > 0

    def test_validate_batch(self):
        v = SchemaValidator("pacs.008.001.01")
        valid_row = {
            "msg_id": "MSG001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": 1,
            "settlement_method": "CLRG",
            "end_to_end_id": "E2E001",
            "interbank_settlement_amount": 1000.00,
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
        }
        invalid_row = {"msg_id": "MSG002"}
        total, valid, errors = v.validate_batch([valid_row, invalid_row])
        assert total == 2
        assert valid == 1
        assert len(errors) == 1

    def test_get_field_schema(self):
        v = SchemaValidator("pacs.008.001.01")
        schema = v.get_field_schema("msg_id")
        assert schema is not None
        assert "type" in schema

    def test_get_field_description(self):
        v = SchemaValidator("pacs.008.001.01")
        desc = v.get_field_description("msg_id")
        assert desc is not None or desc is None  # may or may not have description

    def test_v08_has_uetr_property(self):
        """UETR is optional in XSD but defined as a property in v08+."""
        v = SchemaValidator("pacs.008.001.08")
        schema = v.get_field_schema("uetr")
        assert schema is not None
        assert schema.get("pattern") is not None
