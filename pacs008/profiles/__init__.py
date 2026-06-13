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

"""Scheme / usage-guideline profiles.

ISO 20022 by itself is a generic message vocabulary. Real-world rails
layer their own *usage guidelines* on top: SWIFT CBPR+ (cross-border
correspondent banking), HVPS+ (high-value payment systems), the
Federal Reserve's Fedwire 2026 profile, BoE's CHAPS rulebook, T2 RTGS,
EPC SCT Inst, and so on. Each rulebook restricts the base ISO 20022
type system further — narrower charge-bearer codes, mandatory UETR,
structured addresses after a cutoff date, per-message transaction
cardinality, scheme-pinned message versions, etc.

This package exposes a small ABC plus three concrete profiles
shipping in v0.0.2:

- :class:`~pacs008.profiles.generic.GenericProfile` — permissive
  baseline (default). Behaviourally a no-op so legacy callers see no
  change.
- :class:`~pacs008.profiles.cbpr_plus.CBPRPlusProfile` — SWIFT CBPR+
  Usage Guidelines UG2026 (in force 2026-11-14).
- :class:`~pacs008.profiles.fedwire.FedwireProfile` — Federal Reserve
  Fedwire ISO 20022 profile (structured-address cliff 2026-11-16).

Use :func:`get_profile` to look up by name (case-insensitive), or
:func:`list_profiles` for what's available::

    from pacs008.profiles import get_profile
    profile = get_profile("cbpr_plus")
    violations = profile.validate_business_rules(payment_data)

More profiles (HVPS+, CHAPS, T2 RTGS, SCT Inst) arrive in v0.1.0
alongside the codegen pipeline and lifecycle orchestration.
"""

from pacs008.profiles.base import (
    BusinessRuleViolation,
    SchemeProfile,
    SchemeViolationError,
    get_profile,
    list_profiles,
    register_profile,
)

# Import concrete profiles for their side effect of registering
# themselves; re-export at package level for convenience.
from pacs008.profiles.cbpr_plus import CBPRPlusProfile
from pacs008.profiles.chaps import CHAPSProfile
from pacs008.profiles.fedwire import FedwireProfile
from pacs008.profiles.generic import GenericProfile
from pacs008.profiles.hvps_plus import HVPSPlusProfile
from pacs008.profiles.sct_inst import SCTInstProfile
from pacs008.profiles.t2_rtgs import T2RTGSProfile

__all__ = [
    "BusinessRuleViolation",
    "CBPRPlusProfile",
    "CHAPSProfile",
    "FedwireProfile",
    "GenericProfile",
    "HVPSPlusProfile",
    "SCTInstProfile",
    "SchemeProfile",
    "SchemeViolationError",
    "T2RTGSProfile",
    "get_profile",
    "list_profiles",
    "register_profile",
]
