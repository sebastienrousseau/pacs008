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

"""Tests for pacs008.standards.bah (Business Application Header wrapping)."""

from __future__ import annotations

import pytest
from defusedxml import ElementTree as DET

from pacs008.standards.bah import (
    BusinessApplicationHeader,
    extract_bah_fields,
    wrap_in_bah,
)

_PAYLOAD = (
    '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">'
    "<FIToFICstmrCdtTrf>"
    "<GrpHdr><MsgId>BATCH001</MsgId></GrpHdr>"
    "</FIToFICstmrCdtTrf>"
    "</Document>"
)

_KW = dict(
    sender_bic="HSBCGB2L",
    receiver_bic="DEUTDEFF",
    biz_msg_idr="BIZMSG-2026-001",
    msg_def_idr="pacs.008.001.08",
    creation_dt="2026-06-13T12:00:00Z",
)


# ---------------------------------------------------------------------------
# BusinessApplicationHeader validation
# ---------------------------------------------------------------------------


class TestHeaderValidation:
    def test_round_trip_minimal(self):
        h = BusinessApplicationHeader(**_KW)
        assert h.sender_bic == "HSBCGB2L"
        assert h.priority is None

    def test_invalid_sender_bic_rejected(self):
        with pytest.raises(ValueError, match="sender_bic"):
            BusinessApplicationHeader(**{**_KW, "sender_bic": "NOTABIC"})

    def test_invalid_receiver_bic_rejected(self):
        with pytest.raises(ValueError, match="receiver_bic"):
            BusinessApplicationHeader(**{**_KW, "receiver_bic": "12345"})

    def test_biz_msg_idr_empty_rejected(self):
        with pytest.raises(ValueError, match="biz_msg_idr"):
            BusinessApplicationHeader(**{**_KW, "biz_msg_idr": ""})

    def test_biz_msg_idr_too_long_rejected(self):
        with pytest.raises(ValueError, match="biz_msg_idr"):
            BusinessApplicationHeader(**{**_KW, "biz_msg_idr": "X" * 36})

    def test_msg_def_idr_malformed_rejected(self):
        with pytest.raises(ValueError, match="msg_def_idr"):
            BusinessApplicationHeader(**{**_KW, "msg_def_idr": "pacs.008"})

    def test_creation_dt_malformed_rejected(self):
        with pytest.raises(ValueError, match="ISO 8601"):
            BusinessApplicationHeader(**{**_KW, "creation_dt": "yesterday"})

    @pytest.mark.parametrize("p", ["HIGH", "NORM", "URGT"])
    def test_priority_accepts_valid_codes(self, p):
        h = BusinessApplicationHeader(**{**_KW, "priority": p})
        assert h.priority == p

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValueError, match="priority"):
            BusinessApplicationHeader(**{**_KW, "priority": "FAST"})

    def test_three_digit_version_accepted(self):
        # Some schemas use three-digit subversion (e.g. pacs.002.001.012)
        BusinessApplicationHeader(**{**_KW, "msg_def_idr": "pacs.002.001.012"})


# ---------------------------------------------------------------------------
# wrap_in_bah — structure
# ---------------------------------------------------------------------------


class TestWrapStructure:
    def test_returns_string_with_declaration(self):
        envelope = wrap_in_bah(_PAYLOAD, **_KW)
        assert envelope.startswith("<?xml")

    def test_root_is_biz_msg_envlp(self):
        envelope = wrap_in_bah(_PAYLOAD, **_KW)
        root = DET.fromstring(envelope)
        assert root.tag.endswith("BizMsgEnvlp")

    def test_root_namespace_is_nvlp(self):
        envelope = wrap_in_bah(_PAYLOAD, **_KW)
        root = DET.fromstring(envelope)
        ns = root.tag.split("}")[0].lstrip("{")
        assert ns == "urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01"

    def test_app_hdr_namespace_is_head(self):
        envelope = wrap_in_bah(_PAYLOAD, **_KW)
        root = DET.fromstring(envelope)
        nvlp = "{urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01}"
        bah = "{urn:iso:std:iso:20022:tech:xsd:head.001.001.02}"
        app_hdr = root.find(f"{nvlp}Hdr/{bah}AppHdr")
        assert app_hdr is not None

    def test_doc_contains_payload(self):
        envelope = wrap_in_bah(_PAYLOAD, **_KW)
        root = DET.fromstring(envelope)
        nvlp = "{urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01}"
        pacs = "{urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08}"
        doc = root.find(f"{nvlp}Doc/{pacs}Document")
        assert doc is not None

    def test_default_creation_dt_when_omitted(self):
        envelope = wrap_in_bah(
            _PAYLOAD,
            sender_bic="HSBCGB2L",
            receiver_bic="DEUTDEFF",
            biz_msg_idr="BIZMSG-001",
            msg_def_idr="pacs.008.001.08",
        )
        bah = extract_bah_fields(envelope)
        # Should look like ISO timestamp Z-suffixed.
        assert bah.creation_dt.endswith("Z")
        assert "T" in bah.creation_dt


# ---------------------------------------------------------------------------
# Optional fields
# ---------------------------------------------------------------------------


class TestOptionalFields:
    def test_priority_round_trips(self):
        envelope = wrap_in_bah(_PAYLOAD, **{**_KW, "priority": "URGT"})
        bah = extract_bah_fields(envelope)
        assert bah.priority == "URGT"

    def test_signature_embedded(self):
        sig = (
            '<Sgntr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">'
            "<X>placeholder</X>"
            "</Sgntr>"
        )
        envelope = wrap_in_bah(_PAYLOAD, **{**_KW, "signature": sig})
        # The Sgntr element should appear under AppHdr.
        root = DET.fromstring(envelope)
        bah = "{urn:iso:std:iso:20022:tech:xsd:head.001.001.02}"
        nvlp = "{urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01}"
        sgntr = root.find(f"{nvlp}Hdr/{bah}AppHdr/{bah}Sgntr")
        assert sgntr is not None


# ---------------------------------------------------------------------------
# extract_bah_fields — failure modes
# ---------------------------------------------------------------------------


class TestExtractionFailures:
    def test_missing_app_hdr_raises(self):
        bad = (
            '<?xml version="1.0"?>'
            '<BizMsgEnvlp xmlns="urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01">'
            "<Hdr/>"
            "<Doc/>"
            "</BizMsgEnvlp>"
        )
        with pytest.raises(ValueError, match="AppHdr"):
            extract_bah_fields(bad)

    def test_missing_required_child_raises(self):
        # Missing BizMsgIdr.
        envelope = (
            '<?xml version="1.0"?>'
            '<BizMsgEnvlp xmlns="urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01">'
            "<Hdr>"
            '<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">'
            "<Fr><FIId><FinInstnId><BICFI>HSBCGB2L</BICFI></FinInstnId></FIId></Fr>"
            "<To><FIId><FinInstnId><BICFI>DEUTDEFF</BICFI></FinInstnId></FIId></To>"
            "<MsgDefIdr>pacs.008.001.08</MsgDefIdr>"
            "<CreDt>2026-06-13T12:00:00Z</CreDt>"
            "</AppHdr>"
            "</Hdr>"
            "<Doc/>"
            "</BizMsgEnvlp>"
        )
        with pytest.raises(ValueError, match="BizMsgIdr"):
            extract_bah_fields(envelope)


# ---------------------------------------------------------------------------
# Full round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_extract_matches_input(self):
        envelope = wrap_in_bah(_PAYLOAD, **{**_KW, "priority": "NORM"})
        bah = extract_bah_fields(envelope)
        assert bah.sender_bic == _KW["sender_bic"]
        assert bah.receiver_bic == _KW["receiver_bic"]
        assert bah.biz_msg_idr == _KW["biz_msg_idr"]
        assert bah.msg_def_idr == _KW["msg_def_idr"]
        assert bah.creation_dt == _KW["creation_dt"]
        assert bah.priority == "NORM"
