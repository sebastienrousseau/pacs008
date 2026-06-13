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

"""SWIFT CBPR+ (Cross-Border Payments and Reporting Plus) profile.

Cross-border correspondent-banking rulebook governing the majority of
SWIFT-routed payments. The Usage Guidelines UG2026 take force on
14 November 2026 and decommission fully unstructured postal
addresses.

Notable rules captured here:

- ``UETR`` is mandatory under SWIFT gpi (which CBPR+ extends).
- Charge bearers are restricted to ``DEBT`` / ``CRED`` / ``SHAR`` /
  ``SLEV``.
- Unstructured ``Ustrd`` remittance info is capped at 140 characters
  under MR2019 (the maintenance release CBPR+ tracks for core pacs).
- Address policy switches from ``UNSTRUCTURED_OK`` to
  ``HYBRID_OR_STRUCTURED`` on :data:`NOV_2026_CLIFF`.
- Batch transaction cardinality cap of 10,000.
- Pinned message versions reflect the MR2019 hold on the seven core
  pacs/camt messages.

References:
    - SWIFT — *Call to action: November 2026 release*.
    - SWIFT — *Customer Security Programme: CBPR+ Usage Guidelines*.
    - SWIFT MyStandards rulebook (UG2026 collection).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import NOV_2026_CLIFF, AddressPolicy
from pacs008.validation.calendar import Calendar, TARGETCalendar


class CBPRPlusProfile(SchemeProfile):
    """SWIFT CBPR+ Usage Guidelines UG2026."""

    @property
    def name(self) -> str:
        return "cbpr_plus"

    @property
    def mr_version(self) -> str:
        # CBPR+ holds on MR2019 for the seven core pacs/camt messages
        # even after the broader ISO 20022 community moves to MR2024
        # (per ECB T2-0170 alignment).
        return "MR2019"

    @property
    def uetr_required(self) -> bool:
        return True

    @property
    def max_remit_info_len(self) -> int:
        # MR2019 ``Ustrd`` cap.
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        return frozenset({"DEBT", "CRED", "SHAR", "SLEV"})

    @property
    def max_transactions_per_msg(self) -> Optional[int]:
        # CBPR+ permits large batches; the 10,000 cap is the MyStandards
        # documented maximum for FI-to-FI Credit Transfer.
        return 10_000

    def address_policy(
        self, today: Optional[date] = None
    ) -> AddressPolicy:
        ref = today if today is not None else date.today()
        if ref >= NOV_2026_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        # CBPR+ does not yet require LEI; the BoE CHAPS mandate is the
        # forward signal for ECB / Fed but CBPR+ itself remains
        # optional for v0.0.2.
        return ()

    @property
    def calendar(self) -> Calendar:
        # Most CBPR+ EUR settlement routes through TARGET2; multi-CCY
        # CBPR+ is a v0.1.0 concern.
        return TARGETCalendar()

    def pinned_versions(self) -> dict[str, str]:
        # MR2019 pinning for the seven core messages (per ECB T2-0170).
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
            "pacs.004": "001.09",
            "pacs.009": "001.08",
            "pacs.010": "001.03",
            "camt.029": "001.09",
            "camt.056": "001.08",
        }


register_profile("cbpr_plus", CBPRPlusProfile)
# Common alternative spellings — register both so users don't have to
# guess.
register_profile("cbprplus", CBPRPlusProfile)
register_profile("cbpr+", CBPRPlusProfile)
