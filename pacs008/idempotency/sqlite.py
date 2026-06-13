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

"""SQLite-backed idempotency store (persistent, single-host safe)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pacs008.idempotency.base import IdempotencyEntry, IdempotencyStore


class SQLiteStore(IdempotencyStore):
    """File-backed idempotency store.

    Suitable for production single-host installs. The on-disk file
    survives process restarts so a retry minutes after a crash still
    sees the original recording.

    Concurrency: a single connection guarded by a lock — fine for the
    pacs008 pipeline's batch-oriented usage. Multi-process callers
    can each open their own SQLiteStore against the same file (SQLite
    handles cross-process locking).
    """

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS idempotency_entries (
            key TEXT PRIMARY KEY,
            payload_hash TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        )
    """
    _IDX = (
        "CREATE INDEX IF NOT EXISTS idx_idem_recorded_at "
        "ON idempotency_entries(recorded_at)"
    )

    def __init__(self, path: str | Path) -> None:
        """Open or create the SQLite file at ``path``.

        ``path`` may be ``":memory:"`` for an in-process throwaway
        store — useful in tests, but you almost certainly want
        :class:`~pacs008.idempotency.memory.MemoryStore` for that.
        """
        self._path = str(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(
            self._path,
            check_same_thread=False,
            isolation_level=None,  # autocommit
        )
        self._conn.execute(self._SCHEMA)
        self._conn.execute(self._IDX)

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def lookup(
        self, key: str, *, window: timedelta
    ) -> IdempotencyEntry | None:
        """See :meth:`IdempotencyStore.lookup`."""
        cutoff = _utcnow() - window
        with self._lock:
            row = self._conn.execute(
                "SELECT key, payload_hash, recorded_at "
                "FROM idempotency_entries WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        recorded_at = _parse_iso(row[2])
        if recorded_at < cutoff:
            # Expired — best-effort purge.
            with self._lock:
                self._conn.execute(
                    "DELETE FROM idempotency_entries WHERE key = ?",
                    (key,),
                )
            return None
        return IdempotencyEntry(
            key=row[0],
            payload_hash=row[1],
            recorded_at=recorded_at,
        )

    def record(
        self,
        key: str,
        payload_hash: str,
        *,
        recorded_at: datetime | None = None,
    ) -> IdempotencyEntry:
        """See :meth:`IdempotencyStore.record`."""
        recorded_at = recorded_at or _utcnow()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO idempotency_entries "
                "(key, payload_hash, recorded_at) VALUES (?, ?, ?)",
                (key, payload_hash, recorded_at.isoformat()),
            )
        return IdempotencyEntry(
            key=key,
            payload_hash=payload_hash,
            recorded_at=recorded_at,
        )

    def purge_older_than(self, cutoff: datetime) -> int:
        """See :meth:`IdempotencyStore.purge_older_than`."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM idempotency_entries WHERE recorded_at < ?",
                (cutoff.isoformat(),),
            )
            return cursor.rowcount or 0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    """Robustly parse an ISO 8601 timestamp emitted by ``datetime.isoformat``."""
    return datetime.fromisoformat(value)
