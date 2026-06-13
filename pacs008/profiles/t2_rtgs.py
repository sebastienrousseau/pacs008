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

"""ECB TARGET2 (T2 RTGS) profile.

The ECB's June 2026 unfreeze moves T2 to MR2024 globally **except**
for seven core pacs/camt messages which stay on MR2019 to align with
the rest of the global market practice. See ECB notice T2-0170.

References:
    - ECB T2-0170 — *Upgrade of T2 messages to ISO MR 2026* (Oct 2025).
    - ECB — *TARGET 2 / T2 RTGS Service Description*.
"""

from __future__ import annotations

from datetime import date

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import NOV_2026_CLIFF, AddressPolicy
from pacs008.validation.calendar import Calendar, TARGETCalendar


class T2RTGSProfile(SchemeProfile):
    """ECB TARGET2 (T2 RTGS) profile."""

    @property
    def name(self) -> str:
        return "t2_rtgs"

    @property
    def mr_version(self) -> str:
        # MR2019 hold on the seven core pacs/camt messages even after
        # the June 2026 T2 unfreeze to MR2024.
        return "MR2019"

    @property
    def uetr_required(self) -> bool:
        return True

    @property
    def max_remit_info_len(self) -> int:
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        return frozenset({"DEBT", "CRED", "SHAR", "SLEV"})

    @property
    def max_transactions_per_msg(self) -> int | None:
        # T2 supports bulk pacs.008 up to 1000 transactions per file
        # for credit-transfer settlement.
        return 1000

    def address_policy(self, today: date | None = None) -> AddressPolicy:
        ref = today if today is not None else date.today()
        if ref >= NOV_2026_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        return ()

    def pinned_versions(self) -> dict[str, str]:
        # The seven core MR2019 pins per ECB T2-0170.
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
            "pacs.004": "001.09",
            "pacs.009": "001.08",
            "pacs.010": "001.03",
            "camt.029": "001.09",
            "camt.056": "001.08",
        }

    @property
    def calendar(self) -> Calendar:
        return TARGETCalendar()


register_profile("t2_rtgs", T2RTGSProfile)
register_profile("t2rtgs", T2RTGSProfile)
register_profile("target2", T2RTGSProfile)
