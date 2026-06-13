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

"""Scheme-profile base classes and registry.

The :class:`SchemeProfile` ABC defines the shape every concrete profile
must implement; the default :meth:`SchemeProfile.validate_business_rules`
covers charge-bearer / UETR / remittance-info checks for every profile
that doesn't override it.

Concrete profiles register themselves at import time via
:func:`register_profile`. The :func:`get_profile` factory is the public
lookup; calling it with an unknown name raises ``ValueError`` rather
than silently falling back to ``generic`` — failing closed is the
right default for compliance code.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from pacs008.compliance.swift_charset import SWIFT_X_CHARSET
from pacs008.exceptions import Pacs008Error
from pacs008.standards.address import AddressPolicy
from pacs008.validation.calendar import AlwaysOpenCalendar, Calendar


@dataclass(frozen=True)
class BusinessRuleViolation:
    """A single business-rule finding from a scheme profile.

    Attributes:
        row: Zero-based row index in the input payment data.
        party: Party prefix the finding relates to (``"debtor"``,
            ``"creditor"``, ``"debtor_agent"``, …) or ``None`` for
            message-level rules.
        field: The offending field name.
        rule: Short rule identifier (e.g. ``"charge_bearer_invalid"``)
            suitable for log filtering and ticketing.
        message: Human-readable description.
        severity: ``"block"`` (rail will reject) or ``"warn"`` (advisory
            — future cliff).
    """

    row: int
    party: Optional[str]
    field: str
    rule: str
    message: str
    severity: str = "block"


class SchemeViolationError(Pacs008Error):
    """Raised by :func:`pacs008.core.core.process_files` when one or
    more scheme rules block the payment batch.

    The ``violations`` attribute carries every finding so callers can
    surface them to the user (CLI, API response, ticket).
    """

    def __init__(
        self,
        violations: Sequence[BusinessRuleViolation],
        scheme: str,
    ) -> None:
        self.violations: tuple[BusinessRuleViolation, ...] = tuple(violations)
        self.scheme = scheme
        n = len(self.violations)
        s = "" if n == 1 else "s"
        super().__init__(
            f"Scheme {scheme!r} rejected the payment batch: "
            f"{n} violation{s}"
        )


class SchemeProfile(ABC):
    """Abstract base for scheme / usage-guideline rule sets.

    Subclasses encode the rulebook of one rail (CBPR+, HVPS+, Fedwire,
    CHAPS, T2 RTGS, SCT Inst). Property accessors are used in preference
    to plain class attributes so subclasses can compute values
    dynamically (e.g. address policy changes across a cutoff date).
    """

    # ----- identity -----

    @property
    @abstractmethod
    def name(self) -> str:
        """Short, lowercase profile name (e.g. ``"cbpr_plus"``)."""

    @property
    @abstractmethod
    def mr_version(self) -> str:
        """ISO 20022 maintenance release this profile pins to
        (e.g. ``"MR2019"``, ``"UG2026"``)."""

    # ----- rule properties -----

    @property
    @abstractmethod
    def uetr_required(self) -> bool:
        """Whether the UETR is mandatory under this scheme."""

    @property
    @abstractmethod
    def max_remit_info_len(self) -> int:
        """Maximum length of unstructured remittance information."""

    @property
    @abstractmethod
    def allowed_charge_bearers(self) -> frozenset[str]:
        """Permitted ``ChrgBr`` codes (e.g. ``{"DEBT", "CRED", "SHAR", "SLEV"}``)."""

    @property
    @abstractmethod
    def max_transactions_per_msg(self) -> Optional[int]:
        """Maximum number of transactions per message file.

        ``None`` means unbounded. SCT Inst and Fedwire both cap this at
        1; CBPR+ allows large batches.
        """

    @property
    def charset(self) -> frozenset[str]:
        """Character set permitted by this scheme.

        Defaults to :data:`~pacs008.compliance.swift_charset.SWIFT_X_CHARSET`
        (used by CBPR+, SEPA-EPC, generic). Profiles like Fedwire that
        accept a broader set override this with
        :data:`~pacs008.compliance.swift_charset.SWIFT_Z_CHARSET`.

        ``cleanse_data`` and ``cleanse_data_with_report`` accept this
        as a parameter so callers can wire it in directly.
        """
        return SWIFT_X_CHARSET

    @property
    def calendar(self) -> Calendar:
        """Settlement calendar in force on this scheme.

        Defaults to :class:`~pacs008.validation.calendar.AlwaysOpenCalendar`
        (24/7). Profiles tied to a specific RTGS rail override this:
        CBPR+ and T2 RTGS use the TARGET calendar; Fedwire uses the
        Federal Reserve calendar; CHAPS uses the BoE calendar; FedNow
        and SCT Inst stay 24/7.

        ``validate_settlement_dates`` consumes this to flag pacs.008
        messages whose ``IntrBkSttlmDt`` falls on a closing day.
        """
        return AlwaysOpenCalendar()

    # ----- behaviour -----

    @abstractmethod
    def address_policy(
        self, today: Optional[date] = None
    ) -> AddressPolicy:
        """Return the :class:`~pacs008.standards.address.AddressPolicy`
        in force for this scheme on ``today``.

        Cliff-aware profiles will return a more permissive policy
        before the cutoff and a stricter one after.
        """

    @abstractmethod
    def lei_required_for(self) -> tuple[str, ...]:
        """Party prefixes that must carry an LEI under this scheme.

        Empty tuple means LEI is optional everywhere. CHAPS (BoE
        mandate) returns the FI prefixes (``"debtor_agent"``,
        ``"creditor_agent"``).
        """

    @abstractmethod
    def pinned_versions(self) -> dict[str, str]:
        """Message-family → version string the scheme pins to.

        Example::

            {"pacs.008": "001.08", "pacs.002": "001.10"}

        Empty dict means no version pinning (the profile accepts any
        supported version of the message family).
        """

    # ----- default validation -----

    def validate_business_rules(
        self,
        payment_data: Sequence[dict[str, object]],
    ) -> list[BusinessRuleViolation]:
        """Default rule check: charge bearer, UETR presence, remit length.

        Sub-profiles can override entirely or call ``super()`` and add
        their own rules.
        """
        violations: list[BusinessRuleViolation] = []
        allowed_cb = self.allowed_charge_bearers
        uetr_required = self.uetr_required
        max_remit = self.max_remit_info_len

        for row_idx, row in enumerate(payment_data):
            charge_bearer = row.get("charge_bearer")
            if charge_bearer is not None and charge_bearer != "":
                cb = str(charge_bearer)
                if cb not in allowed_cb:
                    violations.append(
                        BusinessRuleViolation(
                            row=row_idx,
                            party=None,
                            field="charge_bearer",
                            rule="charge_bearer_invalid",
                            message=(
                                f"charge_bearer {cb!r} not permitted under "
                                f"scheme {self.name!r}; allowed: "
                                f"{sorted(allowed_cb)}"
                            ),
                        )
                    )

            if uetr_required:
                uetr = row.get("uetr") or row.get("UETR")
                if not uetr:
                    violations.append(
                        BusinessRuleViolation(
                            row=row_idx,
                            party=None,
                            field="uetr",
                            rule="uetr_required",
                            message=(
                                f"UETR is mandatory under scheme "
                                f"{self.name!r} (missing or empty)"
                            ),
                        )
                    )

            remit = row.get("remittance_information") or row.get("ustrd")
            if remit and len(str(remit)) > max_remit:
                violations.append(
                    BusinessRuleViolation(
                        row=row_idx,
                        party=None,
                        field="remittance_information",
                        rule="remit_info_too_long",
                        message=(
                            f"remittance information exceeds "
                            f"{max_remit} chars under scheme "
                            f"{self.name!r}"
                        ),
                    )
                )

        # Cardinality is a per-batch rule, applied once per message.
        cap = self.max_transactions_per_msg
        if cap is not None and len(payment_data) > cap:
            required_chunks = math.ceil(len(payment_data) / cap)
            violations.append(
                BusinessRuleViolation(
                    row=-1,
                    party=None,
                    field="<message>",
                    rule="cardinality_exceeded",
                    message=(
                        f"scheme {self.name!r} permits at most {cap} "
                        f"transaction(s) per message; got "
                        f"{len(payment_data)}. Split into "
                        f"{required_chunks} chunks (see "
                        f"pacs008.core.splitter.split_for_scheme)"
                    ),
                )
            )

        return violations


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


_PROFILES: dict[str, type[SchemeProfile]] = {}


def register_profile(name: str, profile_cls: type[SchemeProfile]) -> None:
    """Register a concrete profile under a lookup name.

    Names are case-insensitive. Re-registering an existing name
    overwrites — useful for tests and downstream subclasses.
    """
    _PROFILES[name.lower()] = profile_cls


def get_profile(name: str) -> SchemeProfile:
    """Look up a scheme profile by name (case-insensitive).

    Raises:
        ValueError: if ``name`` is not registered. Failing closed is
            deliberate — silently falling back to ``generic`` could
            ship non-compliant traffic.
    """
    key = name.lower()
    if key not in _PROFILES:
        available = sorted(_PROFILES)
        raise ValueError(
            f"Unknown scheme profile {name!r}; available: {available}"
        )
    return _PROFILES[key]()


def list_profiles() -> list[str]:
    """Return the names of all registered profiles, sorted."""
    return sorted(_PROFILES)
