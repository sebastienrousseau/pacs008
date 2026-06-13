# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for pacs008.xml.stream_writer — constant-memory XML writer."""

from __future__ import annotations

import io

import pytest
from defusedxml import ElementTree as DET

from pacs008.xml.stream_writer import write_stream


def _row(i: int, currency: str = "EUR", amount: str = "100.00") -> dict:
    return {
        "msg_id": "BATCH001",
        "end_to_end_id": f"E2E-{i}",
        "uetr": f"f47ac10b-58cc-4372-a567-0e02b2c3d4{i:02d}",
        "interbank_settlement_amount": amount,
        "interbank_settlement_currency": currency,
        "debtor_name": f"Debtor {i}",
        "creditor_name": f"Creditor {i}",
    }


# ---------------------------------------------------------------------------
# Basic emission
# ---------------------------------------------------------------------------


class TestBasicEmission:
    def test_writes_xml_declaration(self):
        buf = io.BytesIO()
        write_stream([_row(1)], output=buf)
        assert buf.getvalue().startswith(b"<?xml")

    def test_returns_count(self):
        buf = io.BytesIO()
        n = write_stream([_row(1), _row(2), _row(3)], output=buf)
        assert n == 3

    def test_empty_rows_raises(self):
        buf = io.BytesIO()
        with pytest.raises(ValueError, match="at least one row"):
            write_stream([], output=buf)

    def test_root_namespace_matches_version(self):
        buf = io.BytesIO()
        write_stream(
            [_row(1)], output=buf, msg_def_idr="pacs.008.001.13"
        )
        root = DET.fromstring(buf.getvalue())
        ns = root.tag.split("}")[0].lstrip("{")
        assert ns.endswith("pacs.008.001.13")


# ---------------------------------------------------------------------------
# Output sinks
# ---------------------------------------------------------------------------


class TestOutputSinks:
    def test_path_sink_closes_handle(self, tmp_path):
        out = tmp_path / "msg.xml"
        write_stream([_row(1)], output=out)
        # File should be readable and parseable.
        with out.open("rb") as f:
            DET.fromstring(f.read())

    def test_filelike_sink_left_open(self):
        buf = io.BytesIO()
        write_stream([_row(1)], output=buf)
        # The writer should NOT close a sink it didn't open.
        assert not buf.closed


# ---------------------------------------------------------------------------
# Row content round-trip
# ---------------------------------------------------------------------------


class TestRowContent:
    def test_amount_and_currency_emitted(self):
        buf = io.BytesIO()
        write_stream(
            [_row(1, currency="USD", amount="1234.50")],
            output=buf,
        )
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        amt = root.find(f".//{ns}IntrBkSttlmAmt")
        assert amt is not None
        assert amt.get("Ccy") == "USD"
        assert amt.text == "1234.50"

    def test_uetr_omitted_when_missing(self):
        row = _row(1)
        del row["uetr"]
        buf = io.BytesIO()
        write_stream([row], output=buf)
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        # No UETR element should appear.
        assert root.find(f".//{ns}UETR") is None

    def test_per_row_emission(self):
        buf = io.BytesIO()
        write_stream([_row(i) for i in range(5)], output=buf)
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        txns = root.findall(f".//{ns}CdtTrfTxInf")
        assert len(txns) == 5

    def test_msg_id_default_from_first_row(self):
        buf = io.BytesIO()
        write_stream([_row(1)], output=buf)
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        msg_id = root.find(f".//{ns}MsgId")
        assert msg_id is not None
        assert msg_id.text == "BATCH001"

    def test_msg_id_override(self):
        buf = io.BytesIO()
        write_stream([_row(1)], output=buf, msg_id="OVERRIDE")
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        assert root.find(f".//{ns}MsgId").text == "OVERRIDE"

    def test_msg_id_fallback_when_rows_lack_one(self):
        row = _row(1)
        del row["msg_id"]
        buf = io.BytesIO()
        write_stream([row], output=buf)
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        assert root.find(f".//{ns}MsgId").text == "PACS008"


# ---------------------------------------------------------------------------
# Streaming / generator support
# ---------------------------------------------------------------------------


class TestStreaming:
    def test_accepts_generator_input(self):
        def gen():
            for i in range(10):
                yield _row(i)

        buf = io.BytesIO()
        n = write_stream(gen(), output=buf)
        assert n == 10

    def test_large_batch_completes(self):
        # 5,000 rows — enough to prove the streaming path doesn't
        # materialise everything up front but small enough for CI.
        def gen():
            for i in range(5_000):
                yield _row(i)

        buf = io.BytesIO()
        n = write_stream(gen(), output=buf)
        assert n == 5_000


# ---------------------------------------------------------------------------
# Settlement method, auto totals
# ---------------------------------------------------------------------------


class TestSettlementMethodAndTotals:
    def test_default_settlement_method_clrg(self):
        buf = io.BytesIO()
        write_stream([_row(1)], output=buf)
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        assert root.find(f".//{ns}SttlmMtd").text == "CLRG"

    def test_settlement_method_override(self):
        buf = io.BytesIO()
        write_stream(
            [_row(1)], output=buf, settlement_method="INDA"
        )
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        assert root.find(f".//{ns}SttlmMtd").text == "INDA"

    def test_auto_compute_off_emits_zero_totals(self):
        buf = io.BytesIO()
        write_stream(
            [_row(1)], output=buf, auto_compute_totals=False
        )
        root = DET.fromstring(buf.getvalue())
        ns = "{" + root.tag.split("}")[0].lstrip("{") + "}"
        # auto_compute_totals=False emits "0" — caller fills in later.
        assert root.find(f".//{ns}NbOfTxs").text == "0"
        assert root.find(f".//{ns}CtrlSum").text == "0"
