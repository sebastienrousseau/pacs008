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

"""Idempotency store ABC, value types, and the canonical key hashing."""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from pacs008.exceptions import Pacs008Error


class OnDuplicate(Enum):
    """Policy for what ``check`` does when a key is already known."""

    ERROR = "error"
    """Raise :class:`IdempotencyViolation`. The safe default."""

    SKIP = "skip"
    """Return ``True`` quietly; the caller drops the request."""

    WARN = "warn"
    """Return ``True`` but the caller continues (audit-tagged)."""


class IdempotencyViolation(Pacs008Error):
    """Raised when ``check`` finds a duplicate under ``OnDuplicate.ERROR``.

    Carries the previously-seen entry for diagnostics.
    """

    def __init__(self, key: str, previous: IdempotencyEntry) -> None:
        """Initialise the violation with the duplicate key and prior entry."""
        self.key = key
        self.previous = previous
        super().__init__(
            f"idempotency key {key!r} already seen at "
            f"{previous.recorded_at.isoformat()} "
            f"(payload hash {previous.payload_hash[:16]}…)"
        )


@dataclass(frozen=True)
class IdempotencyEntry:
    """A single previously-seen (key, payload_hash, timestamp)."""

    key: str
    payload_hash: str
    recorded_at: datetime


class IdempotencyStore(ABC):
    """Abstract pluggable store for idempotency keys.

    Implementations decide where the ``(key, payload_hash,
    recorded_at)`` triples live: process memory, SQLite, Redis, a
    Cloud KV, etc.
    """

    @abstractmethod
    def lookup(
        self, key: str, *, window: timedelta
    ) -> IdempotencyEntry | None:
        """Return the most recent entry for ``key`` within ``window``, if any."""

    @abstractmethod
    def record(
        self,
        key: str,
        payload_hash: str,
        *,
        recorded_at: datetime | None = None,
    ) -> IdempotencyEntry:
        """Record ``(key, payload_hash)`` and return the stored entry."""

    @abstractmethod
    def purge_older_than(self, cutoff: datetime) -> int:
        """Drop entries older than ``cutoff``. Returns count purged."""

    # ----- composite operations -----

    def check(
        self,
        key: str,
        payload_hash: str,
        *,
        window: timedelta = timedelta(hours=24),
        on_duplicate: OnDuplicate = OnDuplicate.ERROR,
        recorded_at: datetime | None = None,
    ) -> bool:
        """Check and record a key in one atomic-ish step.

        Args:
            key: Idempotency key (typically the message ``MsgId``
                or a transaction's ``UETR``).
            payload_hash: Hex digest of the payload, computed by
                :func:`compute_payload_hash`.
            window: How far back to consider a previous sighting.
                Defaults to 24h.
            on_duplicate: What to do if ``key`` was seen within
                ``window``. Default is to raise.
            recorded_at: Timestamp to associate with the new
                recording. Defaults to ``datetime.now(timezone.utc)``.

        Returns:
            ``True`` if the key was a duplicate (and policy was
            non-ERROR), ``False`` if it was novel and has been
            recorded.

        Raises:
            IdempotencyViolation: when a duplicate is found and
                ``on_duplicate`` is :attr:`OnDuplicate.ERROR`.
        """
        previous = self.lookup(key, window=window)
        if previous is not None:
            if on_duplicate is OnDuplicate.ERROR:
                raise IdempotencyViolation(key=key, previous=previous)
            return True

        self.record(key, payload_hash, recorded_at=recorded_at)
        return False


def compute_payload_hash(payload: Any) -> str:
    """Stable hex SHA-256 digest of ``payload``.

    Dicts are JSON-encoded with sorted keys for stability; bytes
    are hashed directly; everything else is stringified.
    """
    if isinstance(payload, (bytes, bytearray)):
        data = bytes(payload)
    elif isinstance(payload, str):
        data = payload.encode("utf-8")
    elif isinstance(payload, (dict, list)):
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
    else:
        data = str(payload).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _utcnow() -> datetime:
    """Module-internal clock helper — overridable in tests via monkeypatch."""
    return datetime.now(timezone.utc)
