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

"""Tests for pacs008.xml.parser — inbound dispatch via MsgDefIdr / namespace."""

from __future__ import annotations

import pytest

from pacs008.standards.bah import wrap_in_bah
from pacs008.xml.parser import ParseError, parse


def _unwrapped(family: str, version: str, root_local: str = "Document") -> str:
    msg_def = f"{family}.{version}"
    return (
        f'<{root_local} xmlns="urn:iso:std:iso:20022:tech:xsd:{msg_def}">'
        "<FIToFICstmrCdtTrf/>"
        f"</{root_local}>"
    )


# ---------------------------------------------------------------------------
# Unwrapped Document classification
# ---------------------------------------------------------------------------


class TestUnwrappedClassification:
    @pytest.mark.parametrize(
        "family,version",
        [
            ("pacs.008", "001.08"),
            ("pacs.008", "001.13"),
            ("pacs.002", "001.10"),
            ("pacs.004", "001.11"),
            ("camt.053", "001.08"),
            ("camt.029", "001.09"),
            ("pain.001", "001.12"),
        ],
    )
    def test_namespace_based_dispatch(self, family, version):
        msg = parse(_unwrapped(family, version))
        assert msg.msg_family == family
        assert msg.version == version
        assert msg.msg_def_idr == f"{family}.{version}"
        assert msg.envelope_wrapped is False
        assert msg.bah is None
        assert msg.root_local_name == "Document"

    def test_string_input_accepted(self):
        msg = parse(_unwrapped("pacs.008", "001.08"))
        assert msg.msg_family == "pacs.008"

    def test_bytes_input_accepted(self):
        msg = parse(_unwrapped("pacs.008", "001.08").encode("utf-8"))
        assert msg.msg_family == "pacs.008"

    def test_three_digit_subversion(self):
        # Some message versions use a three-digit subversion.
        msg = parse(_unwrapped("pacs.002", "001.012"))
        assert msg.version == "001.012"

    def test_xml_declaration_tolerated(self):
        x = '<?xml version="1.0"?>' + _unwrapped("pacs.008", "001.08")
        msg = parse(x)
        assert msg.msg_family == "pacs.008"


# ---------------------------------------------------------------------------
# BAH-wrapped envelope dispatch
# ---------------------------------------------------------------------------


class TestEnvelopeDispatch:
    def test_msg_def_idr_taken_from_bah(self):
        inner = _unwrapped("pacs.008", "001.08")
        envelope = wrap_in_bah(
            inner,
            sender_bic="HSBCGB2L",
            receiver_bic="DEUTDEFF",
            biz_msg_idr="BIZ-1",
            msg_def_idr="pacs.008.001.08",
            creation_dt="2026-06-13T12:00:00Z",
        )
        msg = parse(envelope)
        assert msg.envelope_wrapped is True
        assert msg.msg_def_idr == "pacs.008.001.08"
        assert msg.bah is not None
        assert msg.bah.sender_bic == "HSBCGB2L"
        assert msg.bah.biz_msg_idr == "BIZ-1"

    def test_inner_root_classified(self):
        inner = _unwrapped("pacs.002", "001.10")
        envelope = wrap_in_bah(
            inner,
            sender_bic="HSBCGB2L",
            receiver_bic="DEUTDEFF",
            biz_msg_idr="BIZ-2",
            msg_def_idr="pacs.002.001.10",
            creation_dt="2026-06-13T12:00:00Z",
        )
        msg = parse(envelope)
        assert msg.msg_family == "pacs.002"
        assert msg.root_local_name == "Document"

    def test_envelope_with_empty_doc_raises(self):
        empty_doc_envelope = (
            '<?xml version="1.0"?>'
            '<BizMsgEnvlp xmlns="urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01">'
            "<Hdr>"
            '<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">'
            "<Fr><FIId><FinInstnId><BICFI>HSBCGB2L</BICFI></FinInstnId></FIId></Fr>"
            "<To><FIId><FinInstnId><BICFI>DEUTDEFF</BICFI></FinInstnId></FIId></To>"
            "<BizMsgIdr>BIZ-1</BizMsgIdr>"
            "<MsgDefIdr>pacs.008.001.08</MsgDefIdr>"
            "<CreDt>2026-06-13T12:00:00Z</CreDt>"
            "</AppHdr>"
            "</Hdr>"
            "<Doc/>"
            "</BizMsgEnvlp>"
        )
        with pytest.raises(ParseError, match="empty"):
            parse(empty_doc_envelope)


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class TestFailures:
    def test_malformed_xml_raises_parse_error(self):
        with pytest.raises(ParseError, match="malformed"):
            parse("<not-closed")

    def test_unknown_namespace_raises(self):
        x = (
            '<Document xmlns="https://example.com/random/namespace">'
            "<Body/></Document>"
        )
        with pytest.raises(ParseError, match="msg_def_idr"):
            parse(x)

    def test_no_namespace_raises(self):
        x = "<Document><Body/></Document>"
        with pytest.raises(ParseError, match="msg_def_idr"):
            parse(x)


# ---------------------------------------------------------------------------
# ParsedMessage dataclass
# ---------------------------------------------------------------------------


class TestParsedMessageImmutability:
    def test_frozen(self):
        msg = parse(_unwrapped("pacs.008", "001.08"))
        with pytest.raises(Exception):
            msg.msg_family = "OTHER"  # type: ignore[misc]
