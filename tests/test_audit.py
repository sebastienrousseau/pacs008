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

"""Tests for the signed audit envelope (pacs008.observability.audit)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from pacs008.observability.audit import (
    AuditRecord,
    Ed25519Signer,
    Signer,
    sign_envelope,
    verify_envelope,
)


@pytest.fixture
def signer() -> Ed25519Signer:
    return Ed25519Signer.generate()


def _record(signer: Signer, **overrides) -> AuditRecord:
    kwargs = dict(
        input_payload=b"csv-content",
        output_xml=b"<Document/>",
        validator_decisions=("swift_charset:cleansed",),
        scheme="cbpr_plus",
        signer=signer,
    )
    kwargs.update(overrides)
    return sign_envelope(**kwargs)


# ---------------------------------------------------------------------------
# Ed25519Signer construction
# ---------------------------------------------------------------------------


class TestEd25519SignerConstruction:
    def test_generate_yields_signer(self):
        s = Ed25519Signer.generate()
        assert isinstance(s, Ed25519Signer)

    def test_from_pem_round_trip(self):
        # Generate a fresh keypair, export to PEM, reload, verify
        # signatures from each side validate against the other.
        original = Ed25519Signer.generate()
        priv_pem = original._private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        reloaded = Ed25519Signer.from_private_key_pem(priv_pem)
        rec_from_original = _record(original)
        assert verify_envelope(
            rec_from_original,
            public_key_bytes=reloaded.public_key_bytes(),
        )

    def test_from_pem_rejects_non_ed25519(self):
        # An RSA key in PEM form should be rejected.
        rsa_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )
        pem = rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with pytest.raises(TypeError, match="Ed25519"):
            Ed25519Signer.from_private_key_pem(pem)

    def test_public_key_bytes_length(self, signer):
        # Raw Ed25519 public keys are always 32 bytes.
        assert len(signer.public_key_bytes()) == 32

    def test_fingerprint_is_16_hex(self, signer):
        fp = signer.public_key_fingerprint()
        assert len(fp) == 16
        int(fp, 16)

    def test_fingerprint_stable_per_signer(self, signer):
        assert (
            signer.public_key_fingerprint()
            == signer.public_key_fingerprint()
        )

    def test_distinct_signers_have_distinct_fingerprints(self):
        a = Ed25519Signer.generate()
        b = Ed25519Signer.generate()
        assert a.public_key_fingerprint() != b.public_key_fingerprint()

    def test_public_key_pem_exportable(self, signer):
        pem = signer.public_key_pem()
        assert pem.startswith(b"-----BEGIN PUBLIC KEY-----")


# ---------------------------------------------------------------------------
# sign_envelope / verify_envelope
# ---------------------------------------------------------------------------


class TestSignVerify:
    def test_round_trip_valid(self, signer):
        rec = _record(signer)
        assert verify_envelope(
            rec, public_key_bytes=signer.public_key_bytes()
        )

    def test_wrong_public_key_fails(self, signer):
        rec = _record(signer)
        other = Ed25519Signer.generate()
        assert not verify_envelope(
            rec, public_key_bytes=other.public_key_bytes()
        )

    def test_tampered_input_hash_fails(self, signer):
        rec = _record(signer)
        tampered = AuditRecord(
            input_hash="0" * 64,
            output_hash=rec.output_hash,
            validator_decisions=rec.validator_decisions,
            scheme=rec.scheme,
            recorded_at=rec.recorded_at,
            signature=rec.signature,
            public_key_fingerprint=rec.public_key_fingerprint,
        )
        assert not verify_envelope(
            tampered, public_key_bytes=signer.public_key_bytes()
        )

    def test_tampered_decisions_fails(self, signer):
        rec = _record(signer)
        tampered = AuditRecord(
            input_hash=rec.input_hash,
            output_hash=rec.output_hash,
            validator_decisions=("OTHER",),
            scheme=rec.scheme,
            recorded_at=rec.recorded_at,
            signature=rec.signature,
            public_key_fingerprint=rec.public_key_fingerprint,
        )
        assert not verify_envelope(
            tampered, public_key_bytes=signer.public_key_bytes()
        )

    def test_tampered_scheme_fails(self, signer):
        rec = _record(signer)
        tampered = AuditRecord(
            input_hash=rec.input_hash,
            output_hash=rec.output_hash,
            validator_decisions=rec.validator_decisions,
            scheme="other_scheme",
            recorded_at=rec.recorded_at,
            signature=rec.signature,
            public_key_fingerprint=rec.public_key_fingerprint,
        )
        assert not verify_envelope(
            tampered, public_key_bytes=signer.public_key_bytes()
        )

    def test_garbage_public_key_returns_false(self, signer):
        rec = _record(signer)
        assert not verify_envelope(
            rec, public_key_bytes=b"\x00" * 5
        )

    def test_input_hash_is_sha256_hex(self, signer):
        rec = _record(signer, input_payload=b"abc")
        # sha256("abc") = ba7816bf...
        assert rec.input_hash.startswith("ba7816bf")
        assert len(rec.input_hash) == 64

    def test_recorded_at_default_is_iso_utc_z(self, signer):
        rec = _record(signer)
        assert rec.recorded_at.endswith("Z")
        # Parseable.
        datetime.fromisoformat(rec.recorded_at.rstrip("Z"))

    def test_recorded_at_override(self, signer):
        when = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        rec = _record(signer, recorded_at=when)
        assert rec.recorded_at == "2026-01-01T12:00:00Z"

    def test_to_dict_json_friendly(self, signer):
        rec = _record(signer)
        d = rec.to_dict()
        assert isinstance(d["signature"], str)  # hex-encoded
        assert isinstance(d["validator_decisions"], list)
        # No bytes, no tuples — JSON can serialise it.
        import json

        json.dumps(d)


# ---------------------------------------------------------------------------
# AuditRecord immutability
# ---------------------------------------------------------------------------


class TestAuditRecordImmutability:
    def test_frozen(self, signer):
        rec = _record(signer)
        with pytest.raises(Exception):
            rec.scheme = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Custom Signer ABC contract
# ---------------------------------------------------------------------------


class TestCustomSigner:
    def test_can_implement_signer_abc(self):
        # A trivial deterministic "signer" for tests — verifies the
        # ABC plays well with non-Ed25519 implementations from the
        # public-API perspective. Verification doesn't apply here.
        class FixedSigner(Signer):
            def sign(self, message: bytes) -> bytes:
                return b"FIXED"

            def public_key_bytes(self) -> bytes:
                return b"PUB"

        s = FixedSigner()
        rec = _record(s, input_payload=b"x")
        assert rec.signature == b"FIXED"
        assert (
            rec.public_key_fingerprint
            == FixedSigner().public_key_fingerprint()
        )

    def test_cannot_instantiate_signer_abc(self):
        class Incomplete(Signer):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]
