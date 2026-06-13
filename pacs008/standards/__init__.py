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

"""ISO 20022 standards primitives.

This package houses standards-driven types that live above the message
layer but below the scheme-profile layer:

- :mod:`pacs008.standards.address` — ``PostalAddress`` model and the
  hybrid-address tooling required for the November 14, 2026 SWIFT
  CBPR+/HVPS+/T2 RTGS/CHAPS/Fedwire/Lynx address cliff.

Future siblings (planned for v0.1.0): ``bah`` (head.001 BAH wrapping),
``uetr`` (typed UETR identifier), ``lei`` (typed LEI identifier).
"""

from pacs008.standards.address import (
    NOV_2026_CLIFF,
    AddressClassification,
    AddressPolicy,
    AddressValidationError,
    PostalAddress,
    Severity,
    from_unstructured,
    validate_addresses,
)

__all__ = [
    "NOV_2026_CLIFF",
    "AddressClassification",
    "AddressPolicy",
    "AddressValidationError",
    "PostalAddress",
    "Severity",
    "from_unstructured",
    "validate_addresses",
]
