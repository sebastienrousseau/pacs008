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

"""Tests for pacs008.idempotency — pluggable idempotency stores."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

import pytest

from pacs008.idempotency import (
    IdempotencyEntry,
    IdempotencyStore,
    IdempotencyViolation,
    MemoryStore,
    OnDuplicate,
    SQLiteStore,
    compute_payload_hash,
)

# ---------------------------------------------------------------------------
# compute_payload_hash
# ---------------------------------------------------------------------------


class TestComputePayloadHash:
    def test_dict_is_stable_under_key_reorder(self):
        a = compute_payload_hash({"x": 1, "y": 2})
        b = compute_payload_hash({"y": 2, "x": 1})
        assert a == b

    def test_string_vs_bytes_match_when_equal_bytes(self):
        s = "hello"
        assert compute_payload_hash(s) == compute_payload_hash(s.encode())

    def test_different_payloads_different_hashes(self):
        assert compute_payload_hash("a") != compute_payload_hash("b")

    def test_hash_is_hex_sha256_length(self):
        h = compute_payload_hash("anything")
        assert len(h) == 64
        int(h, 16)  # hex-parseable


# ---------------------------------------------------------------------------
# Shared store contract — parametrised across stores
# ---------------------------------------------------------------------------


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path) -> IdempotencyStore:
    if request.param == "memory":
        return MemoryStore()
    return SQLiteStore(tmp_path / "idem.db")


class TestStoreContract:
    def test_fresh_key_is_novel(self, store):
        assert store.check("k1", "h1", window=timedelta(hours=1)) is False

    def test_repeat_key_within_window_raises_by_default(self, store):
        store.check("k1", "h1", window=timedelta(hours=1))
        with pytest.raises(IdempotencyViolation) as excinfo:
            store.check("k1", "h1", window=timedelta(hours=1))
        assert excinfo.value.key == "k1"
        assert excinfo.value.previous.payload_hash == "h1"

    def test_skip_policy_returns_true_silently(self, store):
        store.check("k1", "h1", window=timedelta(hours=1))
        assert (
            store.check(
                "k1",
                "h1",
                window=timedelta(hours=1),
                on_duplicate=OnDuplicate.SKIP,
            )
            is True
        )

    def test_warn_policy_returns_true(self, store):
        store.check("k1", "h1", window=timedelta(hours=1))
        assert (
            store.check(
                "k1",
                "h1",
                window=timedelta(hours=1),
                on_duplicate=OnDuplicate.WARN,
            )
            is True
        )

    def test_expired_entry_treated_as_novel(self, store):
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        store.record("k1", "h1", recorded_at=old)
        assert store.check("k1", "h1", window=timedelta(hours=24)) is False

    def test_distinct_keys_are_independent(self, store):
        assert store.check("k1", "h1", window=timedelta(hours=1)) is False
        assert store.check("k2", "h1", window=timedelta(hours=1)) is False

    def test_purge_older_than(self, store):
        old = datetime.now(timezone.utc) - timedelta(days=2)
        store.record("k_old", "h", recorded_at=old)
        store.record("k_new", "h")
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        purged = store.purge_older_than(cutoff)
        assert purged == 1
        # k_old gone, k_new still findable.
        assert store.lookup("k_old", window=timedelta(days=10)) is None
        assert store.lookup("k_new", window=timedelta(days=10)) is not None


# ---------------------------------------------------------------------------
# MemoryStore specifics
# ---------------------------------------------------------------------------


class TestMemoryStoreSpecifics:
    def test_max_entries_evicts_lru(self):
        s = MemoryStore(max_entries=3)
        s.record("a", "h")
        s.record("b", "h")
        s.record("c", "h")
        s.record("d", "h")  # should evict 'a'
        assert s.lookup("a", window=timedelta(hours=1)) is None
        assert s.lookup("d", window=timedelta(hours=1)) is not None

    def test_lookup_touches_lru(self):
        s = MemoryStore(max_entries=3)
        s.record("a", "h")
        s.record("b", "h")
        s.record("c", "h")
        # touch 'a' so it isn't the LRU.
        s.lookup("a", window=timedelta(hours=1))
        s.record("d", "h")  # should evict 'b' (now the LRU).
        assert s.lookup("a", window=timedelta(hours=1)) is not None
        assert s.lookup("b", window=timedelta(hours=1)) is None

    def test_zero_max_entries_rejected(self):
        with pytest.raises(ValueError):
            MemoryStore(max_entries=0)

    def test_len(self):
        s = MemoryStore()
        s.record("a", "h")
        s.record("b", "h")
        assert len(s) == 2


# ---------------------------------------------------------------------------
# SQLiteStore specifics
# ---------------------------------------------------------------------------


class TestSQLiteStoreSpecifics:
    def test_persists_across_instances(self, tmp_path):
        db = tmp_path / "idem.db"
        s1 = SQLiteStore(db)
        s1.record("k1", "h1")
        s1.close()
        s2 = SQLiteStore(db)
        entry = s2.lookup("k1", window=timedelta(days=10))
        assert entry is not None
        assert entry.payload_hash == "h1"

    def test_memory_path_works(self):
        s = SQLiteStore(":memory:")
        s.record("k1", "h1")
        assert s.lookup("k1", window=timedelta(hours=1)) is not None


# ---------------------------------------------------------------------------
# Concurrent safety (MemoryStore — sqlite is single-conn locked similarly)
# ---------------------------------------------------------------------------


class TestConcurrentSafety:
    def test_no_race_under_threading(self):
        # 8 threads each record their own key 50 times — the lock
        # should keep the LRU dict from corrupting.
        s = MemoryStore(max_entries=10_000)

        def writer(tid: int) -> None:
            for i in range(50):
                s.record(f"t{tid}-k{i}", f"h-{tid}-{i}")

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(s) == 8 * 50


# ---------------------------------------------------------------------------
# IdempotencyEntry / IdempotencyStore ABC contract
# ---------------------------------------------------------------------------


class TestABCContract:
    def test_idempotency_entry_is_frozen(self):
        e = IdempotencyEntry(
            key="k", payload_hash="h", recorded_at=datetime.now()
        )
        with pytest.raises(Exception):
            e.key = "other"  # type: ignore[misc]

    def test_cannot_instantiate_abc(self):
        class Incomplete(IdempotencyStore):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]
