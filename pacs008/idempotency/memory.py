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

"""In-memory idempotency store (LRU with TTL)."""

from __future__ import annotations

import threading
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

from pacs008.idempotency.base import IdempotencyEntry, IdempotencyStore


class MemoryStore(IdempotencyStore):
    """Thread-safe in-process LRU store with TTL eviction.

    Suitable for single-process pipelines, tests, and CI runs. For
    multi-process or persistent setups, use
    :class:`~pacs008.idempotency.sqlite.SQLiteStore` or a custom
    backend.
    """

    def __init__(self, max_entries: int = 100_000) -> None:
        """Initialise the store.

        Args:
            max_entries: Soft cap on retained entries (oldest evicted
                via LRU when exceeded).
        """
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._entries: OrderedDict[str, IdempotencyEntry] = OrderedDict()
        self._lock = threading.Lock()

    def lookup(
        self, key: str, *, window: timedelta
    ) -> IdempotencyEntry | None:
        cutoff = _utcnow() - window
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.recorded_at < cutoff:
                # Expired — drop it.
                self._entries.pop(key, None)
                return None
            # Touch LRU position.
            self._entries.move_to_end(key)
            return entry

    def record(
        self,
        key: str,
        payload_hash: str,
        *,
        recorded_at: datetime | None = None,
    ) -> IdempotencyEntry:
        recorded_at = recorded_at or _utcnow()
        entry = IdempotencyEntry(
            key=key, payload_hash=payload_hash, recorded_at=recorded_at
        )
        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
        return entry

    def purge_older_than(self, cutoff: datetime) -> int:
        purged = 0
        with self._lock:
            keys = [
                k for k, e in self._entries.items() if e.recorded_at < cutoff
            ]
            for k in keys:
                self._entries.pop(k, None)
                purged += 1
        return purged

    def __len__(self) -> int:
        return len(self._entries)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
