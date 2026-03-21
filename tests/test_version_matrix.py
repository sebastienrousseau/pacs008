"""Schema-driven parametrized tests across all 13 pacs.008 versions.

Instead of separate test functions per version, this module uses
pytest.mark.parametrize to run a single validation logic across every
version, testing version-specific features (BIC/BICFI, UETR, mandate,
expiry) with a unified data factory.
"""

import uuid
from xml.etree import ElementTree

import pytest

from pacs008.constants import TEMPLATES_DIR, valid_xml_types
from pacs008.xml.generate_xml import generate_xml_string


# --- Fixtures & Helpers ---


def _base_data(**overrides):
    """Create minimal valid pacs.008 data with optional overrides."""
    row = {
        "msg_id": "MSG-TEST-001",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "end_to_end_id": "E2E-TEST-001",
        "tx_id": "TX-TEST-001",
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
    row.update(overrides)
    return [row]


def _paths(version):
    tpl = str(TEMPLATES_DIR / version / "template.xml")
    xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
    return tpl, xsd


def _version_num(version):
    return int(version.split(".")[-1])


def _enrich_data_for_version(version, extra=None):
    """Build test data with version-appropriate fields."""
    ver = _version_num(version)
    overrides = dict(extra or {})
    if ver >= 8:
        overrides.setdefault("uetr", str(uuid.uuid4()))
    if ver >= 10:
        overrides.setdefault("mandate_id", "MNDT-TEST-001")
    if ver == 13:
        overrides.setdefault("expiry_date_time", "2026-12-31T23:59:59")
    return _base_data(**overrides)


def _generate(version, data=None):
    """Generate XML string for a given version."""
    if data is None:
        data = _enrich_data_for_version(version)
    tpl, xsd = _paths(version)
    return generate_xml_string(data, version, tpl, xsd)


def _parse_xml(xml_string):
    """Parse XML string and return root element."""
    return ElementTree.fromstring(xml_string)


# --- 1. Universal XSD Validation (all 13 versions) ---


class TestAllVersionsXsdValid:
    """Every version must produce XSD-valid XML."""

    @pytest.mark.version_compat
    @pytest.mark.parametrize("version", valid_xml_types)
    def test_generates_xsd_valid_xml(self, version):
        xml = _generate(version)
        assert xml.strip().startswith("<?xml") or xml.strip().startswith(
            "<Document"
        )

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_contains_namespace(self, version):
        xml = _generate(version)
        assert f"urn:iso:std:iso:20022:tech:xsd:{version}" in xml


# --- 2. BIC vs BICFI (version-dependent identifier) ---

BIC_VERSIONS = ["pacs.008.001.01", "pacs.008.001.02"]
BICFI_VERSIONS = [v for v in valid_xml_types if v not in BIC_VERSIONS]


class TestBicIdentifier:
    """v01-v02 use <BIC>, v03+ use <BICFI>."""

    @pytest.mark.parametrize("version", BIC_VERSIONS)
    def test_bic_versions_use_bic_tag(self, version):
        xml = _generate(version)
        assert "<BIC>" in xml
        assert "<BICFI>" not in xml

    @pytest.mark.parametrize("version", BICFI_VERSIONS)
    def test_bicfi_versions_use_bicfi_tag(self, version):
        xml = _generate(version)
        assert "<BICFI>" in xml


# --- 3. UETR (required v08+, UUID v4 format, exactly 36 chars) ---

UETR_VERSIONS = [v for v in valid_xml_types if _version_num(v) >= 8]
NO_UETR_VERSIONS = [v for v in valid_xml_types if _version_num(v) < 8]


class TestUetrGeneration:
    """v08+ must include UETR (36-char UUID v4)."""

    @pytest.mark.parametrize("version", UETR_VERSIONS)
    def test_uetr_present_in_xml(self, version):
        uetr = str(uuid.uuid4())
        data = _enrich_data_for_version(version, {"uetr": uetr})
        xml = _generate(version, data)
        assert "<UETR>" in xml
        assert uetr in xml

    @pytest.mark.parametrize("version", UETR_VERSIONS)
    def test_uetr_is_36_characters(self, version):
        uetr = str(uuid.uuid4())
        data = _enrich_data_for_version(version, {"uetr": uetr})
        xml = _generate(version, data)
        root = _parse_xml(xml)
        ns = f"{{urn:iso:std:iso:20022:tech:xsd:{version}}}"
        uetr_el = root.find(f".//{ns}UETR")
        assert uetr_el is not None
        assert len(uetr_el.text) == 36

    @pytest.mark.parametrize("version", NO_UETR_VERSIONS)
    def test_no_uetr_in_older_versions(self, version):
        xml = _generate(version)
        assert "<UETR>" not in xml


# --- 4. Mandate Information (MndtRltdInf, v10+) ---

MANDATE_VERSIONS = [v for v in valid_xml_types if _version_num(v) >= 10]
NO_MANDATE_VERSIONS = [v for v in valid_xml_types if _version_num(v) < 10]


class TestMandateInfo:
    """v10+ support MndtRltdInf with MndtId."""

    @pytest.mark.parametrize("version", MANDATE_VERSIONS)
    def test_mandate_id_in_xml(self, version):
        data = _enrich_data_for_version(
            version, {"mandate_id": "MNDT-PARAM-001"}
        )
        xml = _generate(version, data)
        assert "<MndtId>MNDT-PARAM-001</MndtId>" in xml

    @pytest.mark.parametrize("version", MANDATE_VERSIONS)
    def test_mandate_element_structure(self, version):
        data = _enrich_data_for_version(
            version, {"mandate_id": "MNDT-STRUCT"}
        )
        xml = _generate(version, data)
        assert "<MndtRltdInf>" in xml
        assert "</MndtRltdInf>" in xml

    @pytest.mark.parametrize("version", NO_MANDATE_VERSIONS)
    def test_no_mandate_in_older_versions(self, version):
        xml = _generate(version)
        assert "<MndtRltdInf>" not in xml


# --- 5. Expiry Date Time (XpryDtTm, v13 only) ---


class TestExpiryDateTime:
    """v13 supports XpryDtTm in GrpHdr."""

    def test_expiry_datetime_in_v13(self):
        data = _enrich_data_for_version(
            "pacs.008.001.13",
            {"expiry_date_time": "2026-12-31T23:59:59"},
        )
        xml = _generate("pacs.008.001.13", data)
        assert "<XpryDtTm>2026-12-31T23:59:59</XpryDtTm>" in xml

    @pytest.mark.parametrize(
        "version",
        [v for v in valid_xml_types if v != "pacs.008.001.13"],
    )
    def test_no_expiry_in_other_versions(self, version):
        xml = _generate(version)
        assert "<XpryDtTm>" not in xml


# --- 6. Core Element Presence (all versions) ---


class TestCoreElements:
    """Every version must contain mandatory pacs.008 elements."""

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_msg_id_present(self, version):
        xml = _generate(version)
        assert "<MsgId>MSG-TEST-001</MsgId>" in xml

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_settlement_method_present(self, version):
        xml = _generate(version)
        assert "<SttlmMtd>CLRG</SttlmMtd>" in xml

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_interbank_amount_present(self, version):
        xml = _generate(version)
        assert "1000.00" in xml
        assert "<IntrBkSttlmAmt" in xml

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_debtor_name_present(self, version):
        xml = _generate(version)
        assert "<Nm>Debtor Corp</Nm>" in xml

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_creditor_name_present(self, version):
        xml = _generate(version)
        assert "<Nm>Creditor Ltd</Nm>" in xml

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_end_to_end_id_present(self, version):
        xml = _generate(version)
        assert "<EndToEndId>E2E-TEST-001</EndToEndId>" in xml


# --- 7. Multi-Transaction Support ---


class TestMultiTransaction:
    """All versions must handle multiple transactions in one message."""

    @pytest.mark.parametrize(
        "version", ["pacs.008.001.01", "pacs.008.001.05", "pacs.008.001.10"]
    )
    def test_two_transactions(self, version):
        ver = _version_num(version)
        base = {
            "msg_id": "MSG-MULTI",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "2",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-001",
            "tx_id": "TX-001",
            "interbank_settlement_amount": "500.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Debtor A",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor A",
        }
        row2 = dict(base)
        row2["end_to_end_id"] = "E2E-002"
        row2["tx_id"] = "TX-002"
        row2["interbank_settlement_amount"] = "750.00"
        row2["debtor_name"] = "Debtor B"
        row2["creditor_name"] = "Creditor B"

        if ver >= 8:
            base["uetr"] = str(uuid.uuid4())
            row2["uetr"] = str(uuid.uuid4())
        if ver >= 10:
            base["mandate_id"] = "MNDT-A"
            row2["mandate_id"] = "MNDT-B"

        data = [base, row2]
        xml = _generate(version, data)
        assert xml.count("<EndToEndId>") == 2
        assert "E2E-001" in xml
        assert "E2E-002" in xml


# --- 8. Edge Cases ---


class TestEdgeCases:
    """Edge cases that should be handled gracefully."""

    def test_empty_data_raises(self):
        tpl, xsd = _paths("pacs.008.001.01")
        with pytest.raises(ValueError, match="empty"):
            generate_xml_string([], "pacs.008.001.01", tpl, xsd)

    def test_invalid_version_raises(self):
        with pytest.raises(ValueError, match="Invalid XML message type"):
            generate_xml_string(
                [{"msg_id": "X"}], "pacs.008.001.99", "t.xml", "s.xsd"
            )

    @pytest.mark.parametrize("version", valid_xml_types)
    def test_optional_fields_can_be_empty(self, version):
        """XML generation works with only XSD-required fields populated."""
        minimal = {
            "msg_id": "MSG-MIN",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "end_to_end_id": "E2E-MIN",
            "tx_id": "TX-MIN",
            "interbank_settlement_amount": "100.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SHAR",
            "debtor_name": "Min Debtor",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Min Creditor",
        }
        ver = _version_num(version)
        if ver >= 8:
            minimal["uetr"] = str(uuid.uuid4())
        if ver >= 10:
            minimal["mandate_id"] = "MNDT-MIN"
        if ver == 13:
            minimal["expiry_date_time"] = "2026-12-31T23:59:59"

        data = [minimal]
        xml = _generate(version, data)
        assert "<MsgId>MSG-MIN</MsgId>" in xml
