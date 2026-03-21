"""Tests for __main__.py entry point."""

import csv
import json

import pytest

from pacs008.__main__ import main
from pacs008.constants import TEMPLATES_DIR


def _make_valid_row():
    return {
        "msg_id": "MSG-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-001",
        "tx_id": "TX-001",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
        "interbank_settlement_date": "2026-01-15",
    }


@pytest.fixture()
def test_data_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "payments.csv"
    row = _make_valid_row()
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
    return str(path)


class TestMainMissingArgs:
    def test_no_message_type(self):
        with pytest.raises(SystemExit) as exc_info:
            main(None, "template.xml", "schema.xsd", "data.csv")
        assert exc_info.value.code == 1

    def test_no_template(self):
        with pytest.raises(SystemExit) as exc_info:
            main("pacs.008.001.01", None, "schema.xsd", "data.csv")
        assert exc_info.value.code == 1

    def test_no_schema(self):
        with pytest.raises(SystemExit) as exc_info:
            main("pacs.008.001.01", "template.xml", None, "data.csv")
        assert exc_info.value.code == 1

    def test_no_data(self):
        with pytest.raises(SystemExit) as exc_info:
            main("pacs.008.001.01", "template.xml", "schema.xsd", None)
        assert exc_info.value.code == 1


class TestMainValidation:
    def test_invalid_message_type(self, test_data_csv):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        with pytest.raises(SystemExit) as exc_info:
            main("pacs.008.001.99", tpl, xsd, test_data_csv)
        assert exc_info.value.code == 1

    def test_nonexistent_template(self, test_data_csv):
        with pytest.raises(SystemExit) as exc_info:
            main(
                "pacs.008.001.01",
                "/nonexistent/template.xml",
                str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd"),
                test_data_csv,
            )
        assert exc_info.value.code == 1


class TestMainDryRun:
    def test_dry_run(self, test_data_csv):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        # dry_run should not raise and not generate XML
        main(version, tpl, xsd, test_data_csv, dry_run=True)


class TestMainGenerate:
    def test_generate_xml(self, test_data_csv, monkeypatch):
        from pathlib import Path
        # CWD must contain the template dir for path validation
        monkeypatch.chdir(Path(__file__).resolve().parent.parent)
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        main(version, tpl, xsd, test_data_csv)
