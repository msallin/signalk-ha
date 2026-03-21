from types import SimpleNamespace

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalk_ha.auth import SignalKAuthManager
from custom_components.signalk_ha.const import (
    CONF_SERVER_ID,
    CONF_SERVER_VERSION,
    DOMAIN,
)
from custom_components.signalk_ha.diagnostics import (
    _redact_url,
    async_get_config_entry_diagnostics,
)
from custom_components.signalk_ha.runtime import SignalKRuntimeData


async def test_diagnostics_redacts_urls(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SERVER_ID: "signalk-server-node", CONF_SERVER_VERSION: "2.19.0"},
    )
    entry.add_to_hass(hass)

    cfg = SimpleNamespace(
        base_url="http://sk.local:3000/signalk/v1/api/",
        ws_url="ws://sk.local:3000/signalk/v1/stream?subscribe=none",
        vessel_id="mmsi:261006533",
        vessel_name="ONA",
    )
    coordinator = SimpleNamespace(
        config=cfg,
        connection_state="connected",
        last_error=None,
        counters={"messages": 0, "parse_errors": 0, "reconnects": 0},
        reconnect_count=0,
        last_message=None,
        last_update_by_path={},
        last_backoff=0.0,
        subscribed_paths=[],
        notification_count=0,
        last_notification=None,
    )
    discovery = SimpleNamespace(conflicts=[], last_refresh=None)
    auth = SignalKAuthManager("token123")
    auth.mark_success()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=discovery,
        auth=auth,
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["config"]["rest_url"] == "<redacted>"
    assert diagnostics["config"]["ws_url"] == "<redacted>"
    assert diagnostics["auth"]["token_present"] is True
    assert diagnostics["last_update_by_path"] == {}
    assert diagnostics["notifications"]["count"] == 0
    assert diagnostics["notifications"]["last"] is None
    assert diagnostics["config"]["server_id"] == "signalk-server-node"
    assert diagnostics["config"]["server_version"] == "2.19.0"


async def test_diagnostics_no_runtime_data(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SERVER_ID: "signalk-server-node", CONF_SERVER_VERSION: "2.19.0"},
    )
    entry.add_to_hass(hass)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["error"] == "no_runtime_data"


def test_redact_url_empty() -> None:
    assert _redact_url("") == ""


async def test_diagnostics_handles_none_timestamps(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SERVER_ID: "signalk-server-node", CONF_SERVER_VERSION: "2.19.0"},
    )
    entry.add_to_hass(hass)

    cfg = SimpleNamespace(
        base_url="http://sk.local:3000/signalk/v1/api/",
        ws_url="ws://sk.local:3000/signalk/v1/stream?subscribe=none",
        vessel_id="mmsi:261006533",
        vessel_name="ONA",
    )
    coordinator = SimpleNamespace(
        config=cfg,
        connection_state="connected",
        last_error=None,
        counters={"messages": 0, "parse_errors": 0, "reconnects": 0},
        reconnect_count=0,
        last_message=None,
        last_update_by_path={"navigation.speedOverGround": None},
        last_backoff=0.0,
        subscribed_paths=[],
        notification_count=0,
        last_notification=None,
    )
    discovery = SimpleNamespace(conflicts=[], last_refresh=None)
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=discovery,
        auth=SignalKAuthManager(None),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["last_update_by_path"]["navigation.speedOverGround"] is None


async def test_diagnostics_last_notification(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SERVER_ID: "signalk-server-node", CONF_SERVER_VERSION: "2.19.0"},
    )
    entry.add_to_hass(hass)

    cfg = SimpleNamespace(
        base_url="http://sk.local:3000/signalk/v1/api/",
        ws_url="ws://sk.local:3000/signalk/v1/stream?subscribe=none",
        vessel_id="mmsi:261006533",
        vessel_name="ONA",
    )
    coordinator = SimpleNamespace(
        config=cfg,
        connection_state="connected",
        last_error=None,
        counters={"messages": 0, "parse_errors": 0, "reconnects": 0},
        reconnect_count=0,
        last_message=None,
        last_update_by_path={},
        last_backoff=0.0,
        subscribed_paths=[],
        notification_count=2,
        last_notification={
            "path": "notifications.navigation.anchor",
            "state": "alert",
            "message": "Anchor Alarm",
            "received_at": dt_util.utcnow(),
        },
    )
    discovery = SimpleNamespace(conflicts=[], last_refresh=None)
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=discovery,
        auth=SignalKAuthManager(None),
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["notifications"]["count"] == 2
    assert diagnostics["notifications"]["last"]["path"] == "notifications.navigation.anchor"
    assert diagnostics["notifications"]["last"]["received_at"]
