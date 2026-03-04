"""Tests for HMAC-SHA256 signature computation and verification."""
import pytest

from app.security.signing import compute_signature, verify_signature


class TestHMACSignature:
    """Test HMAC-SHA256 signing and verification."""

    def test_compute_signature_deterministic(self):
        """Same input always produces the same signature."""
        payload = b'{"order_id":123}'
        secret = "my-secret"
        sig1 = compute_signature(payload, secret)
        sig2 = compute_signature(payload, secret)
        assert sig1 == sig2

    def test_compute_signature_format(self):
        """Signature should be a hex string."""
        sig = compute_signature(b"test", "secret")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex digest is 64 chars
        assert all(c in "0123456789abcdef" for c in sig)

    def test_verify_valid_signature(self):
        """Verification should pass for payload signed with correct secret."""
        payload = b'{"event":"test"}'
        secret = "webhook-secret-123"
        signature = compute_signature(payload, secret)
        assert verify_signature(payload, secret, signature) is True

    def test_verify_tampered_payload_fails(self):
        """Verification should fail if payload was modified after signing."""
        original = b'{"amount":100}'
        tampered = b'{"amount":999}'
        secret = "my-secret"
        signature = compute_signature(original, secret)
        assert verify_signature(tampered, secret, signature) is False

    def test_verify_wrong_secret_fails(self):
        """Verification should fail if a different secret is used."""
        payload = b'{"data":"value"}'
        signature = compute_signature(payload, "correct-secret")
        assert verify_signature(payload, "wrong-secret", signature) is False

    def test_different_payloads_different_signatures(self):
        """Different payloads should produce different signatures."""
        secret = "shared-secret"
        sig1 = compute_signature(b'{"a":1}', secret)
        sig2 = compute_signature(b'{"a":2}', secret)
        assert sig1 != sig2

    def test_different_secrets_different_signatures(self):
        """Same payload with different secrets should produce different signatures."""
        payload = b'{"a":1}'
        sig1 = compute_signature(payload, "secret-1")
        sig2 = compute_signature(payload, "secret-2")
        assert sig1 != sig2

    def test_empty_payload(self):
        """Should handle empty payload without error."""
        sig = compute_signature(b"", "secret")
        assert verify_signature(b"", "secret", sig) is True

    def test_unicode_secret(self):
        """Should handle Unicode characters in secret."""
        payload = b'{"test":true}'
        secret = "s\u00e9cret-\u00fcnicode"
        sig = compute_signature(payload, secret)
        assert verify_signature(payload, secret, sig) is True
