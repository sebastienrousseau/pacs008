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

"""ISO 20022 Business Application Header (BAH / head.001) wrapping.

CBPR+, HVPS+ and most modern RTGS schemes require the pacs.008 (or
any business message) to be carried inside an envelope of:

- ``BizMsgEnvlp`` (``nvlp.001.001.01``) — the outer wrapper
- ``Hdr`` containing the ``AppHdr`` (``head.001.001.02``) — sender,
  receiver, business message identifier, message definition
  identifier, creation timestamp, optional priority/signature
- ``Doc`` containing the actual ``Document`` element

This module provides a small standalone wrapper:

- :class:`BusinessApplicationHeader` — frozen dataclass for the
  AppHdr fields.
- :func:`wrap_in_bah` — wrap a payload XML string in an envelope.
- :func:`extract_bah_fields` — pull the BAH back out of a wrapped
  envelope.

No xsdata models needed — the implementation uses lxml directly so
this works alongside the existing Jinja-template pipeline today.

References:
    - ISO 20022 — head.001.001.02 / .03 Business Application Header.
    - ISO 20022 — nvlp.001.001.01 Business Message Envelope.
    - SWIFT CBPR+ — *AppHdr Usage Guidelines UG2026*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from defusedxml import ElementTree as DET
from lxml import etree

from pacs008.validation.bic_validator import validate_bic_safe

# Namespaces used by the envelope.
_NS_NVLP = "urn:iso:std:iso:20022:tech:xsd:nvlp.001.001.01"
_NS_BAH = "urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
_NS_PAYLOAD_PREFIX = "urn:iso:std:iso:20022:tech:xsd:"

# Recognised priority codes per AppHdr (HIGH / NORM / URGT).
_VALID_PRIORITIES = frozenset({"HIGH", "NORM", "URGT"})

# Loose BizMsgIdr / MsgDefIdr format checks (35 / 35 chars max per spec).
_MAX_BIZ_MSG_IDR = 35
_MSG_DEF_IDR_PATTERN = re.compile(r"^[a-z]{4}\.\d{3}\.\d{3}\.\d{2,3}$")


@dataclass(frozen=True)
class BusinessApplicationHeader:
    """The AppHdr fields carried in head.001.001.02.

    Attributes:
        sender_bic: ISO 9362 BIC of the sending institution.
        receiver_bic: ISO 9362 BIC of the receiving institution.
        biz_msg_idr: Business message identifier (max 35 chars).
        msg_def_idr: Message definition identifier
            (e.g. ``"pacs.008.001.08"``).
        creation_dt: ISO 8601 timestamp of envelope creation.
        priority: Optional priority code (``HIGH``, ``NORM``, ``URGT``).
        signature: Optional pre-computed XML-Signature string. The
            wrapper does NOT sign on the caller's behalf — callers
            using XAdES / W3C DSig pass the rendered ``<Sgntr>``
            block here.
    """

    sender_bic: str
    receiver_bic: str
    biz_msg_idr: str
    msg_def_idr: str
    creation_dt: str
    priority: str | None = None
    signature: str | None = None

    def __post_init__(self) -> None:
        for label, bic in (
            ("sender_bic", self.sender_bic),
            ("receiver_bic", self.receiver_bic),
        ):
            if not validate_bic_safe(bic):
                raise ValueError(
                    f"{label} {bic!r} is not a valid ISO 9362 BIC"
                )

        if not self.biz_msg_idr or len(self.biz_msg_idr) > _MAX_BIZ_MSG_IDR:
            raise ValueError(
                "biz_msg_idr must be 1.."
                f"{_MAX_BIZ_MSG_IDR} characters; "
                f"got len={len(self.biz_msg_idr)}"
            )

        if not _MSG_DEF_IDR_PATTERN.match(self.msg_def_idr):
            raise ValueError(
                "msg_def_idr must look like 'pacs.008.001.08'; "
                f"got {self.msg_def_idr!r}"
            )

        try:
            datetime.fromisoformat(self.creation_dt.rstrip("Z"))
        except ValueError as exc:
            raise ValueError(
                f"creation_dt must be ISO 8601; got {self.creation_dt!r}"
            ) from exc

        if (
            self.priority is not None
            and self.priority not in _VALID_PRIORITIES
        ):
            raise ValueError(
                f"priority must be one of {sorted(_VALID_PRIORITIES)} "
                f"or None; got {self.priority!r}"
            )


def wrap_in_bah(
    payload_xml: str,
    *,
    sender_bic: str,
    receiver_bic: str,
    biz_msg_idr: str,
    msg_def_idr: str,
    creation_dt: str | None = None,
    priority: str | None = None,
    signature: str | None = None,
) -> str:
    """Wrap a payload XML string in a BizMsgEnvlp envelope.

    Args:
        payload_xml: The serialised business document (e.g. a
            pacs.008 Document element) as a string. The XML
            declaration, if any, is stripped before embedding.
        sender_bic: BIC of the sending FI.
        receiver_bic: BIC of the receiving FI.
        biz_msg_idr: Business message identifier.
        msg_def_idr: Message definition identifier
            (e.g. ``"pacs.008.001.08"``).
        creation_dt: ISO 8601 timestamp. Defaults to UTC now.
        priority: Optional ``HIGH`` / ``NORM`` / ``URGT``.
        signature: Optional pre-rendered ``<Sgntr>`` XML.

    Returns:
        The full envelope as a UTF-8 string with XML declaration.

    Raises:
        ValueError: if any BAH field is malformed.
    """
    resolved_credt = creation_dt or _utcnow_iso()

    header = BusinessApplicationHeader(
        sender_bic=sender_bic,
        receiver_bic=receiver_bic,
        biz_msg_idr=biz_msg_idr,
        msg_def_idr=msg_def_idr,
        creation_dt=resolved_credt,
        priority=priority,
        signature=signature,
    )

    nvlp_ns = f"{{{_NS_NVLP}}}"
    bah_ns = f"{{{_NS_BAH}}}"

    envelope = etree.Element(
        f"{nvlp_ns}BizMsgEnvlp",
        nsmap={None: _NS_NVLP},
    )
    hdr = etree.SubElement(envelope, f"{nvlp_ns}Hdr")
    app_hdr = etree.SubElement(
        hdr,
        f"{bah_ns}AppHdr",
        nsmap={None: _NS_BAH},
    )
    _populate_app_hdr(app_hdr, header, bah_ns)

    doc = etree.SubElement(envelope, f"{nvlp_ns}Doc")
    payload_root = _parse_payload(payload_xml)
    doc.append(payload_root)

    serialised: bytes = etree.tostring(
        envelope,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    return serialised.decode("utf-8")


def extract_bah_fields(
    envelope_xml: str,
) -> BusinessApplicationHeader:
    """Pull the BAH back out of a wrapped envelope.

    Tolerant of an envelope with or without an XML declaration. The
    payload is NOT returned — callers that need the inner document
    should use :func:`pacs008.xml.parser.parse`.

    Raises:
        ValueError: if the envelope is missing the AppHdr or any
            mandatory AppHdr child.
    """
    root = DET.fromstring(envelope_xml.encode("utf-8"))

    app_hdr = _find(root, f"{{{_NS_NVLP}}}Hdr/{{{_NS_BAH}}}AppHdr")
    if app_hdr is None:
        raise ValueError("envelope missing Hdr/AppHdr element")

    sender_bic = _find_text(
        app_hdr,
        f"{{{_NS_BAH}}}Fr/{{{_NS_BAH}}}FIId/{{{_NS_BAH}}}FinInstnId"
        f"/{{{_NS_BAH}}}BICFI",
    )
    receiver_bic = _find_text(
        app_hdr,
        f"{{{_NS_BAH}}}To/{{{_NS_BAH}}}FIId/{{{_NS_BAH}}}FinInstnId"
        f"/{{{_NS_BAH}}}BICFI",
    )
    biz_msg_idr = _find_text(app_hdr, f"{{{_NS_BAH}}}BizMsgIdr")
    msg_def_idr = _find_text(app_hdr, f"{{{_NS_BAH}}}MsgDefIdr")
    creation_dt = _find_text(app_hdr, f"{{{_NS_BAH}}}CreDt")
    priority = _find_text(app_hdr, f"{{{_NS_BAH}}}Prty", required=False)

    return BusinessApplicationHeader(
        sender_bic=sender_bic,
        receiver_bic=receiver_bic,
        biz_msg_idr=biz_msg_idr,
        msg_def_idr=msg_def_idr,
        creation_dt=creation_dt,
        priority=priority,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _populate_app_hdr(
    app_hdr: etree._Element,
    header: BusinessApplicationHeader,
    bah_ns: str,
) -> None:
    """Render the AppHdr children in canonical order."""
    fr = etree.SubElement(app_hdr, f"{bah_ns}Fr")
    fr_fi_id = etree.SubElement(fr, f"{bah_ns}FIId")
    fr_fin_id = etree.SubElement(fr_fi_id, f"{bah_ns}FinInstnId")
    etree.SubElement(fr_fin_id, f"{bah_ns}BICFI").text = header.sender_bic

    to = etree.SubElement(app_hdr, f"{bah_ns}To")
    to_fi_id = etree.SubElement(to, f"{bah_ns}FIId")
    to_fin_id = etree.SubElement(to_fi_id, f"{bah_ns}FinInstnId")
    etree.SubElement(to_fin_id, f"{bah_ns}BICFI").text = header.receiver_bic

    etree.SubElement(app_hdr, f"{bah_ns}BizMsgIdr").text = header.biz_msg_idr
    etree.SubElement(app_hdr, f"{bah_ns}MsgDefIdr").text = header.msg_def_idr
    etree.SubElement(app_hdr, f"{bah_ns}CreDt").text = header.creation_dt

    if header.priority is not None:
        etree.SubElement(app_hdr, f"{bah_ns}Prty").text = header.priority

    if header.signature is not None:
        # The signature payload is opaque XML — parse and append.
        sig_root = etree.fromstring(header.signature.encode("utf-8"))
        app_hdr.append(sig_root)


def _parse_payload(payload_xml: str) -> etree._Element:
    """Parse the inner Document element, stripping any XML declaration."""
    # lxml.etree.fromstring rejects XML declarations on bytes, so encode.
    return etree.fromstring(payload_xml.encode("utf-8"))


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find(root: Any, path: str) -> Any:
    return root.find(path)


def _find_text(root: Any, path: str, *, required: bool = True) -> str:
    el = root.find(path)
    if el is None or el.text is None:
        if required:
            raise ValueError(f"envelope missing {path}")
        return None  # type: ignore[return-value]
    return str(el.text)
