import hashlib
import hmac


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_signature(payload_bytes: bytes, secret: str, signature: str) -> bool:
    expected = compute_signature(payload_bytes, secret)
    return hmac.compare_digest(expected, signature)
