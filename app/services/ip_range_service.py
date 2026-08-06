# app/services/ip_range_service.py
"""
Office 365 Safe Links IP range service.

Microsoft Defender for Office 365's "Safe Links" feature pre-scans every
link in an email before delivery, using a request crafted to look like a
real browser — so User-Agent substrings (see tracking.py's
_PROXY_SIGNATURES, which already catches Proofpoint/Barracuda) cannot catch
it. The only reliable signal is the request's source IP address, which
falls inside a published set of Microsoft datacenter ranges.

This service fetches that published list from Microsoft's own endpoint,
caches it in memory, and exposes a single is_office365_ip() check used by
tracking.py.
"""

import ipaddress
import logging
import time
import uuid

import requests

logger = logging.getLogger(__name__)

_ENDPOINT_URL = "https://endpoints.office.com/endpoints/worldwide"
_CACHE_TTL_SECONDS = 24 * 60 * 60  # Microsoft updates this list infrequently.
_REQUEST_TIMEOUT_SECONDS = 5

_NetworkType = ipaddress.IPv4Network | ipaddress.IPv6Network

_cached_networks: list[_NetworkType] = []
_cache_fetched_at: float = 0.0


def _fetch_networks() -> list[_NetworkType]:
    """
    Fetch and parse Microsoft's published Office 365 IP ranges.

    Returns an empty list on any failure (network error, bad response,
    unparseable entry) — a Microsoft-side outage should never break click
    tracking, it should just mean Safe Links clicks temporarily aren't
    filtered out.
    """
    params = {"ClientRequestId": str(uuid.uuid4()), "format": "json"}
    try:
        response = requests.get(
            _ENDPOINT_URL, params=params, timeout=_REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        entries = response.json()
    except (requests.RequestException, ValueError):
        logger.exception("Failed to fetch Office 365 IP ranges")
        return []

    networks: list[_NetworkType] = []
    for entry in entries:
        for cidr in entry.get("ips", []):
            try:
                networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                logger.warning("Skipping unparseable CIDR: %s", cidr)
    return networks


def _get_networks() -> list[_NetworkType]:
    """Return the cached range list, refreshing it if stale or empty."""
    global _cached_networks, _cache_fetched_at

    now: int | float = time.monotonic()
    if not _cached_networks or (now - _cache_fetched_at) > _CACHE_TTL_SECONDS:
        fetched = _fetch_networks()
        if fetched:
            _cached_networks = fetched
            _cache_fetched_at = now
    return _cached_networks


def is_office365_ip(ip_address: str) -> bool:
    """
    Return True if ip_address falls inside a published Microsoft Office 365
    / Safe Links range. Fails safe: an invalid IP or an unreachable
    Microsoft endpoint returns False, so a click is never wrongly dropped.
    """
    try:
        parsed = ipaddress.ip_address(ip_address)
    except ValueError:
        return False

    return any(parsed in network for network in _get_networks())
