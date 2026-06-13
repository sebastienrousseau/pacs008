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

"""Tests for pacs008.core.splitter — scheme-aware batch splitter."""

from __future__ import annotations

import inspect

import pytest

from pacs008.core.splitter import (
    required_chunks,
    split_for_scheme,
)


def _rows(n: int, base_msg_id: str = "BATCH001") -> list[dict]:
    return [
        {"msg_id": base_msg_id, "uetr": f"u{i}", "amount": i * 10}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# required_chunks
# ---------------------------------------------------------------------------


class TestRequiredChunks:
    def test_empty_returns_zero(self):
        assert required_chunks([], "fedwire") == 0

    def test_unbounded_scheme_returns_one(self):
        assert required_chunks(_rows(10_000), "generic") == 1

    def test_fedwire_single_tx_per_chunk(self):
        # cap = 1 → one chunk per row
        assert required_chunks(_rows(5), "fedwire") == 5

    def test_cbpr_plus_under_cap(self):
        assert required_chunks(_rows(9_999), "cbpr_plus") == 1

    def test_cbpr_plus_at_cap(self):
        assert required_chunks(_rows(10_000), "cbpr_plus") == 1

    def test_cbpr_plus_over_cap_ceils(self):
        assert required_chunks(_rows(10_001), "cbpr_plus") == 2

    def test_unknown_scheme_raises(self):
        with pytest.raises(ValueError, match="Unknown scheme"):
            required_chunks(_rows(1), "not_a_scheme")


# ---------------------------------------------------------------------------
# split_for_scheme — basic cardinality
# ---------------------------------------------------------------------------


class TestSplitForSchemeFedwire:
    def test_empty_yields_nothing(self):
        assert list(split_for_scheme([], "fedwire")) == []

    def test_single_row_yields_one_chunk_of_one(self):
        chunks = list(split_for_scheme(_rows(1), "fedwire"))
        assert len(chunks) == 1
        assert len(chunks[0]) == 1

    def test_three_rows_yields_three_chunks(self):
        chunks = list(split_for_scheme(_rows(3), "fedwire"))
        assert len(chunks) == 3
        assert all(len(c) == 1 for c in chunks)

    def test_msg_id_template_format(self):
        chunks = list(split_for_scheme(_rows(3), "fedwire"))
        assert chunks[0][0]["msg_id"] == "BATCH001-0001"
        assert chunks[1][0]["msg_id"] == "BATCH001-0002"
        assert chunks[2][0]["msg_id"] == "BATCH001-0003"

    def test_non_msg_id_fields_preserved(self):
        chunks = list(split_for_scheme(_rows(3), "fedwire"))
        for i, chunk in enumerate(chunks):
            assert chunk[0]["uetr"] == f"u{i}"
            assert chunk[0]["amount"] == i * 10


class TestSplitForSchemeCBPRPlus:
    def test_under_cap_yields_single_chunk(self):
        chunks = list(split_for_scheme(_rows(9_999), "cbpr_plus"))
        assert len(chunks) == 1
        assert len(chunks[0]) == 9_999

    def test_at_cap_yields_single_chunk(self):
        chunks = list(split_for_scheme(_rows(10_000), "cbpr_plus"))
        assert len(chunks) == 1
        assert len(chunks[0]) == 10_000

    def test_over_cap_yields_two_chunks(self):
        chunks = list(split_for_scheme(_rows(10_001), "cbpr_plus"))
        assert len(chunks) == 2
        assert len(chunks[0]) == 10_000
        assert len(chunks[1]) == 1

    def test_two_full_chunks_plus_partial(self):
        chunks = list(split_for_scheme(_rows(25_000), "cbpr_plus"))
        assert len(chunks) == 3
        assert [len(c) for c in chunks] == [10_000, 10_000, 5_000]


class TestSplitForSchemeGeneric:
    def test_generic_yields_single_chunk_unchanged_msg_id(self):
        rows = _rows(50_000)
        chunks = list(split_for_scheme(rows, "generic"))
        assert len(chunks) == 1
        # Unbounded scheme — msg_id is NOT rewritten.
        assert chunks[0][0]["msg_id"] == "BATCH001"


# ---------------------------------------------------------------------------
# Msg-id base resolution
# ---------------------------------------------------------------------------


class TestMsgIdBase:
    def test_explicit_base_overrides_row_msg_id(self):
        chunks = list(
            split_for_scheme(_rows(2), "fedwire", base_msg_id="OVERRIDE")
        )
        assert chunks[0][0]["msg_id"] == "OVERRIDE-0001"
        assert chunks[1][0]["msg_id"] == "OVERRIDE-0002"

    def test_fallback_when_no_msg_id_in_rows(self):
        rows = [{"uetr": "u1"}, {"uetr": "u2"}]
        chunks = list(split_for_scheme(rows, "fedwire"))
        assert chunks[0][0]["msg_id"] == "PACS008-0001"
        assert chunks[1][0]["msg_id"] == "PACS008-0002"

    def test_first_row_msg_id_wins(self):
        rows = [
            {"msg_id": "FIRST"},
            {"msg_id": "SECOND"},
        ]
        chunks = list(split_for_scheme(rows, "fedwire"))
        assert chunks[0][0]["msg_id"].startswith("FIRST-")
        assert chunks[1][0]["msg_id"].startswith("FIRST-")

    def test_custom_template(self):
        chunks = list(
            split_for_scheme(
                _rows(2),
                "fedwire",
                msg_id_template="{base}_PART{index:02d}",
            )
        )
        assert chunks[0][0]["msg_id"] == "BATCH001_PART01"
        assert chunks[1][0]["msg_id"] == "BATCH001_PART02"


# ---------------------------------------------------------------------------
# Mutation safety
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_input_dicts_not_mutated(self):
        rows = _rows(3)
        original_msg_id = rows[0]["msg_id"]
        list(split_for_scheme(rows, "fedwire"))
        # Originals untouched.
        for row in rows:
            assert row["msg_id"] == original_msg_id


# ---------------------------------------------------------------------------
# Laziness
# ---------------------------------------------------------------------------


class TestLazyIteration:
    def test_split_returns_iterator(self):
        result = split_for_scheme(_rows(3), "fedwire")
        assert inspect.isgenerator(result), (
            "split_for_scheme should return a generator, not materialise "
            "all chunks up front"
        )

    def test_can_pull_one_chunk_at_a_time(self):
        # 1M-row batch under Fedwire would be 1M chunks. Pulling just
        # the first chunk should not iterate the whole input.
        rows = _rows(1_000_000)
        gen = split_for_scheme(rows, "fedwire")
        first = next(gen)
        assert len(first) == 1
        assert first[0]["msg_id"] == "BATCH001-0001"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestErrorPaths:
    def test_unknown_scheme_raises(self):
        gen = split_for_scheme(_rows(1), "bogus")
        with pytest.raises(ValueError, match="Unknown scheme"):
            next(gen)


# ---------------------------------------------------------------------------
# Cardinality-violation message points at the splitter
# ---------------------------------------------------------------------------


class TestCardinalityMessagePointsAtSplitter:
    def test_message_includes_required_chunk_count(self):
        from pacs008.profiles import FedwireProfile

        violations = FedwireProfile().validate_business_rules(_rows(5))
        msgs = [
            v.message for v in violations if v.rule == "cardinality_exceeded"
        ]
        assert msgs, "expected a cardinality_exceeded violation"
        assert "Split into 5 chunks" in msgs[0]
        assert "split_for_scheme" in msgs[0]
