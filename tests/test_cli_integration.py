"""Tests for CLI integration using Click's CliRunner."""

import csv
import os
import uuid

import pytest
from click.testing import CliRunner

from pacs008.cli.cli import main, _configure_logging, _load_configuration
from pacs008.constants import TEMPLATES_DIR


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def valid_csv(tmp_path):
    """Create a valid CSV file for CLI testing."""
    path = tmp_path / "payments.csv"
    fieldnames = [
        "msg_id", "creation_date_time", "nb_of_txs", "settlement_method",
        "interbank_settlement_date", "end_to_end_id", "tx_id",
        "interbank_settlement_amount", "interbank_settlement_currency",
        "charge_bearer", "debtor_name", "debtor_account_iban",
        "debtor_agent_bic", "creditor_agent_bic", "creditor_name",
        "creditor_account_iban", "remittance_information",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "msg_id": "MSG-CLI-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-CLI",
            "tx_id": "TX-CLI-001",
            "interbank_settlement_amount": "1000.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor Corp",
            "debtor_account_iban": "DE89370400440532013000",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
            "creditor_account_iban": "GB29NWBK60161331926819",
            "remittance_information": "Invoice 12345",
        })
    return str(path)


@pytest.fixture()
def config_file(tmp_path):
    """Create a config INI file."""
    path = tmp_path / "config.ini"
    path.write_text(
        "[Paths]\n"
        "xml_template_file_path = override_template.xml\n"
        "xsd_schema_file_path = override_schema.xsd\n"
        "data_file_path = override_data.csv\n",
        encoding="utf-8",
    )
    return str(path)


class TestCliHelp:
    """Test CLI help output."""

    def test_help_flag(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "pacs.008" in result.output.lower() or "ISO 20022" in result.output

    def test_short_help(self, runner):
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0


class TestCliDryRun:
    """Test CLI dry-run mode."""

    def test_dry_run_validates_only(self, runner, valid_csv):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        result = runner.invoke(main, [
            "-t", version,
            "-m", tpl,
            "-s", xsd,
            "-d", valid_csv,
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "validations passed" in result.output.lower() or "dry" in result.output.lower()


class TestCliGenerate:
    """Test CLI XML generation."""

    def test_generate_xml(self, runner, valid_csv):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        result = runner.invoke(main, [
            "-t", version,
            "-m", tpl,
            "-s", xsd,
            "-d", valid_csv,
        ])
        assert result.exit_code == 0

    def test_verbose_mode(self, runner, valid_csv):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        result = runner.invoke(main, [
            "-t", version,
            "-m", tpl,
            "-s", xsd,
            "-d", valid_csv,
            "--dry-run",
            "--verbose",
        ])
        assert result.exit_code == 0


class TestCliErrors:
    """Test CLI error handling."""

    def test_missing_required_args(self, runner):
        result = runner.invoke(main, [])
        assert result.exit_code != 0

    def test_invalid_message_type(self, runner):
        result = runner.invoke(main, ["-t", "pacs.008.001.99"])
        assert result.exit_code != 0

    def test_missing_data_file(self, runner):
        version = "pacs.008.001.01"
        tpl = str(TEMPLATES_DIR / version / "template.xml")
        xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
        result = runner.invoke(main, [
            "-t", version,
            "-m", tpl,
            "-s", xsd,
            "-d", "/nonexistent/file.csv",
        ])
        assert result.exit_code != 0


class TestConfigureLogging:
    """Test CLI logging configuration helper."""

    def test_verbose_sets_debug(self):
        logger = _configure_logging(True)
        assert logger.level == logging.DEBUG

    def test_non_verbose_sets_info(self):
        logger = _configure_logging(False)
        assert logger.level == logging.INFO


class TestLoadConfiguration:
    """Test configuration file loading."""

    def test_no_config_file(self):
        t, s, d = _load_configuration(None, "t.xml", "s.xsd", "d.csv")
        assert t == "t.xml"
        assert s == "s.xsd"
        assert d == "d.csv"

    def test_config_file_overrides(self, config_file):
        t, s, d = _load_configuration(config_file, "t.xml", "s.xsd", "d.csv")
        assert t == "override_template.xml"
        assert s == "override_schema.xsd"
        assert d == "override_data.csv"

    def test_config_file_without_paths_section(self, tmp_path):
        cfg = tmp_path / "empty.ini"
        cfg.write_text("[Other]\nkey = value\n", encoding="utf-8")
        t, s, d = _load_configuration(str(cfg), "t.xml", "s.xsd", "d.csv")
        assert t == "t.xml"  # No override


import logging
