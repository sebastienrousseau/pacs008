"""Tests for core/core.py — process_files orchestration and helpers."""

import uuid

import pytest

from pacs008.constants import TEMPLATES_DIR, valid_xml_types
from pacs008.core.core import (
    _determine_data_source_type,
    _validate_inputs,
    process_files,
)
from pacs008.exceptions import XMLGenerationError


class TestDetermineDataSourceType:
    """Test data source type detection."""

    def test_list_type(self):
        assert _determine_data_source_type([{"a": 1}]) == "list"

    def test_dict_type(self):
        assert _determine_data_source_type({"a": 1}) == "dict"

    def test_csv_file(self):
        assert _determine_data_source_type("payments.csv") == "csv"

    def test_json_file(self):
        assert _determine_data_source_type("data.json") == "json"

    def test_jsonl_file(self):
        assert _determine_data_source_type("data.jsonl") == "jsonl"

    def test_parquet_file(self):
        assert _determine_data_source_type("data.parquet") == "parquet"

    def test_sqlite_file(self):
        assert _determine_data_source_type("payments.db") == "sqlite"

    def test_sqlite_uri(self):
        assert _determine_data_source_type("sqlite:///data.db") == "sqlite"

    def test_unknown_file(self):
        assert _determine_data_source_type("file.txt") == "file"

    def test_unknown_type(self):
        assert _determine_data_source_type(42) == "unknown"


class TestValidateInputs:
    """Test input validation for process_files."""

    def test_invalid_message_type_raises(self):
        with pytest.raises(XMLGenerationError, match="Invalid XML message type"):
            _validate_inputs("pacs.008.001.99", "t.xml", "s.xsd")

    def test_missing_template_raises(self):
        with pytest.raises(FileNotFoundError):
            _validate_inputs("pacs.008.001.01", "/nonexistent/template.xml", "s.xsd")

    def test_missing_schema_raises(self):
        tpl = str(TEMPLATES_DIR / "pacs.008.001.01" / "template.xml")
        with pytest.raises(FileNotFoundError):
            _validate_inputs("pacs.008.001.01", tpl, "/nonexistent/schema.xsd")

    def test_valid_inputs(self):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        safe_tpl, safe_xsd = _validate_inputs(version, tpl, xsd)
        assert "template.xml" in safe_tpl
        assert version in safe_xsd


@pytest.mark.integration
class TestProcessFiles:
    """Test the process_files orchestration function."""

    def _make_data(self, version):
        ver = int(version.split(".")[-1])
        row = {
            "msg_id": "MSG-CORE-TEST",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-CORE",
            "tx_id": "TX-CORE",
            "interbank_settlement_amount": "1000.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
        }
        if ver >= 8:
            row["uetr"] = str(uuid.uuid4())
        if ver >= 10:
            row["mandate_id"] = "MNDT-CORE"
        if ver == 13:
            row["expiry_date_time"] = "2026-12-31T23:59:59"
        return [row]

    def test_process_files_with_list_data(self):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        data = self._make_data(version)
        # Should not raise
        process_files(version, tpl, xsd, data)

    def test_process_files_invalid_type(self):
        with pytest.raises(XMLGenerationError):
            process_files(
                "pacs.008.001.99",
                "template.xml",
                "schema.xsd",
                [{"msg_id": "X"}],
            )

    @pytest.mark.parametrize(
        "version", ["pacs.008.001.01", "pacs.008.001.08", "pacs.008.001.13"]
    )
    def test_process_files_version_samples(self, version):
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        data = self._make_data(version)
        process_files(version, tpl, xsd, data)
