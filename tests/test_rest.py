import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.signalk_ha.auth import AuthRequired
from custom_components.signalk_ha.rest import (
    async_fetch_discovery,
    async_fetch_vessel_self,
    normalize_host_input,
    normalize_server_url,
    parse_discovery,
)


class _MockResponse:
    def __init__(self, status: int, payload: dict) -> None:
        self.status = status
        self._payload = payload

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"{self.status}")

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


async def test_async_fetch_vessel_self_success() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(200, {"name": "ONA"}))

    data = await async_fetch_vessel_self(
        session, "http://sk.local:3000/signalk/v1/api/", True, token=None
    )
    assert data["name"] == "ONA"


async def test_async_fetch_vessel_self_auth_required() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(401, {}))

    with pytest.raises(AuthRequired):
        await async_fetch_vessel_self(
            session, "http://sk.local:3000/signalk/v1/api/", True, token=None
        )


async def test_async_fetch_vessel_self_non_object() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(200, ["not", "dict"]))

    with pytest.raises(ValueError):
        await async_fetch_vessel_self(
            session, "http://sk.local:3000/signalk/v1/api/", True, token=None
        )


def test_normalize_host_input() -> None:
    host, port, scheme = normalize_host_input("https://Example.com:1234")
    assert host == "example.com"
    assert port == 1234
    assert scheme == "https"

    host, port, scheme = normalize_host_input("SK.LOCAL")
    assert host == "sk.local"
    assert port is None
    assert scheme is None


def test_parse_discovery_success() -> None:
    data = {
        "endpoints": {
            "v1": {
                "signalk-http": "http://sk.local:3000/signalk/v1/api/",
                "signalk-ws": "ws://sk.local:3000/signalk/v1/stream",
                "version": "2.0.0",
            }
        },
        "server": {"id": "signalk-server-node", "version": "2.1.0"},
    }
    info = parse_discovery(data)
    assert info.base_url.endswith("/signalk/v1/api/")
    assert info.ws_url.endswith("subscribe=none")
    assert info.server_id == "signalk-server-node"
    assert info.server_version == "2.1.0"


def test_parse_discovery_from_file() -> None:
    data = Path("tests/discovery_testdata.json").read_text(encoding="utf-8")
    info = parse_discovery(json.loads(data))
    assert info.base_url.endswith("/signalk/v1/api/")
    assert info.ws_url.startswith("wss://")
    assert info.ws_url.endswith("subscribe=none")
    assert info.server_id == "signalk-server-node"
    assert info.server_version == "2.19.0"


def test_parse_discovery_missing_endpoints_v1() -> None:
    with pytest.raises(ValueError):
        parse_discovery({"endpoints": {}})


def test_parse_discovery_fallback_version() -> None:
    data = {
        "endpoints": {
            "v1": {
                "signalk-http": "http://sk.local:3000/signalk/v1/api/",
                "signalk-ws": "ws://sk.local:3000/signalk/v1/stream",
                "version": "2.0.0",
            }
        },
        "server": {"id": "signalk-server-node"},
    }
    info = parse_discovery(data)
    assert info.server_version == "2.0.0"


async def test_async_fetch_discovery_success() -> None:
    payload = {
        "endpoints": {
            "v1": {
                "signalk-http": "http://sk.local:3000/signalk/v1/api/",
                "signalk-ws": "ws://sk.local:3000/signalk/v1/stream",
                "version": "2.0.0",
            }
        },
        "server": {"id": "signalk-server-node", "version": "2.1.0"},
    }
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(200, payload))

    server_url = normalize_server_url("sk.local", 3000, False)
    info = await async_fetch_discovery(session, server_url, True)
    assert info.server_id == "signalk-server-node"


async def test_async_fetch_discovery_http_error() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(500, {}))

    server_url = normalize_server_url("sk.local", 3000, False)
    with pytest.raises(RuntimeError):
        await async_fetch_discovery(session, server_url, True)


async def test_async_fetch_discovery_auth_required() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(401, {}))

    server_url = normalize_server_url("sk.local", 3000, False)
    with pytest.raises(AuthRequired):
        await async_fetch_discovery(session, server_url, True)


async def test_async_fetch_discovery_non_object() -> None:
    session = SimpleNamespace()
    session.get = Mock(return_value=_MockResponse(200, ["bad"]))

    server_url = normalize_server_url("sk.local", 3000, False)
    with pytest.raises(ValueError):
        await async_fetch_discovery(session, server_url, True)


def test_parse_discovery_missing_endpoints() -> None:
    with pytest.raises(ValueError):
        parse_discovery({"endpoints": []})


def test_parse_discovery_missing_http_or_ws() -> None:
    with pytest.raises(ValueError):
        parse_discovery({"endpoints": {"v1": {"signalk-ws": "ws://sk/ws"}}})
    with pytest.raises(ValueError):
        parse_discovery({"endpoints": {"v1": {"signalk-http": "http://sk/api"}}})


def test_parse_discovery_normalizes_ws_and_base_url() -> None:
    data = {
        "endpoints": {
            "v1": {
                "signalk-http": "http://sk.local:3000/signalk/v1/api",
                "signalk-ws": "wss://sk.local:3000/signalk/v1/stream?subscribe=all",
            }
        }
    }
    info = parse_discovery(data)
    assert info.base_url.endswith("/signalk/v1/api/")
    assert info.ws_url.endswith("subscribe=all")


def test_discovery_origin_matches_when_user_input_matches_server() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    info = DiscoveryInfo(
        base_url="http://sk.local:3000/signalk/v1/api/",
        ws_url="ws://sk.local:3000/signalk/v1/stream?subscribe=none",
        server_id="signalk-server-node",
        server_version="2.19.0",
    )
    assert discovery_origin_matches(info, "sk.local", 3000, False)
    assert discovery_origin_matches(info, "SK.LOCAL", 3000, False)


def test_discovery_origin_matches_returns_false_for_host_mismatch() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    info = DiscoveryInfo(
        base_url="http://rpi.local:3000/signalk/v1/api/",
        ws_url="ws://rpi.local:3000/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    # User entered an IP but the server still reports rpi.local.
    assert not discovery_origin_matches(info, "192.168.1.5", 3000, False)


def test_discovery_origin_matches_returns_false_when_ws_host_differs() -> None:
    # Pathological case: REST endpoint matches the user-entered address but the
    # SK server publishes its WS endpoint on a different host. Without checking
    # the WS URL the override step would be skipped and live updates would fail.
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    info = DiscoveryInfo(
        base_url="http://192.168.1.5:3000/signalk/v1/api/",
        ws_url="ws://rpi.local:3000/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    assert not discovery_origin_matches(info, "192.168.1.5", 3000, False)


def test_discovery_origin_matches_returns_false_when_ws_scheme_differs() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    # SK published an upgraded wss endpoint while REST stayed http.
    info = DiscoveryInfo(
        base_url="http://sk.local:3000/signalk/v1/api/",
        ws_url="wss://sk.local:3000/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    assert not discovery_origin_matches(info, "sk.local", 3000, False)


def test_discovery_origin_matches_returns_false_for_scheme_mismatch() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    info = DiscoveryInfo(
        base_url="https://sk.local:3000/signalk/v1/api/",
        ws_url="wss://sk.local:3000/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    assert not discovery_origin_matches(info, "sk.local", 3000, False)


def test_discovery_origin_matches_default_https_port() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        discovery_origin_matches,
    )

    # Server URL omits the explicit port; default should resolve to 443.
    info = DiscoveryInfo(
        base_url="https://sk.local/signalk/v1/api/",
        ws_url="wss://sk.local/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    assert discovery_origin_matches(info, "sk.local", 443, True)


def test_rewrite_discovery_origin_replaces_host_and_port() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        rewrite_discovery_origin,
    )

    info = DiscoveryInfo(
        base_url="http://rpi.local:3000/signalk/v1/api/",
        ws_url="ws://rpi.local:3000/signalk/v1/stream?subscribe=none",
        server_id="x",
        server_version="2.0",
    )
    rewritten = rewrite_discovery_origin(info, "192.168.1.5", 3000, False)
    assert rewritten.base_url == "http://192.168.1.5:3000/signalk/v1/api/"
    assert rewritten.ws_url.startswith("ws://192.168.1.5:3000/signalk/v1/stream")
    assert rewritten.server_id == "x"
    assert rewritten.server_version == "2.0"


def test_rewrite_discovery_origin_uses_wss_for_https() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        rewrite_discovery_origin,
    )

    info = DiscoveryInfo(
        base_url="http://rpi.local:3000/signalk/v1/api/",
        ws_url="ws://rpi.local:3000/signalk/v1/stream?subscribe=none",
        server_id=None,
        server_version=None,
    )
    rewritten = rewrite_discovery_origin(info, "10.0.0.5", 3443, True)
    assert rewritten.base_url.startswith("https://10.0.0.5:3443/")
    assert rewritten.ws_url.startswith("wss://10.0.0.5:3443/")


def test_rewrite_discovery_origin_preserves_path_and_query() -> None:
    from custom_components.signalk_ha.rest import (
        DiscoveryInfo,
        rewrite_discovery_origin,
    )

    info = DiscoveryInfo(
        base_url="http://sk.local/api/sk/",
        ws_url="ws://sk.local/api/sk/stream?subscribe=none&extra=1",
        server_id=None,
        server_version=None,
    )
    rewritten = rewrite_discovery_origin(info, "192.168.1.5", 8080, False)
    assert rewritten.base_url == "http://192.168.1.5:8080/api/sk/"
    assert rewritten.ws_url.startswith("ws://192.168.1.5:8080/api/sk/stream")
    assert "subscribe=none" in rewritten.ws_url
    assert "extra=1" in rewritten.ws_url
