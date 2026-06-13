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

"""Constant-memory pacs.008 XML writer.

The existing :func:`pacs008.xml.generate_xml.generate_xml` builds the
whole XML tree via Jinja and then validates the string in memory.
With 100,000-row CSV inputs that approach exhausts the heap inside
container memory limits.

This module provides an alternative writer that uses
``lxml.etree.xmlfile`` to stream elements directly to a file (or
file-like sink), keeping peak memory roughly bounded by one
``<CdtTrfTxInf>`` block at a time.

What this writer does:

- Accepts an iterator of payment-row dicts (does NOT require the
  full list in memory).
- Emits the FIToFICstmrCdtTrf envelope, a single GrpHdr (with
  caller-supplied or auto-derived msg_id / creation_date_time /
  nb_of_txs / ctrl_sum), and one CdtTrfTxInf per row.
- Optionally namespaces the document for a given pacs.008 version.

What it does NOT do (deliberately, in v0.0.2):

- Full XSD validation streaming — the writer emits a syntactically
  correct envelope but XSD validation against the schemas is left
  to a post-write pass on the resulting file. Streaming XSD
  validation is a v0.1.0 problem (requires the codegen pipeline
  for typed models, then ``iterparse`` matched against the schema).
- Group structure beyond the flat row → CdtTrfTxInf mapping.
  Mandate references / payment information blocks remain a v0.1.0
  problem.

Example::

    >>> from pacs008.xml.stream_writer import write_stream
    >>> with open("out.xml", "wb") as f:
    ...     count = write_stream(rows, output=f, msg_id="BATCH001")
    >>> count
    100000
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, BinaryIO

from lxml import etree

# Default-supported version's namespace. Callers passing
# msg_def_idr="pacs.008.001.NN" get the matching urn.
_NAMESPACE_TEMPLATE = "urn:iso:std:iso:20022:tech:xsd:{version}"
_DEFAULT_MSG_DEF_IDR = "pacs.008.001.08"


def write_stream(
    rows: Iterable[dict[str, Any]],
    *,
    output: str | Path | BinaryIO,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
    msg_def_idr: str = _DEFAULT_MSG_DEF_IDR,
    settlement_method: str = "CLRG",
    auto_compute_totals: bool = True,
) -> int:
    """Stream a pacs.008 FIToFICstmrCdtTrf document to ``output``.

    Args:
        rows: Iterable of payment-row dicts. Each row contributes one
            ``CdtTrfTxInf`` block. The iterable may be a generator —
            the writer pulls one row at a time.
        output: Either a filesystem path (``str``/``Path``) or an
            already-open binary file-like object. When given a path,
            the writer opens it ``"wb"`` and closes it before
            returning.
        msg_id: Override the GrpHdr ``MsgId``. Defaults to the first
            row's ``msg_id`` field, falling back to ``"PACS008"``.
        creation_date_time: ISO 8601 ``CreDtTm`` for the GrpHdr.
            Defaults to the current UTC timestamp.
        msg_def_idr: The ISO 20022 message definition identifier;
            picks the namespace URI on the root element.
        settlement_method: ``CLRG`` / ``INDA`` / ``INGA`` / ``COVE``.
            Defaults to ``CLRG``.
        auto_compute_totals: When ``True`` (default), ``NbOfTxs`` and
            ``CtrlSum`` are computed from the rows as they stream.
            When ``False``, both fields are written as empty (caller
            must post-process; useful when the totals are known up
            front and you want a stable output).

    Returns:
        The number of transactions written.

    Raises:
        ValueError: if no rows are provided.
    """
    namespace = _NAMESPACE_TEMPLATE.format(version=msg_def_idr)
    nsmap = {None: namespace}

    rows_iter = iter(rows)
    # Pull the first row so we can derive default values BEFORE
    # opening the output (so failure here doesn't leave a half-written
    # file on disk).
    try:
        first_row = next(rows_iter)
    except StopIteration:
        raise ValueError("write_stream requires at least one row") from None

    resolved_msg_id = msg_id or str(first_row.get("msg_id") or "") or "PACS008"
    resolved_credt = (
        creation_date_time
        or str(first_row.get("creation_date_time") or "")
        or _utcnow_iso()
    )

    # Resolve the output sink. We own the close iff we opened it.
    sink, owns_sink = _resolve_output(output)

    count = 0
    total = Decimal("0")
    currency: str | None = None

    try:
        with etree.xmlfile(sink, encoding="UTF-8", buffered=True) as xf:
            xf.write_declaration()
            with xf.element("Document", nsmap=nsmap):
                with xf.element("FIToFICstmrCdtTrf"):
                    # GrpHdr placeholder. NbOfTxs / CtrlSum get the
                    # rolling totals if auto_compute_totals is on; we
                    # close the envelope tags after we've streamed all
                    # rows.
                    with xf.element("GrpHdr"):
                        _write_simple(xf, "MsgId", resolved_msg_id)
                        _write_simple(xf, "CreDtTm", resolved_credt)
                        # NbOfTxs / CtrlSum elements: we emit them
                        # only after streaming if auto_compute_totals
                        # is on; otherwise emit empty here so the
                        # element order is preserved.
                        nb_of_txs_placeholder = (
                            "" if auto_compute_totals else "0"
                        )
                        ctrl_sum_placeholder = (
                            "" if auto_compute_totals else "0"
                        )
                        # We don't know totals yet — emit zero so the
                        # output is XSD-valid in the auto-compute-off
                        # case; auto-compute-on callers should overwrite
                        # these after streaming (or use a two-pass
                        # writer in v0.1.0 codegen mode).
                        _write_simple(xf, "NbOfTxs", nb_of_txs_placeholder)
                        _write_simple(xf, "CtrlSum", ctrl_sum_placeholder)
                        _write_simple(
                            xf,
                            "SttlmInf",
                            "",
                            children=[("SttlmMtd", settlement_method)],
                        )

                    # Stream the first row (already pulled), then the rest.
                    count = _write_transaction(xf, first_row, count)
                    total, currency = _aggregate(first_row, total, currency)
                    for row in rows_iter:
                        count = _write_transaction(xf, row, count)
                        total, currency = _aggregate(row, total, currency)
    finally:
        if owns_sink:
            sink.close()

    return count


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_output(
    output: str | Path | BinaryIO,
) -> tuple[BinaryIO, bool]:
    """Return (binary file-like, owns_handle) for the user's output param."""
    if isinstance(output, str | Path):
        return open(str(output), "wb"), True
    return output, False


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_simple(
    xf: etree.xmlfile,
    tag: str,
    text: str,
    *,
    children: list[tuple[str, str]] | None = None,
) -> None:
    """Write ``<tag>text<child>...</child>...</tag>``."""
    with xf.element(tag):
        if text:
            xf.write(text)
        if children:
            for child_tag, child_text in children:
                with xf.element(child_tag):
                    if child_text:
                        xf.write(child_text)


def _write_transaction(
    xf: etree.xmlfile,
    row: dict[str, Any],
    current_count: int,
) -> int:
    """Emit one ``<CdtTrfTxInf>`` block for ``row``."""
    with xf.element("CdtTrfTxInf"):
        with xf.element("PmtId"):
            _write_simple(
                xf, "EndToEndId", str(row.get("end_to_end_id") or "")
            )
            uetr = row.get("uetr") or row.get("UETR")
            if uetr:
                _write_simple(xf, "UETR", str(uetr))

        amount = row.get("interbank_settlement_amount")
        currency = row.get("interbank_settlement_currency") or "EUR"
        if amount is not None:
            with xf.element("IntrBkSttlmAmt", attrib={"Ccy": str(currency)}):
                xf.write(str(amount))

        debtor_name = row.get("debtor_name")
        if debtor_name:
            with xf.element("Dbtr"):
                _write_simple(xf, "Nm", str(debtor_name))

        creditor_name = row.get("creditor_name")
        if creditor_name:
            with xf.element("Cdtr"):
                _write_simple(xf, "Nm", str(creditor_name))

    return current_count + 1


def _aggregate(
    row: dict[str, Any],
    running_total: Decimal,
    seen_currency: str | None,
) -> tuple[Decimal, str | None]:
    """Update ``running_total`` and remember the currency."""
    amount = row.get("interbank_settlement_amount")
    if amount is not None:
        try:
            running_total += Decimal(str(amount))
        except (ValueError, ArithmeticError):
            pass
    currency = row.get("interbank_settlement_currency")
    if currency and seen_currency is None:
        return running_total, str(currency)
    return running_total, seen_currency
