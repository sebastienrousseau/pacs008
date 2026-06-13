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

"""Tests for pacs008.vop — EPC Verification of Payee helpers."""

from __future__ import annotations

from datetime import date

import pytest

from pacs008.vop import (
    VoPMatchResult,
    VoPResult,
    VoPValidationError,
    embed_in_row,
    extract_from_row,
    validate_vop_results,
)

_PRE_MANDATE = date(2025, 10, 8)
_POST_MANDATE = date(2025, 10, 10)


# ---------------------------------------------------------------------------
# VoPResult
# ---------------------------------------------------------------------------


class TestVoPResult:
    def test_match_is_proceed(self):
        r = VoPResult(
            result=VoPMatchResult.MATCH,
            name_compared="Alice Smith",
            iban="DE89370400440532013000",
        )
        assert r.is_proceed
        assert not r.is_blocking

    def test_no_match_is_blocking(self):
        r = VoPResult(
            result=VoPMatchResult.NO_MATCH,
            name_compared="Alice Smith",
            iban="DE89370400440532013000",
        )
        assert r.is_blocking
        assert not r.is_proceed

    def test_close_match_neither_proceed_nor_blocking(self):
        # CLOSE_MATCH is operationally a "show the user, ask
        # confirmation" — neither auto-proceed nor block.
        r = VoPResult(
            result=VoPMatchResult.CLOSE_MATCH,
            name_compared="Alice Smith",
            iban="DE89370400440532013000",
            suggested_name="Alice T Smith",
        )
        assert not r.is_blocking
        assert not r.is_proceed

    def test_not_applicable_is_proceed(self):
        r = VoPResult(
            result=VoPMatchResult.NOT_APPLICABLE,
            name_compared="Alice",
            iban="DE89370400440532013000",
        )
        assert r.is_proceed

    def test_performed_at_iso_validated(self):
        with pytest.raises(ValueError, match="ISO 8601"):
            VoPResult(
                result=VoPMatchResult.MATCH,
                name_compared="Alice",
                iban="DE89370400440532013000",
                performed_at="not-a-date",
            )

    def test_performed_at_iso_accepted(self):
        # Both date-only and full datetime should parse.
        VoPResult(
            result=VoPMatchResult.MATCH,
            name_compared="Alice",
            iban="DE89370400440532013000",
            performed_at="2026-06-13T14:00:00",
        )
        VoPResult(
            result=VoPMatchResult.MATCH,
            name_compared="Alice",
            iban="DE89370400440532013000",
            performed_at="2026-06-13",
        )


# ---------------------------------------------------------------------------
# embed_in_row / extract_from_row
# ---------------------------------------------------------------------------


class TestEmbedExtract:
    def test_round_trip_match(self):
        original = {"msg_id": "M1"}
        vop = VoPResult(
            result=VoPMatchResult.MATCH,
            name_compared="Alice",
            iban="DE89370400440532013000",
        )
        embedded = embed_in_row(original, vop)
        # Originals untouched.
        assert "vop_result" not in original
        # Extraction round-trips.
        extracted = extract_from_row(embedded)
        assert extracted == vop

    def test_round_trip_close_match_with_optional_fields(self):
        vop = VoPResult(
            result=VoPMatchResult.CLOSE_MATCH,
            name_compared="Alice",
            iban="DE89370400440532013000",
            reason_code="NAME_FUZZY",
            suggested_name="Alice T. Smith",
            performed_at="2026-06-13T14:00:00",
        )
        embedded = embed_in_row({}, vop)
        assert extract_from_row(embedded) == vop

    def test_extract_returns_none_when_missing(self):
        assert extract_from_row({"msg_id": "M1"}) is None

    def test_extract_raises_on_garbage_result_value(self):
        with pytest.raises(ValueError, match="unrecognised vop_result"):
            extract_from_row({"vop_result": "MAYBE"})


# ---------------------------------------------------------------------------
# validate_vop_results
# ---------------------------------------------------------------------------


class TestValidateVoPResults:
    def test_empty_returns_empty(self):
        assert validate_vop_results([], today=_POST_MANDATE) == []

    def test_missing_vop_passes_before_mandate(self):
        rows = [{"msg_id": "M1"}]
        assert validate_vop_results(rows, today=_PRE_MANDATE) == []

    def test_missing_vop_fails_after_mandate(self):
        rows = [{"msg_id": "M1"}]
        errors = validate_vop_results(rows, today=_POST_MANDATE)
        assert len(errors) == 1
        assert errors[0].rule == "vop_required"

    def test_match_passes_after_mandate(self):
        row = embed_in_row(
            {"msg_id": "M1"},
            VoPResult(
                result=VoPMatchResult.MATCH,
                name_compared="Alice",
                iban="DE89370400440532013000",
            ),
        )
        assert validate_vop_results([row], today=_POST_MANDATE) == []

    def test_no_match_blocks(self):
        row = embed_in_row(
            {},
            VoPResult(
                result=VoPMatchResult.NO_MATCH,
                name_compared="Alice",
                iban="DE89370400440532013000",
            ),
        )
        errors = validate_vop_results([row], today=_POST_MANDATE)
        assert len(errors) == 1
        assert errors[0].rule == "vop_blocking"
        assert "NO_MATCH" in errors[0].message

    def test_garbage_result_value_flagged(self):
        rows = [
            {
                "vop_result": "MAYBE",
                "vop_name_compared": "Alice",
                "vop_iban": "DE89370400440532013000",
            }
        ]
        errors = validate_vop_results(rows, today=_POST_MANDATE)
        assert len(errors) == 1
        assert errors[0].rule == "vop_result_unrecognised"

    def test_close_match_does_not_block_in_validator(self):
        # CLOSE_MATCH is a "show the user" outcome; the validator
        # leaves the decision to the caller.
        row = embed_in_row(
            {},
            VoPResult(
                result=VoPMatchResult.CLOSE_MATCH,
                name_compared="Alice",
                iban="DE89370400440532013000",
            ),
        )
        assert validate_vop_results([row], today=_POST_MANDATE) == []


class TestVoPValidationError:
    def test_frozen_dataclass(self):
        err = VoPValidationError(0, "vop_result", "vop_required", "x")
        with pytest.raises(Exception):
            err.row = 99  # type: ignore[misc]
