"""Tests for retry logic and exponential backoff."""
import pytest

from app.services.delivery_service import compute_backoff, is_retryable_status


class TestRetryableStatusCodes:
    """Verify which HTTP status codes trigger retries."""

    @pytest.mark.parametrize("code", [200, 201, 204, 301, 302, 304])
    def test_success_and_redirect_not_retryable(self, code: int):
        assert is_retryable_status(code) is False

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 405, 409, 422])
    def test_client_errors_not_retryable(self, code: int):
        assert is_retryable_status(code) is False

    def test_408_request_timeout_is_retryable(self):
        assert is_retryable_status(408) is True

    def test_429_too_many_requests_is_retryable(self):
        assert is_retryable_status(429) is True

    @pytest.mark.parametrize("code", [500, 502, 503, 504])
    def test_server_errors_are_retryable(self, code: int):
        assert is_retryable_status(code) is True


class TestExponentialBackoff:
    """Verify backoff calculation."""

    def test_first_retry_within_expected_range(self):
        """First retry (attempt 0) should be base_delay * 2^0 = 1s, plus up to 50% jitter."""
        for _ in range(100):
            delay = compute_backoff(attempt_number=0, base_delay=1.0, max_delay=3600.0)
            assert 1.0 <= delay <= 1.5

    def test_second_retry_within_expected_range(self):
        """Second retry (attempt 1) should be base_delay * 2^1 = 2s, plus jitter."""
        for _ in range(100):
            delay = compute_backoff(attempt_number=1, base_delay=1.0, max_delay=3600.0)
            assert 2.0 <= delay <= 3.0

    def test_third_retry_within_expected_range(self):
        """Third retry (attempt 2) should be base_delay * 2^2 = 4s, plus jitter."""
        for _ in range(100):
            delay = compute_backoff(attempt_number=2, base_delay=1.0, max_delay=3600.0)
            assert 4.0 <= delay <= 6.0

    def test_backoff_respects_max_delay_ceiling(self):
        """Backoff should never exceed max_delay."""
        for _ in range(100):
            delay = compute_backoff(attempt_number=20, base_delay=1.0, max_delay=60.0)
            assert delay <= 60.0

    def test_backoff_increases_exponentially(self):
        """Each successive attempt should have a higher minimum delay."""
        min_delays = []
        for attempt in range(5):
            delays = [
                compute_backoff(attempt_number=attempt, base_delay=1.0, max_delay=3600.0)
                for _ in range(50)
            ]
            min_delays.append(min(delays))

        # Each minimum should be greater than the previous
        for i in range(1, len(min_delays)):
            assert min_delays[i] > min_delays[i - 1]

    def test_custom_base_delay(self):
        """Verify custom base delay is respected."""
        for _ in range(100):
            delay = compute_backoff(attempt_number=0, base_delay=5.0, max_delay=3600.0)
            assert 5.0 <= delay <= 7.5

    def test_jitter_introduces_randomness(self):
        """Multiple calls with same params should produce different values."""
        delays = {
            compute_backoff(attempt_number=2, base_delay=1.0, max_delay=3600.0)
            for _ in range(50)
        }
        # With 50 samples, we should have many distinct values
        assert len(delays) > 10


class TestMaxAttemptsLogic:
    """Verify max attempts boundary conditions."""

    def test_attempt_under_max_is_retryable_scenario(self):
        """If attempt_count < max_attempts and status is retryable, should retry."""
        attempt_count = 3
        max_attempts = 5
        status_code = 500

        should_retry = is_retryable_status(status_code) and attempt_count < max_attempts
        assert should_retry is True

    def test_attempt_at_max_should_not_retry(self):
        """If attempt_count >= max_attempts, should not retry even if retryable."""
        attempt_count = 5
        max_attempts = 5
        status_code = 500

        should_retry = is_retryable_status(status_code) and attempt_count < max_attempts
        assert should_retry is False

    def test_non_retryable_code_never_retries(self):
        """Non-retryable codes should fail immediately regardless of attempt count."""
        attempt_count = 1
        max_attempts = 5
        status_code = 404

        should_retry = is_retryable_status(status_code) and attempt_count < max_attempts
        assert should_retry is False
