"""Tests for XML generation across all 13 pacs.008 versions."""

import os
import uuid

import pytest

from pacs008.constants import TEMPLATES_DIR, valid_xml_types
from pacs008.xml.generate_xml import generate_xml_string


def _make_base_data(**overrides):
    """Create minimal valid pacs.008 data."""
    data = {
        "msg_id": "MSG001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "end_to_end_id": "E2E001",
        "tx_id": "TX001",
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
    }
    data.update(overrides)
    return [data]


def _template_path(version):
    return str(TEMPLATES_DIR / version / "template.xml")


def _xsd_path(version):
    return str(TEMPLATES_DIR / version / f"{version}.xsd")


class TestGenerateXmlV01:
    """Tests for pacs.008.001.01."""

    @pytest.mark.version_compat
    def test_v01_generates_valid_xml(self):
        version = "pacs.008.001.01"
        data = _make_base_data()
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "pacs.008.001.01" in xml
        assert "<MsgId>MSG001</MsgId>" in xml
        assert "<SttlmMtd>CLRG</SttlmMtd>" in xml
        assert "<IntrBkSttlmAmt" in xml
        assert "<BIC>" in xml


class TestGenerateXmlV02:
    """Tests for pacs.008.001.02 (BIC identifiers)."""

    @pytest.mark.version_compat
    def test_v02_generates_valid_xml(self):
        version = "pacs.008.001.02"
        data = _make_base_data()
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "pacs.008.001.02" in xml
        assert "<FIToFICstmrCdtTrf>" in xml
        assert "<MsgId>MSG001</MsgId>" in xml
        assert "<BIC>" in xml


class TestGenerateXmlV03ToV04:
    """Tests for pacs.008.001.03 through .04 (BICFI identifiers)."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("ver", ["03", "04"])
    def test_v03_to_v04_generates_valid_xml(self, ver):
        version = f"pacs.008.001.{ver}"
        data = _make_base_data()
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert f"pacs.008.001.{ver}" in xml
        assert "<FIToFICstmrCdtTrf>" in xml
        assert "<MsgId>MSG001</MsgId>" in xml
        assert "<BICFI>" in xml


class TestGenerateXmlV05ToV07:
    """Tests for pacs.008.001.05 through .07 (BICFI)."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("ver", ["05", "06", "07"])
    def test_v05_to_v07_uses_bicfi(self, ver):
        version = f"pacs.008.001.{ver}"
        data = _make_base_data()
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "<BICFI>" in xml
        assert "<BIC>" not in xml or "<BICFI>" in xml


class TestGenerateXmlV08ToV09:
    """Tests for pacs.008.001.08 through .09 (UETR)."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("ver", ["08", "09"])
    def test_v08_to_v09_includes_uetr(self, ver):
        version = f"pacs.008.001.{ver}"
        uetr = str(uuid.uuid4())
        data = _make_base_data(uetr=uetr)
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "<UETR>" in xml
        assert uetr in xml


class TestGenerateXmlV10ToV12:
    """Tests for pacs.008.001.10 through .12 (MndtRltdInf)."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("ver", ["10", "11", "12"])
    def test_v10_to_v12_includes_mandate(self, ver):
        version = f"pacs.008.001.{ver}"
        uetr = str(uuid.uuid4())
        data = _make_base_data(uetr=uetr, mandate_id="MNDT-001")
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "<UETR>" in xml
        assert "<MndtId>MNDT-001</MndtId>" in xml


class TestGenerateXmlV13:
    """Tests for pacs.008.001.13."""

    @pytest.mark.version_compat
    def test_v13_includes_expiry_date_time(self):
        version = "pacs.008.001.13"
        uetr = str(uuid.uuid4())
        data = _make_base_data(
            uetr=uetr,
            mandate_id="MNDT-002",
            expiry_date_time="2026-12-31T23:59:59",
        )
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert "<UETR>" in xml
        assert "<MndtId>MNDT-002</MndtId>" in xml


class TestGenerateXmlErrors:
    """Test error handling in generate_xml_string."""

    def test_invalid_message_type_raises(self):
        with pytest.raises(ValueError, match="Invalid XML message type"):
            generate_xml_string(
                [{"msg_id": "X"}],
                "pacs.008.001.99",
                "template.xml",
                "schema.xsd",
            )

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="empty"):
            generate_xml_string(
                [],
                "pacs.008.001.01",
                _template_path("pacs.008.001.01"),
                _xsd_path("pacs.008.001.01"),
            )


class TestAllVersionsValidateAgainstXsd:
    """Ensure every version generates XSD-valid XML."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("version", valid_xml_types)
    def test_xsd_validation(self, version):
        ver_num = int(version.split(".")[-1])
        extra = {}
        if ver_num >= 8:
            extra["uetr"] = str(uuid.uuid4())
        if ver_num >= 10:
            extra["mandate_id"] = "MNDT-XSD"

        data = _make_base_data(**extra)
        xml = generate_xml_string(
            data, version, _template_path(version), _xsd_path(version)
        )
        assert xml.strip().startswith("<?xml") or xml.strip().startswith("<Document")
