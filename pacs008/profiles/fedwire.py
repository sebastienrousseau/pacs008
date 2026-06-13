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

"""Federal Reserve Fedwire ISO 20022 profile.

Fedwire Funds completed its big-bang migration to ISO 20022 on
14 July 2025 (the originally-scheduled 10 March 2025 date slipped
after a no-go decision). It now settles roughly $4.7T/day on ISO
20022 and is governed by the Federal Reserve's Fedwire ISO 20022
Implementation Center documentation.

Notable rules captured here:

- Single-transaction-per-message — Fedwire does not support batches.
- UETR is mandatory.
- Structured-address cliff is 16 November 2026 (two days later than
  the SWIFT CBPR+ cliff).
- Charge bearers exclude ``SLEV`` (not used on Fedwire).
- Version pins to the ``.08`` family per the implementation guide.

References:
    - Federal Reserve — *Fedwire ISO 20022 Implementation Center*.
    - Volante — *Fedwire migration rescheduled to 14 July 2025*.
    - Federal Reserve — November 2026 release notes.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pacs008.compliance.swift_charset import SWIFT_Z_CHARSET
from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import AddressPolicy
from pacs008.validation.calendar import Calendar, FedwireCalendar


# Fedwire's address-structuring cutover is dated 16 November 2026,
# whereas SWIFT CBPR+ uses 14 November 2026.
_FEDWIRE_ADDRESS_CLIFF: date = date(2026, 11, 16)


class FedwireProfile(SchemeProfile):
    """Federal Reserve Fedwire 2026 ISO 20022 profile."""

    @property
    def name(self) -> str:
        return "fedwire"

    @property
    def mr_version(self) -> str:
        # Fedwire's profile is published as a Federal Reserve-managed
        # variant; the underlying messages track MR2019 plus Fed
        # extensions documented in the Implementation Center.
        return "Fedwire-2026"

    @property
    def uetr_required(self) -> bool:
        return True

    @property
    def max_remit_info_len(self) -> int:
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        # SLEV is not used on Fedwire — net settlement model excludes
        # the service-level-agreement charge code.
        return frozenset({"DEBT", "CRED", "SHAR"})

    @property
    def max_transactions_per_msg(self) -> Optional[int]:
        # Fedwire is strictly one transaction per message file.
        return 1

    @property
    def charset(self) -> frozenset[str]:
        # Fedwire accepts the broader Z character set — accented Latin
        # supplements come through unchanged rather than being
        # transliterated.
        return SWIFT_Z_CHARSET

    @property
    def calendar(self) -> Calendar:
        return FedwireCalendar()

    def address_policy(
        self, today: Optional[date] = None
    ) -> AddressPolicy:
        ref = today if today is not None else date.today()
        if ref >= _FEDWIRE_ADDRESS_CLIFF:
            return AddressPolicy.HYBRID_OR_STRUCTURED
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        return ()

    def pinned_versions(self) -> dict[str, str]:
        return {
            "pacs.008": "001.08",
            "pacs.002": "001.10",
            "pacs.009": "001.08",
            "pacs.028": "001.03",
        }


register_profile("fedwire", FedwireProfile)
