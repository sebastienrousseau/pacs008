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

"""Tests for the second-wave scheme profiles (Block I)."""

from __future__ import annotations

from datetime import date

import pytest

from pacs008.profiles import (
    CHAPSProfile,
    HVPSPlusProfile,
    SCTInstProfile,
    T2RTGSProfile,
    get_profile,
    list_profiles,
)
from pacs008.standards.address import AddressPolicy
from pacs008.validation.calendar import (
    AlwaysOpenCalendar,
    CHAPSCalendar,
    TARGETCalendar,
)

_PRE_CLIFF = date(2026, 11, 13)
_POST_CLIFF = date(2026, 11, 14)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistryAdditions:
    def test_all_new_profiles_registered(self):
        names = list_profiles()
        for n in ("chaps", "hvps_plus", "t2_rtgs", "sct_inst"):
            assert n in names

    @pytest.mark.parametrize(
        "alias,cls",
        [
            ("chaps", CHAPSProfile),
            ("CHAPS", CHAPSProfile),
            ("hvps_plus", HVPSPlusProfile),
            ("hvpsplus", HVPSPlusProfile),
            ("hvps+", HVPSPlusProfile),
            ("t2_rtgs", T2RTGSProfile),
            ("target2", T2RTGSProfile),
            ("sct_inst", SCTInstProfile),
            ("sct-inst", SCTInstProfile),
            ("sctinst", SCTInstProfile),
        ],
    )
    def test_aliases_resolve(self, alias, cls):
        assert isinstance(get_profile(alias), cls)


# ---------------------------------------------------------------------------
# CHAPS — defining feature: LEI required for FI fields
# ---------------------------------------------------------------------------


class TestCHAPSProfile:
    def setup_method(self):
        self.profile = CHAPSProfile()

    def test_lei_required_for_fi(self):
        assert set(self.profile.lei_required_for()) == {
            "debtor_agent",
            "creditor_agent",
        }

    def test_uetr_required(self):
        assert self.profile.uetr_required is True

    def test_uses_chaps_calendar(self):
        assert isinstance(self.profile.calendar, CHAPSCalendar)

    def test_slev_rejected(self):
        assert "SLEV" not in self.profile.allowed_charge_bearers

    def test_address_policy_cliff(self):
        assert (
            self.profile.address_policy(today=_PRE_CLIFF)
            is AddressPolicy.UNSTRUCTURED_OK
        )
        assert (
            self.profile.address_policy(today=_POST_CLIFF)
            is AddressPolicy.HYBRID_OR_STRUCTURED
        )

    def test_pinned_versions(self):
        v = self.profile.pinned_versions()
        assert v["pacs.008"] == "001.08"
        assert v["camt.029"] == "001.09"

    def test_cardinality_cap(self):
        assert self.profile.max_transactions_per_msg == 1000


# ---------------------------------------------------------------------------
# HVPS+
# ---------------------------------------------------------------------------


class TestHVPSPlusProfile:
    def setup_method(self):
        self.profile = HVPSPlusProfile()

    def test_single_tx(self):
        assert self.profile.max_transactions_per_msg == 1

    def test_uetr_required(self):
        assert self.profile.uetr_required is True

    def test_shar_only(self):
        assert self.profile.allowed_charge_bearers == frozenset({"SHAR"})

    def test_default_calendar_is_target(self):
        assert isinstance(self.profile.calendar, TARGETCalendar)


# ---------------------------------------------------------------------------
# T2 RTGS
# ---------------------------------------------------------------------------


class TestT2RTGSProfile:
    def setup_method(self):
        self.profile = T2RTGSProfile()

    def test_mr2019_hold(self):
        assert self.profile.mr_version == "MR2019"

    def test_seven_core_pins(self):
        v = self.profile.pinned_versions()
        for msg in (
            "pacs.008",
            "pacs.002",
            "pacs.004",
            "pacs.009",
            "pacs.010",
            "camt.029",
            "camt.056",
        ):
            assert msg in v

    def test_uses_target_calendar(self):
        assert isinstance(self.profile.calendar, TARGETCalendar)

    def test_cardinality_cap(self):
        assert self.profile.max_transactions_per_msg == 1000


# ---------------------------------------------------------------------------
# SCT Inst — defining feature: 24/7 + 1 tx per file + SLEV-only
# ---------------------------------------------------------------------------


class TestSCTInstProfile:
    def setup_method(self):
        self.profile = SCTInstProfile()

    def test_single_tx_per_file(self):
        assert self.profile.max_transactions_per_msg == 1

    def test_slev_only(self):
        assert self.profile.allowed_charge_bearers == frozenset({"SLEV"})

    def test_always_open_calendar(self):
        assert isinstance(self.profile.calendar, AlwaysOpenCalendar)

    def test_uetr_not_required(self):
        # SCT Inst uses End-to-End ID; UETR is optional.
        assert self.profile.uetr_required is False


# ---------------------------------------------------------------------------
# End-to-end validation integration
# ---------------------------------------------------------------------------


class TestSchemeRuleEnforcement:
    def test_chaps_blocks_missing_fi_lei(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                # debtor_agent_lei / creditor_agent_lei intentionally missing
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "chaps")
        rules = [v.rule for v in excinfo.value.violations]
        assert "lei" in rules

    def test_sct_inst_blocks_two_tx_batch(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {"charge_bearer": "SLEV"},
            {"charge_bearer": "SLEV"},
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "sct_inst")
        rules = [v.rule for v in excinfo.value.violations]
        assert "cardinality_exceeded" in rules

    def test_hvps_blocks_non_shar(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {
                "uetr": "u1",
                "charge_bearer": "DEBT",
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "hvps_plus")
        assert any(
            v.rule == "charge_bearer_invalid" for v in excinfo.value.violations
        )

    def test_t2_blocks_christmas_settlement(self):
        from pacs008.core.core import _run_scheme_validation
        from pacs008.profiles import SchemeViolationError

        rows = [
            {
                "uetr": "u1",
                "charge_bearer": "SHAR",
                "interbank_settlement_date": "2026-12-25",
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "t2_rtgs")
        assert any(
            v.rule == "settlement_date_closed"
            for v in excinfo.value.violations
        )
