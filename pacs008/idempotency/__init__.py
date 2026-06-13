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

"""Idempotency layer for pacs008.

Payment hubs see retries from network blips, dropped acks, and
client timeouts. Without duplicate detection the same CSV processed
twice double-debits — a real audit-and-treasury failure.

This package exposes a tiny pluggable interface:

- :class:`IdempotencyStore` — ABC. Implementations decide where
  ``(key, payload_hash, timestamp)`` triples live.
- :class:`MemoryStore` — in-process LRU with TTL. The default for
  tests, single-process pipelines, and CI runs.
- :class:`SQLiteStore` — file-backed, single-writer-safe. The
  default for production single-host installs.
- :class:`IdempotencyViolation` — raised when ``check`` finds a
  duplicate under the configured policy.

Default policy is **error** (raise on duplicate). ``skip`` and
``warn`` modes are also supported. Silent dedup is opt-in — banking
audits hate "we quietly dropped it".
"""

from pacs008.idempotency.base import (
    IdempotencyEntry,
    IdempotencyStore,
    IdempotencyViolation,
    OnDuplicate,
    compute_payload_hash,
)
from pacs008.idempotency.memory import MemoryStore
from pacs008.idempotency.sqlite import SQLiteStore

__all__ = [
    "IdempotencyEntry",
    "IdempotencyStore",
    "IdempotencyViolation",
    "MemoryStore",
    "OnDuplicate",
    "SQLiteStore",
    "compute_payload_hash",
]
