"""HTTP helpers for Signal K discovery and vessel data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import async_timeout
from aiohttp import ClientSession

from .auth import AuthRequired, build_auth_headers, build_ssl_param


@dataclass(frozen=True)
class DiscoveryInfo:
    base_url: str
    ws_url: str
    server_id: str | None
    server_version: str | None


def normalize_base_url(host: str, port: int, use_ssl: bool) -> str:
    # Normalize into a canonical REST base so comparisons and stored config stay stable.
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}/signalk/v1/api/"


def normalize_ws_url(host: str, port: int, use_ssl: bool) -> str:
    # Normalize the WS endpoint so we always connect to the same stream path.
    scheme = "wss" if use_ssl else "ws"
    return f"{scheme}://{host}:{port}/signalk/v1/stream?subscribe=none"


def normalize_server_url(host: str, port: int, use_ssl: bool) -> str:
    # Normalize the server origin to avoid mixing host-only and full URL inputs.
    scheme = "https" if use_ssl else "http"
    return f"{scheme}://{host}:{port}"


def normalize_host_input(host: str) -> tuple[str, int | None, str | None]:
    # Accept raw host or full URL input and normalize to a host/port/scheme triple.
    if host.startswith("http://") or host.startswith("https://"):
        parsed = urlsplit(host)
        hostname = (parsed.hostname or "").lower()
        return hostname, parsed.port, parsed.scheme
    return host.lower(), None, None


async def async_fetch_discovery(
    session: ClientSession, server_url: str, verify_ssl: bool
) -> DiscoveryInfo:
    url = urlunsplit(urlsplit(server_url)._replace(path="/signalk", query=""))
    ssl_context = build_ssl_param(verify_ssl)

    # The discovery document is the source of truth for REST/WS endpoints.
    async with async_timeout.timeout(5):
        async with session.get(url, ssl=ssl_context) as resp:
            if resp.status in (401, 403):
                raise AuthRequired("Authentication required")
            resp.raise_for_status()
            data = await resp.json()
            if not isinstance(data, dict):
                raise ValueError("Discovery did not return an object")
            return parse_discovery(data)


def parse_discovery(data: dict[str, Any]) -> DiscoveryInfo:
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, dict):
        raise ValueError("Discovery missing endpoints")
    v1 = endpoints.get("v1")
    if not isinstance(v1, dict):
        raise ValueError("Discovery missing endpoints.v1")

    # Avoid hardcoded paths; trust the server-provided endpoints.
    http_base = v1.get("signalk-http")
    ws_stream = v1.get("signalk-ws")
    if not isinstance(http_base, str) or not http_base:
        raise ValueError("Discovery missing endpoints.v1.signalk-http")
    if not isinstance(ws_stream, str) or not ws_stream:
        raise ValueError("Discovery missing endpoints.v1.signalk-ws")

    server = data.get("server") if isinstance(data.get("server"), dict) else {}
    server_id = server.get("id") if isinstance(server, dict) else None
    server_id = server_id if isinstance(server_id, str) and server_id.strip() else None
    server_version = server.get("version") if isinstance(server, dict) else None
    if not isinstance(server_version, str) or not server_version.strip():
        fallback_version = v1.get("version")
        server_version = (
            fallback_version if isinstance(fallback_version, str) and fallback_version else None
        )

    # Normalize endpoints to a stable form so comparisons and device info stay consistent.
    return DiscoveryInfo(
        base_url=_ensure_trailing_slash(http_base),
        ws_url=_ensure_subscribe_none(ws_stream),
        server_id=server_id,
        server_version=server_version,
    )


def discovery_origin_matches(info: DiscoveryInfo, host: str, port: int, use_ssl: bool) -> bool:
    """Return True if the discovered URLs use the same scheme/host/port the user gave.

    Both ``base_url`` and ``ws_url`` are checked independently, since SK
    discovery treats them as separate fields. A server can report a REST URL
    on the user-entered address but a WebSocket URL on a different (or
    unresolvable) host; in that case live updates would silently fail even
    though the REST setup looks fine, so the caller still needs the chance
    to surface the mismatch.
    """
    expected_http_scheme = "https" if use_ssl else "http"
    expected_ws_scheme = "wss" if use_ssl else "ws"
    return _url_origin_matches(
        info.base_url, expected_http_scheme, host, port
    ) and _url_origin_matches(info.ws_url, expected_ws_scheme, host, port)


def _url_origin_matches(url: str, expected_scheme: str, host: str, port: int) -> bool:
    parsed = urlsplit(url)
    parsed_host = (parsed.hostname or "").lower()
    if parsed.port is not None:
        parsed_port = parsed.port
    elif parsed.scheme in ("https", "wss"):
        parsed_port = 443
    else:
        parsed_port = 80
    return parsed.scheme == expected_scheme and parsed_host == host.lower() and parsed_port == port


def rewrite_discovery_origin(
    info: DiscoveryInfo, host: str, port: int, use_ssl: bool
) -> DiscoveryInfo:
    """Return a copy of ``info`` with the HTTP and WS URL origins replaced.

    Path and query are preserved, so reverse-proxied Signal K setups keep
    working. Use this only when the user has explicitly opted in (e.g. because
    the discovered hostname is unreachable from the Home Assistant runtime).
    """
    scheme = "https" if use_ssl else "http"
    return DiscoveryInfo(
        base_url=_rewrite_origin(info.base_url, scheme, host, port, ws=False),
        ws_url=_rewrite_origin(info.ws_url, scheme, host, port, ws=True),
        server_id=info.server_id,
        server_version=info.server_version,
    )


def _rewrite_origin(url: str, scheme: str, host: str, port: int | None, *, ws: bool) -> str:
    """Replace the scheme/host/port of url while preserving path and query.

    Example (ws=True, scheme="http", host="192.168.1.5", port=3000):
        in:  "ws://rpi.local:3000/signalk/v1/stream?subscribe=none"
        out: "ws://192.168.1.5:3000/signalk/v1/stream?subscribe=none"
    """
    parsed = urlsplit(url)
    if ws:
        new_scheme = "wss" if scheme == "https" else "ws"
    else:
        new_scheme = scheme
    netloc = f"{host}:{port}" if port else host
    return urlunsplit(parsed._replace(scheme=new_scheme, netloc=netloc))


def _ensure_trailing_slash(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or ""
    if not path.endswith("/"):
        path = f"{path}/"
    return urlunsplit(parsed._replace(path=path))


def _ensure_subscribe_none(url: str) -> str:
    parsed = urlsplit(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    # Default to subscribe=none so we always control the subscription payloads.
    if not query.get("subscribe"):
        query["subscribe"] = ["none"]
    new_query = urlencode(query, doseq=True)
    return urlunsplit(parsed._replace(query=new_query))


async def async_fetch_vessel_self(
    session: ClientSession, base_url: str, verify_ssl: bool, token: str | None = None
) -> dict[str, Any]:
    url = urlunsplit(urlsplit(base_url)._replace(path="/signalk/v1/api/vessels/self"))
    ssl_context = build_ssl_param(verify_ssl)
    headers = build_auth_headers(token)

    # Keep REST discovery snappy to avoid blocking HA startup on slow servers.
    async with async_timeout.timeout(5):
        async with session.get(url, ssl=ssl_context, headers=headers) as resp:
            if resp.status in (401, 403):
                raise AuthRequired("Authentication required")
            resp.raise_for_status()
            data = await resp.json()
            if not isinstance(data, dict):
                raise ValueError("vessels/self did not return an object")
            return data
