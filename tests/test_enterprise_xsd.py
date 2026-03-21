"""Enterprise-level XSD validation tests for all 13 pacs.008 versions.

Exercises every supported optional element and validates generated XML
against the corresponding XSD schema for each version.
"""

from pathlib import Path

import pytest

from pacs008.xml.generate_xml import generate_xml_string

BASE = Path(__file__).resolve().parent.parent / "pacs008" / "templates"

ALL_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(1, 14)]
BIC_VERSIONS = [f"pacs.008.001.{i:02d}" for i in (1, 2)]
BICFI_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(3, 14)]
UETR_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(8, 14)]
MANDATE_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(10, 14)]
NUMBERED_PRVS_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(7, 14)]
UNNUMBERED_PRVS_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(1, 7)]
CLR_SYS_REF_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(2, 14)]
STTLM_PRTY_VERSIONS = [f"pacs.008.001.{i:02d}" for i in range(2, 14)]


def _paths(v):
    d = BASE / v
    return str(d / "template.xml"), str(d / f"{v}.xsd")


def _minimal(v_num):
    """Minimal required-only data."""
    d = {
        "msg_id": "MSG-MIN",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "1",
        "settlement_method": "CLRG",
        "end_to_end_id": "E2E-MIN",
        "tx_id": "TX-MIN",
        "interbank_settlement_amount": "1000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Debtor Corp",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Creditor Ltd",
    }
    if v_num >= 8:
        d["uetr"] = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
    return [d]


def _full(v_num):
    """Full data with all optional elements."""
    d = {
        "msg_id": "MSG-FULL",
        "creation_date_time": "2026-01-15T10:30:00",
        "nb_of_txs": "2",
        "settlement_method": "CLRG",
        "interbank_settlement_date": "2026-01-15",
        "ctrl_sum": "35000.00",
        "ttl_intrbank_sttlm_amt": "35000.00",
        "ttl_intrbank_sttlm_ccy": "EUR",
        "instg_agt_bic": "DEUTDEFF",
        "instd_agt_bic": "COBADEFF",
        "end_to_end_id": "E2E-FULL-001",
        "tx_id": "TX-FULL-001",
        "instr_id": "INSTR-001",
        "interbank_settlement_amount": "25000.00",
        "interbank_settlement_currency": "EUR",
        "charge_bearer": "SHAR",
        "debtor_name": "Acme Corp GmbH",
        "debtor_account_iban": "DE89370400440532013000",
        "debtor_agent_bic": "DEUTDEFF",
        "creditor_agent_bic": "COBADEFF",
        "creditor_name": "Widget Industries SA",
        "creditor_account_iban": "FR7630006000011234567890189",
        "remittance_information": "Invoice INV-2026-001",
        "instd_amount": "24500.00",
        "instd_currency": "USD",
        "xchg_rate": "1.0204",
        "purpose_cd": "SALA",
        "ultimate_debtor_name": "Parent Holdings AG",
        "ultimate_creditor_name": "Sub Company SL",
        "intermediary_agent1_bic": "CHASUS33",
        "intermediary_agent2_bic": "BNPAFRPP",
        "instr_for_cdtr_agt_cd": "PHOB",
        "instr_for_cdtr_agt_inf": "Phone beneficiary",
        "instr_for_nxt_agt_inf": "Forward urgently",
        "chrgs_inf_amt": "15.00",
        "chrgs_inf_ccy": "EUR",
        "chrgs_inf_agt_bic": "DEUTDEFF",
        "pmt_tp_inf_svc_lvl_cd": "SDVA",
        "pmt_tp_inf_instr_prty": "HIGH",
    }
    if v_num >= 2:
        d["clr_sys_ref"] = "CLR-REF-001"
        d["sttlm_prty"] = "NORM"
    if v_num < 7:
        d["prvs_instg_agt_bic"] = "BARCGB22"
    if v_num >= 7:
        d["prvs_instg_agt1_bic"] = "BARCGB22"
        d["prvs_instg_agt2_bic"] = "BNPAFRPP"
    if v_num >= 8:
        d["uetr"] = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
    if v_num >= 10:
        d["mandate_id"] = "MNDT-FULL-001"
    if v_num >= 13:
        d["expiry_date_time"] = "2026-12-31T23:59:59"

    tx2 = dict(d)
    tx2["end_to_end_id"] = "E2E-FULL-002"
    tx2["tx_id"] = "TX-FULL-002"
    tx2["instr_id"] = "INSTR-002"
    tx2["interbank_settlement_amount"] = "10000.00"
    tx2["creditor_name"] = "Second Creditor SL"
    return [d, tx2]


# ── Parametrized minimal tests (required-only, all 13 versions) ──────


class TestMinimalXsdValid:
    """Every version must produce valid XML with only required fields."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_minimal_data_validates(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_minimal(v_num), v, t, x)
        assert "<MsgId>MSG-MIN</MsgId>" in xml
        assert "<EndToEndId>E2E-MIN</EndToEndId>" in xml


# ── Parametrized full tests (all optional elements, all 13 versions) ─


class TestFullXsdValid:
    """Every version must produce valid XML with all optional elements."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_full_data_validates(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        # Common optional elements present
        assert "<InstrId>INSTR-001</InstrId>" in xml
        assert "<InstdAmt" in xml
        assert "<XchgRate>" in xml
        assert "<UltmtDbtr>" in xml
        assert "<UltmtCdtr>" in xml
        assert "<IntrmyAgt1>" in xml
        assert "<InstrForCdtrAgt>" in xml
        assert "<InstrForNxtAgt>" in xml
        assert "<Purp>" in xml
        assert "<ChrgsInf>" in xml
        assert "<PmtTpInf>" in xml
        assert "<CtrlSum>" in xml
        assert "<InstgAgt>" in xml
        assert "<InstdAgt>" in xml
        assert "<TtlIntrBkSttlmAmt" in xml


# ── Multi-transaction tests ──────────────────────────────────────────


class TestMultiTransaction:
    """Multiple transactions in a single message must validate."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_two_transactions(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert xml.count("<CdtTrfTxInf>") == 2
        assert "E2E-FULL-001" in xml
        assert "E2E-FULL-002" in xml


# ── BIC vs BICFI element tests ───────────────────────────────────────


class TestBicIdentifierElements:
    """v01-v02 use <BIC>, v03+ use <BICFI>."""

    @pytest.mark.parametrize("v", BIC_VERSIONS)
    def test_bic_tag_present(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<BIC>" in xml
        assert "<BICFI>" not in xml

    @pytest.mark.parametrize("v", BICFI_VERSIONS)
    def test_bicfi_tag_present(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<BICFI>" in xml


# ── UETR element tests ──────────────────────────────────────────────


class TestUetrElement:
    """UETR must appear in v08+ when provided."""

    @pytest.mark.parametrize("v", UETR_VERSIONS)
    def test_uetr_in_xml(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<UETR>a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d</UETR>" in xml


# ── MndtRltdInf element tests ───────────────────────────────────────


class TestMandateElement:
    """MndtRltdInf must appear in v10+ when mandate_id provided."""

    @pytest.mark.parametrize("v", MANDATE_VERSIONS)
    def test_mandate_in_xml(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<MndtRltdInf>" in xml
        assert "<MndtId>MNDT-FULL-001</MndtId>" in xml


# ── XpryDtTm element test ───────────────────────────────────────────


class TestExpiryElement:
    def test_expiry_in_v13(self):
        v = "pacs.008.001.13"
        t, x = _paths(v)
        xml = generate_xml_string(_full(13), v, t, x)
        assert "<XpryDtTm>2026-12-31T23:59:59</XpryDtTm>" in xml


# ── ClrSysRef element tests ─────────────────────────────────────────


class TestClrSysRefElement:
    """ClrSysRef must appear in v02+ when provided."""

    @pytest.mark.parametrize("v", CLR_SYS_REF_VERSIONS)
    def test_clr_sys_ref_in_xml(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<ClrSysRef>CLR-REF-001</ClrSysRef>" in xml


# ── SttlmPrty element tests ─────────────────────────────────────────


class TestSttlmPrtyElement:
    """Settlement priority appears in v02+."""

    @pytest.mark.parametrize("v", STTLM_PRTY_VERSIONS)
    def test_sttlm_prty_in_xml(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<SttlmPrty>NORM</SttlmPrty>" in xml


# ── PrvsInstgAgt naming tests ───────────────────────────────────────


class TestPrvsInstgAgtNaming:
    """v01-v06 use unnumbered, v07+ use numbered PrvsInstgAgt."""

    @pytest.mark.parametrize("v", UNNUMBERED_PRVS_VERSIONS)
    def test_unnumbered_prvs_instg_agt(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<PrvsInstgAgt>" in xml
        assert "<PrvsInstgAgt1>" not in xml

    @pytest.mark.parametrize("v", NUMBERED_PRVS_VERSIONS)
    def test_numbered_prvs_instg_agt(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<PrvsInstgAgt1>" in xml


# ── ChrgsInf structure tests ────────────────────────────────────────


class TestChrgsInfStructure:
    """v01: ChrgsAmt/ChrgsPty, v02: Amt/Pty, v03+: Amt/Agt."""

    def test_v01_chrgs_amt_chrgs_pty(self):
        v = "pacs.008.001.01"
        t, x = _paths(v)
        xml = generate_xml_string(_full(1), v, t, x)
        assert "<ChrgsAmt" in xml
        assert "<ChrgsPty>" in xml

    def test_v02_amt_pty(self):
        v = "pacs.008.001.02"
        t, x = _paths(v)
        xml = generate_xml_string(_full(2), v, t, x)
        assert "<ChrgsInf>" in xml
        assert "<Pty>" in xml

    @pytest.mark.parametrize(
        "v", [f"pacs.008.001.{i:02d}" for i in range(3, 14)]
    )
    def test_v03_plus_amt_agt(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        xml = generate_xml_string(_full(v_num), v, t, x)
        assert "<ChrgsInf>" in xml
        assert "<Agt>" in xml


# ── Cross-currency payment tests ────────────────────────────────────


class TestCrossCurrencyPayment:
    """FX payments with InstdAmt + XchgRate must validate."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_fx_payment(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["instd_amount"] = "24000.00"
        d["instd_currency"] = "GBP"
        d["xchg_rate"] = "0.8567"
        xml = generate_xml_string([d], v, t, x)
        assert 'Ccy="GBP"' in xml
        assert "<XchgRate>0.8567</XchgRate>" in xml


# ── Settlement method variants ──────────────────────────────────────


class TestSettlementMethodVariants:
    """All settlement methods must validate for every version."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    @pytest.mark.parametrize("method", ["CLRG", "INDA", "COVE", "INGA"])
    def test_settlement_method(self, v, method):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["settlement_method"] = method
        xml = generate_xml_string([d], v, t, x)
        assert f"<SttlmMtd>{method}</SttlmMtd>" in xml


# ── Charge bearer variants ──────────────────────────────────────────


class TestChargeBearerVariants:
    """All charge bearers must validate for every version."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    @pytest.mark.parametrize("bearer", ["DEBT", "CRED", "SHAR", "SLEV"])
    def test_charge_bearer(self, v, bearer):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["charge_bearer"] = bearer
        xml = generate_xml_string([d], v, t, x)
        assert f"<ChrgBr>{bearer}</ChrgBr>" in xml


# ── Currency variants ────────────────────────────────────────────────


class TestCurrencyVariants:
    """Multiple currencies must validate for every version."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    @pytest.mark.parametrize("ccy", ["EUR", "USD", "GBP", "CHF", "JPY"])
    def test_currency(self, v, ccy):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["interbank_settlement_currency"] = ccy
        xml = generate_xml_string([d], v, t, x)
        assert f'Ccy="{ccy}"' in xml


# ── Regulatory reporting tests ──────────────────────────────────────


class TestRegulatoryReporting:
    """RgltryRptg element must validate with full details."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_regulatory_reporting(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["rgltry_rptg_cd"] = "R01" if v_num == 1 else "RR01"
        d["rgltry_rptg_dbt_cdt_rptg_ind"] = "DEBT"
        d["rgltry_rptg_authrty_nm"] = "Financial Authority"
        d["rgltry_rptg_authrty_ctry"] = "DE"
        d["rgltry_rptg_inf"] = "Cross-border payment"
        xml = generate_xml_string([d], v, t, x)
        assert "<RgltryRptg>" in xml
        assert "<DbtCdtRptgInd>DEBT</DbtCdtRptgInd>" in xml
        assert "<Authrty>" in xml


# ── Payment type information tests ──────────────────────────────────


class TestPaymentTypeInfo:
    """PmtTpInf with various sub-elements must validate."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_pmt_tp_inf_service_level(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["pmt_tp_inf_svc_lvl_cd"] = "SDVA"
        xml = generate_xml_string([d], v, t, x)
        assert "<PmtTpInf>" in xml
        assert "<SvcLvl><Cd>SDVA</Cd></SvcLvl>" in xml

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_pmt_tp_inf_instruction_priority(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["pmt_tp_inf_instr_prty"] = "HIGH"
        xml = generate_xml_string([d], v, t, x)
        assert "<InstrPrty>HIGH</InstrPrty>" in xml


# ── Intermediary agent chain tests ──────────────────────────────────


class TestIntermediaryAgentChain:
    """Multiple intermediary agents must validate."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_three_intermediary_agents(self, v):
        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["intermediary_agent1_bic"] = "CHASUS33"
        d["intermediary_agent2_bic"] = "BNPAFRPP"
        d["intermediary_agent3_bic"] = "BARCGB22"
        xml = generate_xml_string([d], v, t, x)
        assert "<IntrmyAgt1>" in xml
        assert "<IntrmyAgt2>" in xml
        assert "<IntrmyAgt3>" in xml


# ── SWIFT compliance integration ─────────────────────────────────────


class TestSwiftComplianceIntegration:
    """SWIFT-cleansed data must produce valid XML for all versions."""

    @pytest.mark.parametrize("v", ALL_VERSIONS)
    def test_cleansed_data_validates(self, v):
        from pacs008.compliance import cleanse_data

        t, x = _paths(v)
        v_num = int(v.split(".")[-1])
        d = _minimal(v_num)[0]
        d["debtor_name"] = "Müller & Söhne™ GmbH"
        d["creditor_name"] = "García Café SL"
        d["remittance_information"] = "Invoice™ #123 — €500"
        cleansed = cleanse_data([d])
        xml = generate_xml_string(cleansed, v, t, x)
        assert "Muller" in xml or "Mueller" in xml
        assert "Garcia" in xml
