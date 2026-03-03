import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings


_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # If we can't parse it, block it
    return any(addr in network for network in _PRIVATE_NETWORKS)


def validate_webhook_url(url: str) -> None:
    """Validate a webhook URL, blocking private/loopback IPs unless allowed.

    Raises ValueError if the URL is invalid or targets a private IP.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}. Only http/https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    if settings.ALLOW_PRIVATE_IPS:
        return

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

    for family, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        if _is_private_ip(ip_str):
            raise ValueError(
                f"Webhook URL resolves to private/loopback IP ({ip_str}). "
                "Private IPs are blocked in production. Set ALLOW_PRIVATE_IPS=true for development."
            )
