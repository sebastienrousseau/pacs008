"""Tests for the 7 additional pacs message types (non-008)."""



from pacs008.constants import TEMPLATES_DIR
from pacs008.xml.generate_xml import generate_xml_string


def _paths(version):
    tpl = str(TEMPLATES_DIR / version / "template.xml")
    xsd = str(TEMPLATES_DIR / version / f"{version}.xsd")
    return tpl, xsd


def _generate(version, data):
    tpl, xsd = _paths(version)
    return generate_xml_string(data, version, tpl, xsd)


# --- pacs.002.001.12 (Payment Status Report) ---


class TestPacs002:
    VERSION = "pacs.002.001.12"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-STS-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "original_msg_id": "MSG-ORIG-001",
            "original_msg_nm_id": "pacs.008.001.13",
            "original_end_to_end_id": "E2E-ORIG-001",
            "original_tx_id": "TX-ORIG-001",
            "tx_sts": "ACSC",
            "sts_rsn_cd": "AB05",
            "sts_rsn_addtl_inf": "Accepted",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FIToFIPmtStsRpt>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.12" in xml

    def test_msg_id_present(self):
        xml = _generate(self.VERSION, self._data())
        assert "<MsgId>MSG-STS-001</MsgId>" in xml

    def test_original_msg_id(self):
        xml = _generate(self.VERSION, self._data())
        assert "<OrgnlMsgId>MSG-ORIG-001</OrgnlMsgId>" in xml

    def test_tx_status(self):
        xml = _generate(self.VERSION, self._data())
        assert "<TxSts>ACSC</TxSts>" in xml

    def test_status_reason(self):
        xml = _generate(self.VERSION, self._data())
        assert "<Cd>AB05</Cd>" in xml

    def test_optional_agents(self):
        xml = _generate(
            self.VERSION,
            self._data(instg_agt_bic="DEUTDEFF", instd_agt_bic="COBADEFF"),
        )
        assert "<BICFI>DEUTDEFF</BICFI>" in xml
        assert "<BICFI>COBADEFF</BICFI>" in xml

    def test_group_status(self):
        xml = _generate(self.VERSION, self._data(grp_sts="ACSC"))
        assert "<GrpSts>ACSC</GrpSts>" in xml

    def test_multiple_transactions(self):
        data = self._data()
        row2 = dict(data[0])
        row2["original_end_to_end_id"] = "E2E-ORIG-002"
        row2["tx_sts"] = "RJCT"
        data.append(row2)
        xml = _generate(self.VERSION, data)
        assert xml.count("<TxInfAndSts>") == 2


# --- pacs.003.001.09 (Customer Direct Debit) ---


class TestPacs003:
    VERSION = "pacs.003.001.09"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-DD-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-DD-001",
            "tx_id": "TX-DD-001",
            "interbank_settlement_amount": "500.00",
            "interbank_settlement_currency": "EUR",
            "charge_bearer": "SLEV",
            "mandate_id": "MNDT-DD-001",
            "seq_tp": "RCUR",
            "debtor_name": "Debtor Corp",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
            "creditor_name": "Creditor Ltd",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FIToFICstmrDrctDbt>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.003.001.09" in xml

    def test_mandate_id(self):
        xml = _generate(self.VERSION, self._data())
        assert "<MndtId>MNDT-DD-001</MndtId>" in xml

    def test_direct_debit_structure(self):
        xml = _generate(self.VERSION, self._data())
        assert "<DrctDbtTxInf>" in xml
        assert "<DrctDbtTx>" in xml

    def test_settlement_method(self):
        xml = _generate(self.VERSION, self._data())
        assert "<SttlmMtd>CLRG</SttlmMtd>" in xml

    def test_debtor_creditor(self):
        xml = _generate(self.VERSION, self._data())
        assert "<Nm>Debtor Corp</Nm>" in xml
        assert "<Nm>Creditor Ltd</Nm>" in xml

    def test_interbank_amount(self):
        xml = _generate(self.VERSION, self._data())
        assert "500.00" in xml


# --- pacs.004.001.11 (Payment Return) ---


class TestPacs004:
    VERSION = "pacs.004.001.11"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-RTR-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "original_msg_id": "MSG-ORIG-001",
            "original_msg_nm_id": "pacs.008.001.13",
            "original_end_to_end_id": "E2E-ORIG-001",
            "original_tx_id": "TX-ORIG-001",
            "returned_interbank_settlement_amount": "1000.00",
            "returned_interbank_settlement_currency": "EUR",
            "return_reason_cd": "AC01",
            "return_reason_addtl_inf": "Account invalid",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<PmtRtr>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.004.001.11" in xml

    def test_return_amount(self):
        xml = _generate(self.VERSION, self._data())
        assert "<RtrdIntrBkSttlmAmt" in xml
        assert "1000.00" in xml

    def test_return_reason(self):
        xml = _generate(self.VERSION, self._data())
        assert "<Cd>AC01</Cd>" in xml

    def test_original_group_info(self):
        xml = _generate(self.VERSION, self._data())
        assert "<OrgnlMsgId>MSG-ORIG-001</OrgnlMsgId>" in xml
        assert "<OrgnlMsgNmId>pacs.008.001.13</OrgnlMsgNmId>" in xml

    def test_multiple_returns(self):
        data = self._data()
        row2 = dict(data[0])
        row2["original_end_to_end_id"] = "E2E-ORIG-002"
        row2["return_reason_cd"] = "AM04"
        data.append(row2)
        xml = _generate(self.VERSION, data)
        assert xml.count("<TxInf>") == 2


# --- pacs.007.001.11 (Payment Reversal) ---


class TestPacs007:
    VERSION = "pacs.007.001.11"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-RVSL-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "original_msg_id": "MSG-ORIG-001",
            "original_msg_nm_id": "pacs.008.001.13",
            "original_end_to_end_id": "E2E-ORIG-001",
            "original_tx_id": "TX-ORIG-001",
            "reversed_interbank_settlement_amount": "1000.00",
            "reversed_interbank_settlement_currency": "EUR",
            "reversal_reason_cd": "DUPL",
            "reversal_reason_addtl_inf": "Duplicate payment",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FIToFIPmtRvsl>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.007.001.11" in xml

    def test_reversed_amount(self):
        xml = _generate(self.VERSION, self._data())
        assert "<RvsdIntrBkSttlmAmt" in xml
        assert "1000.00" in xml

    def test_reversal_reason(self):
        xml = _generate(self.VERSION, self._data())
        assert "<Cd>DUPL</Cd>" in xml

    def test_original_group_info(self):
        xml = _generate(self.VERSION, self._data())
        assert "<OrgnlMsgId>MSG-ORIG-001</OrgnlMsgId>" in xml


# --- pacs.009.001.10 (FI Credit Transfer) ---


class TestPacs009:
    VERSION = "pacs.009.001.10"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-FICTRF-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-FICTRF-001",
            "tx_id": "TX-FICTRF-001",
            "interbank_settlement_amount": "50000.00",
            "interbank_settlement_currency": "EUR",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FICdtTrf>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.10" in xml

    def test_settlement_method(self):
        xml = _generate(self.VERSION, self._data())
        assert "<SttlmMtd>CLRG</SttlmMtd>" in xml

    def test_agent_bics(self):
        xml = _generate(self.VERSION, self._data())
        assert "<BICFI>DEUTDEFF</BICFI>" in xml
        assert "<BICFI>COBADEFF</BICFI>" in xml

    def test_interbank_amount(self):
        xml = _generate(self.VERSION, self._data())
        assert "50000.00" in xml

    def test_intermediary_agent(self):
        xml = _generate(
            self.VERSION,
            self._data(intermediary_agent1_bic="BNPAFRPP"),
        )
        assert "<BICFI>BNPAFRPP</BICFI>" in xml


# --- pacs.010.001.05 (FI Direct Debit) ---


class TestPacs010:
    VERSION = "pacs.010.001.05"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-FIDD-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "nb_of_txs": "1",
            "settlement_method": "CLRG",
            "interbank_settlement_date": "2026-01-15",
            "end_to_end_id": "E2E-FIDD-001",
            "tx_id": "TX-FIDD-001",
            "interbank_settlement_amount": "25000.00",
            "interbank_settlement_currency": "EUR",
            "debtor_agent_bic": "DEUTDEFF",
            "creditor_agent_bic": "COBADEFF",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FIDrctDbt>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.010.001.05" in xml

    def test_settlement_method(self):
        xml = _generate(self.VERSION, self._data())
        assert "<SttlmMtd>CLRG</SttlmMtd>" in xml

    def test_interbank_amount(self):
        xml = _generate(self.VERSION, self._data())
        assert "25000.00" in xml


# --- pacs.028.001.05 (Payment Status Request) ---


class TestPacs028:
    VERSION = "pacs.028.001.05"

    def _data(self, **overrides):
        row = {
            "msg_id": "MSG-STSREQ-001",
            "creation_date_time": "2026-01-15T10:30:00",
            "original_msg_id": "MSG-ORIG-001",
            "original_msg_nm_id": "pacs.008.001.13",
            "original_end_to_end_id": "E2E-ORIG-001",
            "original_tx_id": "TX-ORIG-001",
        }
        row.update(overrides)
        return [row]

    def test_generates_valid_xml(self):
        xml = _generate(self.VERSION, self._data())
        assert "<FIToFIPmtStsReq>" in xml

    def test_contains_namespace(self):
        xml = _generate(self.VERSION, self._data())
        assert "urn:iso:std:iso:20022:tech:xsd:pacs.028.001.05" in xml

    def test_msg_id(self):
        xml = _generate(self.VERSION, self._data())
        assert "<MsgId>MSG-STSREQ-001</MsgId>" in xml

    def test_original_msg_id(self):
        xml = _generate(self.VERSION, self._data())
        assert "<OrgnlMsgId>MSG-ORIG-001</OrgnlMsgId>" in xml

    def test_original_end_to_end_id(self):
        xml = _generate(self.VERSION, self._data())
        assert "<OrgnlEndToEndId>E2E-ORIG-001</OrgnlEndToEndId>" in xml

    def test_optional_agents(self):
        xml = _generate(
            self.VERSION,
            self._data(instg_agt_bic="DEUTDEFF", instd_agt_bic="COBADEFF"),
        )
        assert "<BICFI>DEUTDEFF</BICFI>" in xml

    def test_multiple_tx_inquiries(self):
        data = self._data()
        row2 = dict(data[0])
        row2["original_end_to_end_id"] = "E2E-ORIG-002"
        data.append(row2)
        xml = _generate(self.VERSION, data)
        assert xml.count("<TxInf>") == 2
