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

"""Inbound ISO 20022 XML dispatcher.

Most institutions only need to *generate* pacs.008. But round-trip
operations — handling pacs.002 status reports, pacs.004 returns,
camt.053 statements — require an inbound side. The
``go-fedwire`` library does this elegantly via ``AppHdr.MsgDefIdr``
dispatch; this module is the Python equivalent at the parse-and-
classify layer.

What :func:`parse` does:

1. XXE-safe parse via defusedxml.
2. If the root is a BAH-wrapped envelope (``BizMsgEnvlp``), read the
   ``MsgDefIdr`` directly and extract the BAH.
3. Otherwise, look at the root element's namespace URI for the
   ``pacs.008.001.08`` style identifier.
4. Return a :class:`ParsedMessage` carrying ``msg_def_idr``,
   ``msg_family``, ``version``, the optional BAH, and the local-name
   + namespace of the inner document root.

What :func:`parse` does NOT do:

- Build a typed model of the message body. That arrives with the
  v0.1.0 xsdata codegen pipeline. Today the caller still receives
  the lxml element via ``ParsedMessage.payload`` and walks it
  themselves.
- XSD validation. Callers wanting validation should pipe the
  payload through the existing ``validate_via_xsd`` helper.

Example::

    >>> from pacs008.xml.parser import parse
    >>> msg = parse(open("inbound.xml", "rb").read())
    >>> msg.msg_family, msg.version
    ('pacs.002', '001.10')
    >>> msg.bah.sender_bic if msg.bah else None
    'DEUTDEFF'
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Union

from defusedxml import ElementTree as DET

from pacs008.standards.bah import BusinessApplicationHeader, extract_bah_fields

# Envelope namespaces.
_NS_NVLP = "urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01"
_NS_BAH = "urn:iso:std:iso:20022:tech:xsd:head.001.001.02"

# Identifier shape inside the namespace URI.
_NS_IDENTIFIER = re.compile(
    r"(?P<family>[a-z]{4}\.\d{3})\.(?P<version>\d{3}\.\d{2,3})$"
)


class ParseError(ValueError):
    """Raised when the inbound XML cannot be parsed or classified."""


@dataclass(frozen=True)
class ParsedMessage:
    """Result of :func:`parse`.

    Attributes:
        msg_def_idr: Full message definition identifier
            (e.g. ``"pacs.008.001.08"``).
        msg_family: Family prefix (e.g. ``"pacs.008"``).
        version: Version suffix (e.g. ``"001.08"``).
        bah: The BAH if the message was envelope-wrapped, else
            ``None``.
        root_local_name: Local name of the inner document root
            (e.g. ``"Document"`` for most pacs/camt messages).
        namespace_uri: Namespace URI of the inner document root.
        envelope_wrapped: ``True`` iff the message was wrapped in
            ``BizMsgEnvlp``.
    """

    msg_def_idr: str
    msg_family: str
    version: str
    bah: Optional[BusinessApplicationHeader]
    root_local_name: str
    namespace_uri: str
    envelope_wrapped: bool


def parse(xml: Union[str, bytes]) -> ParsedMessage:
    """Parse and classify an inbound ISO 20022 XML message.

    Args:
        xml: The XML payload as ``str`` or ``bytes``.

    Returns:
        :class:`ParsedMessage` with the classification fields
        populated.

    Raises:
        ParseError: if the XML is malformed or the
            ``MsgDefIdr`` / namespace cannot be identified.
    """
    if isinstance(xml, str):
        xml_bytes = xml.encode("utf-8")
    else:
        xml_bytes = bytes(xml)

    try:
        root = DET.fromstring(xml_bytes)
    except Exception as exc:
        raise ParseError(f"malformed XML: {exc}") from exc

    namespace_uri, local_name = _split_qname(root.tag)

    if namespace_uri == _NS_NVLP and local_name == "BizMsgEnvlp":
        return _parse_envelope(xml.decode("utf-8") if isinstance(xml, bytes) else xml, root)

    return _parse_unwrapped(root, namespace_uri, local_name)


# ---------------------------------------------------------------------------
# Envelope vs unwrapped flows
# ---------------------------------------------------------------------------


def _parse_envelope(envelope_xml: str, root) -> ParsedMessage:
    """Classify a BAH-wrapped envelope."""
    bah = extract_bah_fields(envelope_xml)
    msg_def_idr = bah.msg_def_idr
    family, version = _split_msg_def_idr(msg_def_idr)

    doc = root.find(f"{{{_NS_NVLP}}}Doc")
    if doc is None or len(list(doc)) == 0:
        raise ParseError("envelope Doc element is empty")
    inner = list(doc)[0]
    ns, local = _split_qname(inner.tag)

    return ParsedMessage(
        msg_def_idr=msg_def_idr,
        msg_family=family,
        version=version,
        bah=bah,
        root_local_name=local,
        namespace_uri=ns,
        envelope_wrapped=True,
    )


def _parse_unwrapped(
    root, namespace_uri: str, local_name: str
) -> ParsedMessage:
    """Classify an unwrapped Document element by namespace URI."""
    match = _NS_IDENTIFIER.search(namespace_uri)
    if match is None:
        raise ParseError(
            "could not extract msg_def_idr from root namespace "
            f"{namespace_uri!r}"
        )
    family = match.group("family")
    version = match.group("version")
    msg_def_idr = f"{family}.{version}"

    return ParsedMessage(
        msg_def_idr=msg_def_idr,
        msg_family=family,
        version=version,
        bah=None,
        root_local_name=local_name,
        namespace_uri=namespace_uri,
        envelope_wrapped=False,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_qname(tag: str) -> tuple[str, str]:
    """Split a ``{namespace}LocalName`` tag into its parts."""
    if tag.startswith("{"):
        ns, local = tag[1:].split("}", 1)
        return ns, local
    return "", tag


def _split_msg_def_idr(msg_def_idr: str) -> tuple[str, str]:
    """Split ``"pacs.008.001.08"`` into ``("pacs.008", "001.08")``."""
    match = _NS_IDENTIFIER.search(msg_def_idr)
    if match is None:
        raise ParseError(
            f"malformed msg_def_idr {msg_def_idr!r}; "
            "expected <family>.<version> like 'pacs.008.001.08'"
        )
    return match.group("family"), match.group("version")
