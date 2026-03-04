"""Tests for URL validation and SSRF protection."""
import pytest
from unittest.mock import patch

from app.security.url_validator import validate_webhook_url, _is_private_ip


class TestPrivateIPDetection:
    """Test the private IP detection helper."""

    @pytest.mark.parametrize(
        "ip",
        ["127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.1.1", "::1"],
    )
    def test_private_ips_detected(self, ip: str):
        assert _is_private_ip(ip) is True

    @pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
    def test_public_ips_not_detected(self, ip: str):
        assert _is_private_ip(ip) is False

    def test_unparseable_ip_treated_as_private(self):
        assert _is_private_ip("not-an-ip") is True


class TestURLValidation:
    """Test the full URL validation including DNS resolution."""

    def test_invalid_scheme_rejected(self):
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            validate_webhook_url("ftp://example.com/hook")

    def test_empty_hostname_rejected(self):
        with pytest.raises(ValueError, match="valid hostname"):
            validate_webhook_url("http:///hook")

    @patch("app.security.url_validator.settings")
    @patch("app.security.url_validator.socket.getaddrinfo")
    def test_private_ip_blocked_in_production(self, mock_dns, mock_settings):
        mock_settings.ALLOW_PRIVATE_IPS = False
        mock_dns.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 0)),
        ]
        with pytest.raises(ValueError, match="private/loopback IP"):
            validate_webhook_url("https://localhost/hook")

    @patch("app.security.url_validator.settings")
    def test_private_ip_allowed_in_dev(self, mock_settings):
        mock_settings.ALLOW_PRIVATE_IPS = True
        # Should not raise
        validate_webhook_url("https://localhost/hook")

    @patch("app.security.url_validator.settings")
    @patch("app.security.url_validator.socket.getaddrinfo")
    def test_public_ip_allowed(self, mock_dns, mock_settings):
        mock_settings.ALLOW_PRIVATE_IPS = False
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
        ]
        # Should not raise
        validate_webhook_url("https://example.com/hook")

    @patch("app.security.url_validator.settings")
    @patch("app.security.url_validator.socket.getaddrinfo")
    def test_dns_failure_rejected(self, mock_dns, mock_settings):
        import socket

        mock_settings.ALLOW_PRIVATE_IPS = False
        mock_dns.side_effect = socket.gaierror("DNS resolution failed")
        with pytest.raises(ValueError, match="Could not resolve"):
            validate_webhook_url("https://nonexistent.invalid/hook")
