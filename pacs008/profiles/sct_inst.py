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

"""EPC SCT Inst (SEPA Instant Credit Transfer) profile.

The European Payments Council's SEPA Instant Credit Transfer rulebook
v1.1 went live on 5 October 2025. Three v0.0.2 specifics:

- **Single transaction per file**: SCT Inst routes each instruction
  individually for the < 10-second settlement guarantee.
- **Always-open calendar**: SCT Inst is 24/7/365.
- **SLEV-only charge bearer**: SEPA-wide rule that charges are split
  per the Single Euro Payments Area service level.
- **VoP recommendation**: from 9 October 2025, eurozone PSPs must
  perform Verification of Payee (IBAN/name match) at initiation. The
  VoP result, if provided, is checked by
  :mod:`pacs008.vop`; SCT Inst rows missing a VoP result will be
  flagged via the VoP helper rather than this profile.

References:
    - EPC — *SCT Inst Inter-PSP Implementation Guidelines v1.1*.
    - EPC — *Verification of Payee Implementation Guidelines*.
"""

from __future__ import annotations

from datetime import date

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import NOV_2026_CLIFF, AddressPolicy
from pacs008.validation.calendar import AlwaysOpenCalendar, Calendar


class SCTInstProfile(SchemeProfile):
    """EPC SCT Inst v1.1 profile."""

    @property
    def name(self) -> str:
        return "sct_inst"

    @property
    def mr_version(self) -> str:
        return "MR2019"

    @property
    def uetr_required(self) -> bool:
        # SCT Inst recommends UETR for tracking but doesn't mandate
        # it; the End-to-End ID is the binding identifier. Keep as
        # optional for v0.0.2.
        return False

    @property
    def max_remit_info_len(self) -> int:
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        # SEPA-wide SLEV-only rule.
        return frozenset({"SLEV"})

    @property
    def max_transactions_per_msg(self) -> int | None:
        return 1

    def address_policy(self, today: date | None = None) -> AddressPolicy:
        """See :meth:`SchemeProfile.address_policy`."""
        ref = today if today is not None else date.today()
        if ref >= NOV_2026_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        """See :meth:`SchemeProfile.lei_required_for`."""
        return ()

    def pinned_versions(self) -> dict[str, str]:
        """See :meth:`SchemeProfile.pinned_versions`."""
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
        }

    @property
    def calendar(self) -> Calendar:
        # SCT Inst is 24/7/365.
        return AlwaysOpenCalendar()


register_profile("sct_inst", SCTInstProfile)
register_profile("sctinst", SCTInstProfile)
register_profile("sct-inst", SCTInstProfile)
