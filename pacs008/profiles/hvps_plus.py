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

"""SWIFT HVPS+ (High Value Payment Systems Plus) profile.

HVPS+ is SWIFT's MyStandards-published rulebook that harmonises
high-value payment usage guidelines across major RTGS operators
(T2 RTGS, Fedwire, CHAPS, HKMA CHATS, BOJ-NET).

This v0.0.2 profile captures the *common* HVPS+ tightening:

- Strict single-transaction-per-message (HVPS rails settle one
  payment per file).
- Mandatory UETR.
- Address policy switches to HYBRID_OR_STRUCTURED on 2026-11-14.
- Strict ``SHAR``-only charge bearer per HVPS+ UG2026.
- Defaults the calendar to TARGET because European HVPS volume is
  the largest single segment; institutions deploying for Fedwire HVP
  should use the dedicated FedwireProfile instead.

References:
    - SWIFT — *HVPS+ Usage Guidelines (UG2026 collection)*.
    - SWIFT MyStandards — HVPS+ rulebook.
"""

from __future__ import annotations

from datetime import date

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import NOV_2026_CLIFF, AddressPolicy
from pacs008.validation.calendar import Calendar, TARGETCalendar


class HVPSPlusProfile(SchemeProfile):
    """SWIFT HVPS+ UG2026 (high-value payment system) profile."""

    @property
    def name(self) -> str:
        return "hvps_plus"

    @property
    def mr_version(self) -> str:
        return "UG2026"

    @property
    def uetr_required(self) -> bool:
        return True

    @property
    def max_remit_info_len(self) -> int:
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        # HVPS+ Usage Guidelines tighten to SHAR-only for high-value
        # cross-border / inter-bank settlement.
        return frozenset({"SHAR"})

    @property
    def max_transactions_per_msg(self) -> int | None:
        return 1

    def address_policy(self, today: date | None = None) -> AddressPolicy:
        ref = today if today is not None else date.today()
        if ref >= NOV_2026_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        # Recommended in HVPS+ but not yet mandated globally — see the
        # rail-specific profiles (CHAPSProfile) for hard mandates.
        return ()

    def pinned_versions(self) -> dict[str, str]:
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
            "pacs.009": "001.08",
            "camt.029": "001.09",
            "camt.056": "001.08",
        }

    @property
    def calendar(self) -> Calendar:
        return TARGETCalendar()


register_profile("hvps_plus", HVPSPlusProfile)
register_profile("hvpsplus", HVPSPlusProfile)
register_profile("hvps+", HVPSPlusProfile)
