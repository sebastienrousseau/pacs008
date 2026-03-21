"""Tests for validation/service.py — ValidationService orchestrator."""

import csv
import json
import os

import pytest

from pacs008.constants import TEMPLATES_DIR
from pacs008.exceptions import ConfigurationError
from pacs008.validation.service import (
    ValidationConfig,
    ValidationReport,
    ValidationResult,
    ValidationService,
)


@pytest.fixture()
def service():
    return ValidationService()


@pytest.fixture()
def valid_csv_file(tmp_path, monkeypatch):
    """Create a valid CSV data file."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.csv"
    fieldnames = [
        "msg_id", "creation_date_time", "nb_of_txs", "settlement_method",
        "end_to_end_id", "tx_id", "interbank_settlement_amount",
        "interbank_settlement_currency", "charge_bearer",
        "debtor_name", "debtor_agent_bic", "creditor_agent_bic", "creditor_name",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "msg_id": "MSG-001", "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1", "settlement_method": "CLRG",
            "end_to_end_id": "E2E-001", "tx_id": "TX-001",
            "interbank_settlement_amount": "1000.00",
            "interbank_settlement_currency": "EUR", "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp", "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF", "creditor_name": "Creditor Ltd",
        })
    return str(path)


class TestValidateMessageType:
    def test_valid_type(self, service):
        result = service.validate_message_type("pacs.008.001.01")
        assert result.is_valid

    def test_invalid_type(self, service):
        result = service.validate_message_type("pacs.008.001.99")
        assert not result.is_valid
        assert "Invalid" in result.error

    def test_empty_type(self, service):
        result = service.validate_message_type("")
        assert not result.is_valid
        assert "required" in result.error.lower()


class TestValidateTemplate:
    def test_valid_template(self, service):
        tpl = str(TEMPLATES_DIR / "pacs.008.001.01" / "template.xml")
        result = service.validate_template(tpl)
        assert result.is_valid

    def test_missing_template(self, service):
        result = service.validate_template("/nonexistent/template.xml")
        assert not result.is_valid

    def test_empty_template_path(self, service):
        result = service.validate_template("")
        assert not result.is_valid
        assert "required" in result.error.lower()


class TestValidateSchema:
    def test_valid_schema(self, service):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        result = service.validate_schema(xsd)
        assert result.is_valid

    def test_missing_schema(self, service):
        result = service.validate_schema("/nonexistent/schema.xsd")
        assert not result.is_valid

    def test_empty_schema_path(self, service):
        result = service.validate_schema("")
        assert not result.is_valid


class TestValidateDataSource:
    def test_valid_data_file(self, service, valid_csv_file):
        result = service.validate_data_source(valid_csv_file)
        assert result.is_valid

    def test_missing_data_file(self, service):
        result = service.validate_data_source("/nonexistent/data.csv")
        assert not result.is_valid

    def test_empty_data_path(self, service):
        result = service.validate_data_source("")
        assert not result.is_valid

    def test_directory_instead_of_file(self, service, tmp_path):
        result = service.validate_data_source(str(tmp_path))
        assert not result.is_valid
        assert "directory" in result.error.lower()


class TestValidateDataContent:
    def test_valid_data_content(self, service, valid_csv_file):
        result = service.validate_data_content(valid_csv_file)
        assert result.is_valid

    def test_nonexistent_file(self, service):
        result = service.validate_data_content("/nonexistent/file.csv")
        assert not result.is_valid


class TestValidateAll:
    def test_all_valid(self, service, valid_csv_file):
        version = "pacs.008.001.01"
        config = ValidationConfig(
            xml_message_type=version,
            xml_template_file_path=str(TEMPLATES_DIR / version / "template.xml"),
            xsd_schema_file_path=str(TEMPLATES_DIR / version / f"{version}.xsd"),
            data_file_path=valid_csv_file,
        )
        report = service.validate_all(config)
        assert report.is_valid
        assert len(report.errors) == 0

    def test_invalid_message_type(self, service, valid_csv_file):
        config = ValidationConfig(
            xml_message_type="pacs.008.001.99",
            xml_template_file_path=str(TEMPLATES_DIR / "pacs.008.001.01" / "template.xml"),
            xsd_schema_file_path=str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd"),
            data_file_path=valid_csv_file,
        )
        report = service.validate_all(config)
        assert not report.is_valid
        assert len(report.errors) > 0

    def test_missing_template(self, service, valid_csv_file):
        config = ValidationConfig(
            xml_message_type="pacs.008.001.01",
            xml_template_file_path="/nonexistent/template.xml",
            xsd_schema_file_path=str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd"),
            data_file_path=valid_csv_file,
        )
        report = service.validate_all(config)
        assert not report.is_valid

    def test_missing_data_skips_content(self, service):
        version = "pacs.008.001.01"
        config = ValidationConfig(
            xml_message_type=version,
            xml_template_file_path=str(TEMPLATES_DIR / version / "template.xml"),
            xsd_schema_file_path=str(TEMPLATES_DIR / version / f"{version}.xsd"),
            data_file_path="/nonexistent/data.csv",
        )
        report = service.validate_all(config)
        assert not report.is_valid
        assert "data_content" not in report.results  # Skipped


class TestValidationDataclasses:
    def test_validation_result_defaults(self):
        r = ValidationResult(is_valid=True)
        assert r.error is None
        assert r.field is None
        assert r.details is None

    def test_validation_report_defaults(self):
        r = ValidationReport(is_valid=True)
        assert r.errors == []
        assert r.results == {}

    def test_validation_config(self):
        c = ValidationConfig(
            xml_message_type="v01",
            xml_template_file_path="t.xml",
            xsd_schema_file_path="s.xsd",
            data_file_path="d.csv",
        )
        assert c.pre_validate is True
