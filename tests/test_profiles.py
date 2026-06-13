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

"""Tests for pacs008.profiles — scheme/usage-guideline rule sets."""

from __future__ import annotations

from datetime import date

import pytest

from pacs008.profiles import (
    BusinessRuleViolation,
    CBPRPlusProfile,
    FedwireProfile,
    GenericProfile,
    SchemeProfile,
    SchemeViolationError,
    get_profile,
    list_profiles,
    register_profile,
)
from pacs008.standards.address import AddressPolicy

_PRE_CLIFF = date(2026, 11, 13)
_POST_CLIFF = date(2026, 11, 14)
_FEDWIRE_CLIFF_PRE = date(2026, 11, 15)
_FEDWIRE_CLIFF_POST = date(2026, 11, 16)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_list_includes_shipped_profiles(self):
        profiles = list_profiles()
        assert "generic" in profiles
        assert "cbpr_plus" in profiles
        assert "fedwire" in profiles

    def test_cbpr_aliases_resolve_to_same_class(self):
        for name in ("cbpr_plus", "cbprplus", "CBPR+", "CBPR_PLUS"):
            p = get_profile(name)
            assert isinstance(p, CBPRPlusProfile)

    def test_case_insensitive_lookup(self):
        for name in ("GENERIC", "Generic", "generic"):
            assert isinstance(get_profile(name), GenericProfile)

    def test_unknown_profile_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown scheme"):
            get_profile("does-not-exist")

    def test_register_overwrite_succeeds(self):
        class FakeProfile(GenericProfile):
            @property
            def name(self) -> str:
                return "fake"

        register_profile("fake", FakeProfile)
        assert isinstance(get_profile("fake"), FakeProfile)


# ---------------------------------------------------------------------------
# Generic profile
# ---------------------------------------------------------------------------


class TestGenericProfile:
    def setup_method(self):
        self.profile = GenericProfile()

    def test_identity(self):
        assert self.profile.name == "generic"
        assert self.profile.mr_version == "generic"

    def test_permissive_defaults(self):
        assert self.profile.uetr_required is False
        assert self.profile.max_remit_info_len == 140
        assert self.profile.max_transactions_per_msg is None
        assert self.profile.lei_required_for() == ()
        assert self.profile.pinned_versions() == {}

    def test_accepts_all_base_charge_bearers(self):
        assert self.profile.allowed_charge_bearers == frozenset(
            {"DEBT", "CRED", "SHAR", "SLEV"}
        )

    def test_address_policy_is_unstructured_ok(self):
        assert (
            self.profile.address_policy(today=_POST_CLIFF)
            is AddressPolicy.UNSTRUCTURED_OK
        )

    def test_validate_business_rules_returns_no_violations_for_empty_row(self):
        assert self.profile.validate_business_rules([{}]) == []

    def test_validate_business_rules_returns_no_violations_for_typical_row(
        self,
    ):
        row = {
            "msg_id": "M1",
            "charge_bearer": "SHAR",
            "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "remittance_information": "Invoice 12345",
        }
        assert self.profile.validate_business_rules([row]) == []


# ---------------------------------------------------------------------------
# CBPR+ profile
# ---------------------------------------------------------------------------


class TestCBPRPlusProfile:
    def setup_method(self):
        self.profile = CBPRPlusProfile()

    def test_identity(self):
        assert self.profile.name == "cbpr_plus"
        assert self.profile.mr_version == "MR2019"

    def test_uetr_is_required(self):
        assert self.profile.uetr_required is True

    def test_cardinality_cap(self):
        assert self.profile.max_transactions_per_msg == 10_000

    def test_address_policy_switches_on_cliff(self):
        assert (
            self.profile.address_policy(today=_PRE_CLIFF)
            is AddressPolicy.UNSTRUCTURED_OK
        )
        assert (
            self.profile.address_policy(today=_POST_CLIFF)
            is AddressPolicy.HYBRID_OR_STRUCTURED
        )

    def test_pinned_versions_match_mr2019(self):
        v = self.profile.pinned_versions()
        # Seven core messages per ECB T2-0170 alignment.
        assert v["pacs.008"] == "001.08"
        assert v["pacs.002"] == "001.10"
        assert v["pacs.004"] == "001.09"
        assert v["pacs.009"] == "001.08"
        assert v["pacs.010"] == "001.03"
        assert v["camt.029"] == "001.09"
        assert v["camt.056"] == "001.08"

    def test_missing_uetr_flagged(self):
        rows = [
            {
                "msg_id": "M1",
                "charge_bearer": "SHAR",
                "remittance_information": "Inv 1",
            }
        ]
        violations = self.profile.validate_business_rules(rows)
        rules = [v.rule for v in violations]
        assert "uetr_required" in rules

    def test_invalid_charge_bearer_flagged(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "INVALID",
            }
        ]
        violations = self.profile.validate_business_rules(rows)
        assert any(v.rule == "charge_bearer_invalid" for v in violations)

    def test_remit_info_too_long_flagged(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "remittance_information": "x" * 141,
            }
        ]
        violations = self.profile.validate_business_rules(rows)
        assert any(v.rule == "remit_info_too_long" for v in violations)

    def test_remit_info_at_exact_cap_passes(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "remittance_information": "x" * 140,
            }
        ]
        assert self.profile.validate_business_rules(rows) == []


# ---------------------------------------------------------------------------
# Fedwire profile
# ---------------------------------------------------------------------------


class TestFedwireProfile:
    def setup_method(self):
        self.profile = FedwireProfile()

    def test_identity(self):
        assert self.profile.name == "fedwire"
        assert self.profile.mr_version == "Fedwire-2026"

    def test_single_transaction_cardinality(self):
        assert self.profile.max_transactions_per_msg == 1

    def test_slev_not_in_allowed_charge_bearers(self):
        cb = self.profile.allowed_charge_bearers
        assert "SLEV" not in cb
        assert {"DEBT", "CRED", "SHAR"}.issubset(cb)

    def test_address_policy_cliff_two_days_later_than_cbpr(self):
        # Fedwire cutover is 16 Nov, not 14 Nov.
        assert (
            self.profile.address_policy(today=_FEDWIRE_CLIFF_PRE)
            is AddressPolicy.UNSTRUCTURED_OK
        )
        assert (
            self.profile.address_policy(today=_FEDWIRE_CLIFF_POST)
            is AddressPolicy.HYBRID_OR_STRUCTURED
        )

    def test_pinned_versions(self):
        v = self.profile.pinned_versions()
        assert v["pacs.008"] == "001.08"
        assert v["pacs.028"] == "001.03"

    def test_cardinality_violation_on_multi_tx_batch(self):
        rows = [
            {
                "uetr": "u1",
                "charge_bearer": "SHAR",
            },
            {
                "uetr": "u2",
                "charge_bearer": "SHAR",
            },
        ]
        violations = self.profile.validate_business_rules(rows)
        assert any(v.rule == "cardinality_exceeded" for v in violations)

    def test_slev_charge_bearer_flagged(self):
        rows = [
            {
                "uetr": "u1",
                "charge_bearer": "SLEV",
            }
        ]
        violations = self.profile.validate_business_rules(rows)
        assert any(
            v.rule == "charge_bearer_invalid" and "SLEV" in v.message
            for v in violations
        )


# ---------------------------------------------------------------------------
# Shared dataclass / error contracts
# ---------------------------------------------------------------------------


class TestSchemeViolationError:
    def test_message_includes_count_and_scheme(self):
        v = BusinessRuleViolation(
            row=0,
            party=None,
            field="charge_bearer",
            rule="charge_bearer_invalid",
            message="bad",
        )
        err = SchemeViolationError(violations=[v], scheme="cbpr_plus")
        assert "cbpr_plus" in str(err)
        assert "1 violation" in str(err)

    def test_violations_tuple_preserves_order(self):
        v1 = BusinessRuleViolation(0, None, "a", "ra", "ma")
        v2 = BusinessRuleViolation(1, None, "b", "rb", "mb")
        err = SchemeViolationError(violations=[v1, v2], scheme="cbpr_plus")
        assert err.violations == (v1, v2)


class TestBusinessRuleViolation:
    def test_is_frozen_dataclass(self):
        v = BusinessRuleViolation(0, None, "a", "ra", "ma")
        with pytest.raises(Exception):
            v.row = 99  # type: ignore[misc]

    def test_severity_defaults_to_block(self):
        v = BusinessRuleViolation(0, None, "a", "ra", "ma")
        assert v.severity == "block"


# ---------------------------------------------------------------------------
# ABC contract sanity
# ---------------------------------------------------------------------------


class TestABCContract:
    def test_subclass_must_implement_abstract_methods(self):
        # An incomplete subclass cannot be instantiated.
        class Incomplete(SchemeProfile):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_all_three_concrete_profiles_instantiable(self):
        GenericProfile()
        CBPRPlusProfile()
        FedwireProfile()
