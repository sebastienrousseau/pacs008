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

"""Generic ISO 20022 baseline profile (the permissive default).

This profile enforces only the base ISO 20022 type system — no
scheme-specific tightening. It exists so callers that opt into the
scheme parameter without picking a specific rail see no behaviour
change relative to the pre-block-D pipeline.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pacs008.profiles.base import SchemeProfile, register_profile
from pacs008.standards.address import AddressPolicy


class GenericProfile(SchemeProfile):
    """Permissive baseline — no scheme-specific rules applied."""

    @property
    def name(self) -> str:
        return "generic"

    @property
    def mr_version(self) -> str:
        return "generic"

    @property
    def uetr_required(self) -> bool:
        return False

    @property
    def max_remit_info_len(self) -> int:
        # ISO 20022 ``Ustrd`` base maximum (no scheme tightening).
        return 140

    @property
    def allowed_charge_bearers(self) -> frozenset[str]:
        # All four base ISO 20022 codes are valid.
        return frozenset({"DEBT", "CRED", "SHAR", "SLEV"})

    @property
    def max_transactions_per_msg(self) -> Optional[int]:
        return None

    def address_policy(
        self, today: Optional[date] = None
    ) -> AddressPolicy:
        return AddressPolicy.UNSTRUCTURED_OK

    def lei_required_for(self) -> tuple[str, ...]:
        return ()

    def pinned_versions(self) -> dict[str, str]:
        return {}


register_profile("generic", GenericProfile)
