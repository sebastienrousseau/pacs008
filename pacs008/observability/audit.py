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

"""Cryptographically-signed audit envelope for pacs.008 generation.

DORA (the EU Digital Operational Resilience Act) entered its first
full enforcement year in 2026. One of the practical requirements is
end-to-end traceability of payment-message creation: who generated
what, against what input, and what validator decisions were
made — recorded in a form an operations team can present to a
regulator months later, without trusting the application
that produced it.

This module produces an :class:`AuditRecord` — a frozen, signed,
verifiable summary of a single generation event:

- Hash of the input payload (SHA-256).
- Hash of the output XML (SHA-256).
- Tuple of validator decisions (scheme + outcome).
- Active scheme profile name.
- UTC creation timestamp.
- Ed25519 signature over the canonical concatenation of the above.
- Fingerprint of the signing public key (SHA-256, first 16 hex).

:class:`Ed25519Signer` is the concrete signer that ships with v0.0.2;
its private key can be loaded from a PEM file or generated for
testing. Custom signers (HSM-backed, KMS-backed) implement the
:class:`Signer` ABC.

Use :func:`sign_envelope` to build a record and
:func:`verify_envelope` to check one. The output is JSON-friendly
via :meth:`AuditRecord.to_dict` for log-aggregation pipelines.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# ---------------------------------------------------------------------------
# Signer ABC + Ed25519 impl
# ---------------------------------------------------------------------------


class Signer(ABC):
    """Abstract message signer.

    Implementations carry the private signing material and expose the
    matching public key for verification.
    """

    @abstractmethod
    def sign(self, message: bytes) -> bytes:
        """Return the raw signature over ``message``."""

    @abstractmethod
    def public_key_bytes(self) -> bytes:
        """Return the raw public-key bytes."""

    def public_key_fingerprint(self) -> str:
        """First 16 hex chars of ``sha256(public_key_bytes())``."""
        digest = hashlib.sha256(self.public_key_bytes()).hexdigest()
        return digest[:16]


class Ed25519Signer(Signer):
    """Ed25519 signer backed by :mod:`cryptography`.

    Two ways to construct:

    - :meth:`generate` — fresh keypair, useful for tests/CI fixtures.
    - :meth:`from_private_key_pem` — load a PEM-encoded key from
      disk or a secret manager.
    """

    def __init__(self, private_key: ed25519.Ed25519PrivateKey) -> None:
        """Wrap a generated or loaded Ed25519 private key."""
        self._private = private_key
        self._public = private_key.public_key()

    @classmethod
    def generate(cls) -> Ed25519Signer:
        """Return a signer backed by a freshly-generated keypair."""
        return cls(ed25519.Ed25519PrivateKey.generate())

    @classmethod
    def from_private_key_pem(
        cls, pem: bytes, password: bytes | None = None
    ) -> Ed25519Signer:
        """Load an Ed25519 private key from PEM bytes."""
        key = serialization.load_pem_private_key(pem, password=password)
        if not isinstance(key, ed25519.Ed25519PrivateKey):
            raise TypeError("PEM did not contain an Ed25519 private key")
        return cls(key)

    def sign(self, message: bytes) -> bytes:
        """See :meth:`Signer.sign`."""
        return self._private.sign(message)

    def public_key_bytes(self) -> bytes:
        """See :meth:`Signer.public_key_bytes`."""
        return self._public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def public_key_pem(self) -> bytes:
        """Export the public key as PEM for storage or distribution."""
        return self._public.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


# ---------------------------------------------------------------------------
# AuditRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditRecord:
    """Signed audit record for a single pacs.008 generation event.

    Attributes:
        input_hash: SHA-256 hex digest of the canonical input
            payload (typically JSON-encoded with sorted keys).
        output_hash: SHA-256 hex digest of the generated XML bytes.
        validator_decisions: Tuple of short rule identifiers
            (e.g. ``"swift_charset:cleansed"``,
            ``"scheme:cbpr_plus:ok"``). Stable strings — these are
            the audit primitive.
        scheme: Scheme profile name in force when the record was
            produced.
        recorded_at: ISO 8601 UTC timestamp.
        signature: Raw signature bytes over the canonical payload
            (see :func:`_canonical_payload`).
        public_key_fingerprint: SHA-256 (first 16 hex) of the
            signing public key, for key-rotation tracking.
    """

    input_hash: str
    output_hash: str
    validator_decisions: tuple[str, ...]
    scheme: str
    recorded_at: str
    signature: bytes
    public_key_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict (signature is hex-encoded)."""
        return {
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "validator_decisions": list(self.validator_decisions),
            "scheme": self.scheme,
            "recorded_at": self.recorded_at,
            "signature": self.signature.hex(),
            "public_key_fingerprint": self.public_key_fingerprint,
        }


def sign_envelope(
    *,
    input_payload: bytes,
    output_xml: bytes,
    validator_decisions: Sequence[str],
    scheme: str,
    signer: Signer,
    recorded_at: datetime | None = None,
) -> AuditRecord:
    """Build and sign an :class:`AuditRecord`.

    Args:
        input_payload: Raw input bytes (CSV content, JSON-serialised
            row list, …). What the audit will hash.
        output_xml: Raw generated XML bytes.
        validator_decisions: Stable rule identifiers.
        scheme: Scheme profile name.
        signer: A :class:`Signer` implementation.
        recorded_at: Override the timestamp (defaults to UTC now).

    Returns:
        A populated, signed :class:`AuditRecord`.
    """
    timestamp = (recorded_at or datetime.now(timezone.utc)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    input_hash = hashlib.sha256(input_payload).hexdigest()
    output_hash = hashlib.sha256(output_xml).hexdigest()
    decisions = tuple(validator_decisions)

    canonical = _canonical_payload(
        input_hash=input_hash,
        output_hash=output_hash,
        validator_decisions=decisions,
        scheme=scheme,
        recorded_at=timestamp,
    )

    signature = signer.sign(canonical)
    return AuditRecord(
        input_hash=input_hash,
        output_hash=output_hash,
        validator_decisions=decisions,
        scheme=scheme,
        recorded_at=timestamp,
        signature=signature,
        public_key_fingerprint=signer.public_key_fingerprint(),
    )


def verify_envelope(record: AuditRecord, *, public_key_bytes: bytes) -> bool:
    """Verify the signature on a record using a raw Ed25519 public key.

    Args:
        record: The :class:`AuditRecord` to verify.
        public_key_bytes: Raw 32-byte Ed25519 public key. The same
            bytes returned by :meth:`Ed25519Signer.public_key_bytes`.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.

    Note:
        Returns ``False`` (does not raise) on any signature failure
        so the caller can branch cleanly without try/except in the
        common case.
    """
    canonical = _canonical_payload(
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        validator_decisions=record.validator_decisions,
        scheme=record.scheme,
        recorded_at=record.recorded_at,
    )
    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(
            public_key_bytes
        )
        public_key.verify(record.signature, canonical)
        return True
    except (InvalidSignature, ValueError):
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _canonical_payload(
    *,
    input_hash: str,
    output_hash: str,
    validator_decisions: tuple[str, ...],
    scheme: str,
    recorded_at: str,
) -> bytes:
    """Build the canonical byte sequence that the signature covers.

    JSON with sorted keys gives a deterministic encoding without
    requiring an extra canonicalization library.
    """
    payload = {
        "input_hash": input_hash,
        "output_hash": output_hash,
        "validator_decisions": list(validator_decisions),
        "scheme": scheme,
        "recorded_at": recorded_at,
    }
    return json.dumps(payload, sort_keys=True).encode("utf-8")
