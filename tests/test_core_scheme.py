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

"""Tests for the scheme-aware path through pacs008.core.core.process_files.

These exercise ``_run_scheme_validation`` directly to keep them fast
and to avoid coupling to template/XSD setup.
"""

from __future__ import annotations

import pytest

from pacs008.core.core import _run_scheme_validation
from pacs008.profiles import SchemeViolationError

# ---------------------------------------------------------------------------
# Generic (default) — backward-compat
# ---------------------------------------------------------------------------


class TestGenericNoOp:
    def test_empty_input_passes(self):
        _run_scheme_validation([], "generic")

    def test_minimal_row_passes(self):
        _run_scheme_validation([{"msg_id": "M1"}], "generic")

    def test_unstructured_address_passes_under_generic(self):
        rows = [
            {
                "debtor_address_adr_line_0": "42 High Street",
                "debtor_address_adr_line_1": "London SW1A 1AA",
            }
        ]
        _run_scheme_validation(rows, "generic")


# ---------------------------------------------------------------------------
# CBPR+ — UETR + post-cliff address policy
# ---------------------------------------------------------------------------


class TestCBPRPlusViolations:
    def test_missing_uetr_raises(self):
        rows = [{"msg_id": "M1", "charge_bearer": "SHAR"}]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "cbpr_plus")
        rules = [v.rule for v in excinfo.value.violations]
        assert "uetr_required" in rules

    def test_invalid_charge_bearer_raises(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "OTHR",
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "cbpr_plus")
        assert any(
            v.rule == "charge_bearer_invalid" for v in excinfo.value.violations
        )

    def test_well_formed_row_passes(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
                "remittance_information": "Invoice 12345",
            }
        ]
        # No address fields → no address validation runs.
        _run_scheme_validation(rows, "cbpr_plus")


# ---------------------------------------------------------------------------
# Fedwire — strict cardinality
# ---------------------------------------------------------------------------


class TestFedwireViolations:
    def test_multi_tx_batch_raises_cardinality(self):
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
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "fedwire")
        assert any(
            v.rule == "cardinality_exceeded" for v in excinfo.value.violations
        )

    def test_slev_charge_bearer_raises(self):
        rows = [
            {
                "uetr": "u1",
                "charge_bearer": "SLEV",
            }
        ]
        with pytest.raises(SchemeViolationError) as excinfo:
            _run_scheme_validation(rows, "fedwire")
        assert any(
            v.rule == "charge_bearer_invalid" for v in excinfo.value.violations
        )

    def test_single_well_formed_tx_passes(self):
        rows = [
            {
                "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                "charge_bearer": "SHAR",
            }
        ]
        _run_scheme_validation(rows, "fedwire")


# ---------------------------------------------------------------------------
# Unknown scheme — fail closed
# ---------------------------------------------------------------------------


class TestUnknownScheme:
    def test_unknown_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown scheme"):
            _run_scheme_validation([{"msg_id": "M1"}], "made_up_scheme")
