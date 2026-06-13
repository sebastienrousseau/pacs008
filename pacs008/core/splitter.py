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

"""Scheme-aware transaction batch splitter.

Some rails refuse batches: EPC SCT Inst v1.1 (in force since 5 October
2025) mandates exactly one transaction per file; Fedwire ISO 20022 is
likewise single-transaction. Other rails impose softer caps (CBPR+
allows up to 10,000 per pacs.008 message).

:func:`split_for_scheme` is the row-aware splitter: given a list of
payment rows and a scheme name, it yields chunks small enough to be
sent under the scheme's cardinality rule. Each chunk's rows get a
rewritten ``msg_id`` so each chunk produces a distinct, traceable
message file.

What this module does NOT do (deliberately, in v0.0.2):

- Reconcile the ``GrpHdr`` ``NbOfTxs`` / ``CtrlSum`` fields: those are
  computed downstream by the XML generator from the (now-chunked)
  rows. Callers needing pre-computed totals should iterate the chunks
  and aggregate themselves.
- Preserve cross-row group structure (mandate references, payment
  information blocks, …). The codegen pipeline in v0.1.0 (Block F)
  will allow a smarter, group-aware splitter; today's splitter
  treats each row as an independent transaction.

Example::

    >>> from pacs008.core.splitter import split_for_scheme
    >>> rows = [{"msg_id": "BATCH001", "uetr": str(i)} for i in range(2500)]
    >>> chunks = list(split_for_scheme(rows, "fedwire"))
    >>> len(chunks)
    2500
    >>> chunks[0][0]["msg_id"], chunks[-1][0]["msg_id"]
    ('BATCH001-0001', 'BATCH001-2500')
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from typing import Any

from pacs008.profiles import get_profile

_DEFAULT_MSG_ID_TEMPLATE = "{base}-{index:04d}"
_FALLBACK_BASE_MSG_ID = "PACS008"


def required_chunks(
    payment_data: Sequence[dict[str, Any]],
    scheme: str,
) -> int:
    """Return how many chunks ``payment_data`` would split into under ``scheme``.

    Returns 0 for empty input and 1 for any scheme with no cardinality
    cap (``max_transactions_per_msg is None``).

    Args:
        payment_data: List of payment-row dicts.
        scheme: Scheme profile name (see :func:`pacs008.profiles.get_profile`).

    Returns:
        Number of chunks needed to comply with the scheme's cardinality
        cap.

    Raises:
        ValueError: if ``scheme`` is not a registered profile.
    """
    if not payment_data:
        return 0
    profile = get_profile(scheme)
    cap = profile.max_transactions_per_msg
    if cap is None:
        return 1
    return math.ceil(len(payment_data) / cap)


def split_for_scheme(
    payment_data: Sequence[dict[str, Any]],
    scheme: str,
    *,
    msg_id_template: str = _DEFAULT_MSG_ID_TEMPLATE,
    base_msg_id: str | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Yield scheme-compliant chunks of ``payment_data``.

    For schemes with no cardinality cap (``GenericProfile``) the
    function yields the whole input as a single chunk and does not
    rewrite the ``msg_id``. For capped schemes it yields successive
    fixed-size slices; each row's ``msg_id`` is rewritten via
    ``msg_id_template`` so every chunk produces a distinct downstream
    message file.

    Args:
        payment_data: List of payment-row dicts.
        scheme: Scheme profile name.
        msg_id_template: Format string with named placeholders ``base``
            (the original msg_id) and ``index`` (1-based chunk number).
            Default ``"{base}-{index:04d}"`` (zero-padded to 4 digits;
            extends gracefully for larger batches).
        base_msg_id: Override the base used in the template. If
            ``None`` (default), the splitter takes the msg_id of the
            first row; if no row has a ``msg_id``, falls back to
            ``"PACS008"``.

    Yields:
        Lists of row dicts, each at most ``cap`` long, with rewritten
        ``msg_id`` fields. The underlying input dicts are not mutated.

    Raises:
        ValueError: if ``scheme`` is not a registered profile.

    Note:
        ``GrpHdr.NbOfTxs`` and ``GrpHdr.CtrlSum`` are recomputed
        downstream from each chunk by the XML generator. The splitter
        only ensures the chunk size and msg_id uniqueness — totals are
        not propagated between chunks.
    """
    if not payment_data:
        return

    profile = get_profile(scheme)
    cap = profile.max_transactions_per_msg

    if cap is None:
        yield list(payment_data)
        return

    if cap < 1:
        # Defensive — a profile claiming cap=0 is a configuration error.
        raise ValueError(
            f"scheme {scheme!r} reports max_transactions_per_msg={cap}, "
            "which is not splittable"
        )

    resolved_base = (
        base_msg_id
        if base_msg_id is not None
        else _extract_base_msg_id(payment_data)
    )

    for index, start in enumerate(range(0, len(payment_data), cap), start=1):
        new_msg_id = msg_id_template.format(base=resolved_base, index=index)
        chunk = [
            {**row, "msg_id": new_msg_id}
            for row in payment_data[start : start + cap]
        ]
        yield chunk


def _extract_base_msg_id(
    payment_data: Sequence[dict[str, Any]],
) -> str:
    """Pick a base msg_id from the input — first row, or fallback."""
    for row in payment_data:
        msg_id = row.get("msg_id")
        if msg_id:
            return str(msg_id)
    return _FALLBACK_BASE_MSG_ID
