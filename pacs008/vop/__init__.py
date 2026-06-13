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

"""Verification of Payee (VoP) for SEPA Credit Transfer / SCT Inst.

The EPC's Verification of Payee scheme has been mandatory for
eurozone PSPs since 9 October 2025: every SCT and SCT Inst
instruction must include the result of an IBAN/name match check
performed at initiation. Non-eurozone SEPA PSPs follow by
9 July 2027.

This module exposes a tiny, transport-agnostic helper:

- :class:`VoPMatchResult` — the canonical EPC outcome categories.
- :class:`VoPResult` — frozen dataclass carrying the match result,
  the (creditor) name compared, the IBAN, an optional reason code,
  and the timestamp the check was performed.
- :func:`embed_in_row` — inject the result into a payment-row dict
  using the canonical column names so downstream profile
  validation (SCTInstProfile via :func:`validate_vop_results`) and
  XML generation can consume it.

References:
    - EPC — *Verification of Payee Scheme Rulebook*.
    - EPC — *Verification of Payee Implementation Guidelines*.
    - Crédit Agricole CIB — *Securing SEPA payments: VoP mandatory
      October 2025*.
"""

from pacs008.vop.match import (
    VoPMatchResult,
    VoPResult,
    VoPValidationError,
    embed_in_row,
    extract_from_row,
    validate_vop_results,
)

__all__ = [
    "VoPMatchResult",
    "VoPResult",
    "VoPValidationError",
    "embed_in_row",
    "extract_from_row",
    "validate_vop_results",
]
