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

"""Bank of England CHAPS profile.

The Bank of England's CHAPS rulebook, in force on the BoE-operated
RTGS service. Two notable v0.0.2 specifics:

- LEI is **mandatory** for FI fields (debtor agent + creditor agent)
  per the BoE RTGS Renewal Programme. This is the first major scheme
  to unilaterally require LEI.
- CHAPS Enhanced Data: structured remittance, purpose codes, UETR are
  all mandatory.
- Address policy switches to HYBRID_OR_STRUCTURED on 2026-11-14
  alongside CBPR+ / HVPS+ / T2 / Fedwire.

References:
    - Bank of England — *Mandating ISO 20022 enhanced data in CHAPS*.
    - Bank of England — *RTGS Renewal Programme*.
    - LEI Worldwide — *CHAPS LEI UK*.
"""

from __future__ import annotations

from datetime import date

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import NOV_2026_CLIFF, AddressPolicy
from pacs008.validation.calendar import Calendar, CHAPSCalendar


class CHAPSProfile(SchemeProfile):
    """Bank of England CHAPS profile."""

    @property
    def name(self) -> str:
        return "chaps"

    @property
    def mr_version(self) -> str:
        # CHAPS tracks MR2019 alignment for the core pacs/camt
        # messages — same hold as CBPR+.
        return "MR2019"

    @property
    def uetr_required(self) -> bool:
        return True

    @property
    def max_remit_info_len(self) -> int:
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        # CHAPS does not use SLEV (no service-level agreement code).
        return frozenset({"DEBT", "CRED", "SHAR"})

    @property
    def max_transactions_per_msg(self) -> int | None:
        # CHAPS uses payment-level (single-tx) routing for HVP via
        # pacs.008; multi-tx is allowed but capped per BoE rulebook.
        return 1000

    def address_policy(self, today: date | None = None) -> AddressPolicy:
        ref = today if today is not None else date.today()
        if ref >= NOV_2026_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        # The defining CHAPS rule: LEI mandatory for FI fields.
        return ("debtor_agent", "creditor_agent")

    def pinned_versions(self) -> dict[str, str]:
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
            "pacs.004": "001.09",
            "pacs.009": "001.08",
            "camt.029": "001.09",
            "camt.056": "001.08",
        }

    @property
    def calendar(self) -> Calendar:
        return CHAPSCalendar()


register_profile("chaps", CHAPSProfile)
