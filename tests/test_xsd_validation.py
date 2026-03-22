"""Tests for XML XSD validation module."""

import uuid

from pacs008.constants import TEMPLATES_DIR
from pacs008.xml.generate_xml import generate_xml_string
from pacs008.xml.validate_via_xsd import (
    validate_via_xsd,
    validate_xml_string_via_xsd,
)


def _make_xml(version="pacs.008.001.01"):
    ver = int(version.split(".")[-1])
    row = {
        "msg_id": "MSG-XSD-TEST",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "end_to_end_id": "E2E-XSD",
        "tx_id": "TX-XSD",
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
        row["mandate_id"] = "MNDT-XSD"
    if ver == 13:
        row["expiry_date_time"] = "2026-12-31T23:59:59"
    tpl = str(TEMPLATES_DIR / version / "template.xml")
    xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
    return generate_xml_string([row], version, tpl, xsd), xsd


class TestValidateXmlStringViaXsd:
    def test_valid_xml_string(self):
        xml, xsd = _make_xml()
        assert validate_xml_string_via_xsd(xml, xsd)

    def test_invalid_xml_string(self):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        assert not validate_xml_string_via_xsd("<invalid>xml</invalid>", xsd)

    def test_malformed_xml_string(self):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        assert not validate_xml_string_via_xsd("not xml at all <<<", xsd)

    def test_invalid_xsd_path(self):
        assert not validate_xml_string_via_xsd(
            "<root/>", "/nonexistent/schema.xsd"
        )


class TestValidateViaXsd:
    def test_valid_xml_file(self, tmp_path):
        xml_str, xsd = _make_xml()
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(xml_str, encoding="utf-8")
        assert validate_via_xsd(str(xml_file), xsd)

    def test_invalid_xml_file(self, tmp_path):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        xml_file = tmp_path / "bad.xml"
        xml_file.write_text("<invalid>not valid</invalid>", encoding="utf-8")
        assert not validate_via_xsd(str(xml_file), xsd)

    def test_nonexistent_xml_file(self):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        assert not validate_via_xsd("/nonexistent/file.xml", xsd)

    def test_nonexistent_xsd_file(self, tmp_path):
        xml_file = tmp_path / "test.xml"
        xml_file.write_text("<root/>", encoding="utf-8")
        assert not validate_via_xsd(str(xml_file), "/nonexistent/schema.xsd")

    def test_malformed_xml_file(self, tmp_path):
        xsd = str(TEMPLATES_DIR / "pacs.008.001.01" / "pacs.008.001.01.xsd")
        xml_file = tmp_path / "malformed.xml"
        xml_file.write_text("not xml <<<", encoding="utf-8")
        assert not validate_via_xsd(str(xml_file), xsd)
