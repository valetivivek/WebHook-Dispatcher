import json
import random
import time

import httpx

from app.config import settings
from app.security.signing import compute_signature
from app.logging import get_logger

logger = get_logger(__name__)

# Status codes that should not be retried (client errors), except these two
RETRYABLE_4XX = {408, 429}


def is_retryable_status(status_code: int) -> bool:
    if 200 <= status_code < 400:
        return False
    if status_code >= 500:
        return True
    if status_code in RETRYABLE_4XX:
        return True
    return False


def compute_backoff(attempt_number: int, base_delay: float, max_delay: float) -> float:
    """Compute exponential backoff with full jitter.

    Formula: min(base_delay * 2^attempt + jitter, max_delay)
    Jitter: uniform(0, delay * 0.5)
    """
    delay = base_delay * (2 ** attempt_number)
    jitter = random.uniform(0, delay * 0.5)
    return min(delay + jitter, max_delay)


def deliver_http(
    url: str,
    payload: dict,
    secret: str,
    event_id: str,
    event_type: str,
    idempotency_key: str,
) -> tuple[int | None, str | None, str | None, float]:
    """Perform the outbound HTTP POST delivery.

    Returns (status_code, response_body, error, latency_ms).
    status_code is None on network errors.
    """
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = compute_signature(payload_bytes, secret)

    headers = {
        "Content-Type": "application/json",
        "X-Signature": f"sha256={signature}",
        "X-Event-Id": event_id,
        "X-Event-Type": event_type,
        "Idempotency-Key": idempotency_key,
        "User-Agent": "WebhookDispatcher/1.0",
    }

    start = time.monotonic()
    try:
        with httpx.Client(timeout=settings.DELIVERY_TIMEOUT_SECONDS) as client:
            response = client.post(url, content=payload_bytes, headers=headers)
            latency_ms = (time.monotonic() - start) * 1000

            # Truncate response body to 1KB
            body = response.text[:1024] if response.text else None

            return response.status_code, body, None, latency_ms

    except httpx.TimeoutException as exc:
        latency_ms = (time.monotonic() - start) * 1000
        error_msg = f"Timeout after {settings.DELIVERY_TIMEOUT_SECONDS}s: {exc}"
        logger.warning("Delivery timeout", extra={"event_id": event_id, "url": url})
        return None, None, error_msg, latency_ms

    except httpx.RequestError as exc:
        latency_ms = (time.monotonic() - start) * 1000
        error_msg = f"Network error: {exc}"
        logger.warning("Delivery network error", extra={"event_id": event_id, "url": url})
        return None, None, error_msg, latency_ms
