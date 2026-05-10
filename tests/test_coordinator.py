import asyncio
import json
import time
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientError, WSMsgType, WSServerHandshakeError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.signalk_ha.coordinator as coordinator_module
from custom_components.signalk_ha.auth import AuthRequired, SignalKAuthManager
from custom_components.signalk_ha.const import (
    CONF_BASE_URL,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_HOST,
    CONF_PORT,
    CONF_SERVER_ID,
    CONF_SERVER_VERSION,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DOMAIN,
    notification_event_type,
)
from custom_components.signalk_ha.coordinator import (
    ConnectionState,
    SignalKCoordinator,
    SignalKDiscoveryCoordinator,
)
from custom_components.signalk_ha.discovery import DiscoveryResult
from custom_components.signalk_ha.identity import VesselIdentity
from custom_components.signalk_ha.rest import DiscoveryInfo


def _make_entry(*, options: dict[str, Any] | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "sk.local",
            CONF_PORT: 3000,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_BASE_URL: "http://sk.local:3000/signalk/v1/api/",
            CONF_WS_URL: "ws://sk.local:3000/signalk/v1/stream?subscribe=none",
            CONF_VESSEL_ID: "mmsi:261006533",
            CONF_VESSEL_NAME: "ONA",
        },
        options=options or {},
    )


def test_expected_contexts() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    contexts = coordinator._expected_contexts(coordinator.config)
    assert "vessels.self" in contexts
    assert "vessels.mmsi:261006533" in contexts
    assert "mmsi:261006533" in contexts


def test_expected_contexts_with_prefixed_vessel_id() -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "sk.local",
            CONF_PORT: 3000,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_BASE_URL: "http://sk.local:3000/signalk/v1/api/",
            CONF_WS_URL: "ws://sk.local:3000/signalk/v1/stream?subscribe=none",
            CONF_VESSEL_ID: "vessels.urn:boat:1",
            CONF_VESSEL_NAME: "ONA",
        },
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    contexts = coordinator._expected_contexts(coordinator.config)
    assert "vessels.urn:boat:1" in contexts
    assert "vessels.vessels.urn:boat:1" not in contexts


def test_expected_contexts_without_vessel_id() -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "sk.local",
            CONF_PORT: 3000,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_BASE_URL: "http://sk.local:3000/signalk/v1/api/",
            CONF_WS_URL: "ws://sk.local:3000/signalk/v1/stream?subscribe=none",
            CONF_VESSEL_ID: "",
            CONF_VESSEL_NAME: "ONA",
        },
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    assert coordinator._expected_contexts(coordinator.config) == ["vessels.self"]


def test_notification_properties() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    assert coordinator.notification_count == 0
    assert coordinator.last_notification is None
    assert coordinator.last_notification_timestamp is None
    assert coordinator.messages_per_hour is None
    assert coordinator.notifications_per_hour is None
    assert coordinator.message_count == 0

    coordinator._notification_count = 3
    coordinator._last_notification = {"received_at": "2026-01-03T00:00:00Z"}
    assert coordinator.notification_count == 3
    assert coordinator.last_notification == {"received_at": "2026-01-03T00:00:00Z"}
    assert coordinator.last_notification_timestamp == "2026-01-03T00:00:00Z"


def test_coordinator_property_accessors() -> None:
    entry = _make_entry()
    auth = SignalKAuthManager("token")
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), auth)
    coordinator._last_message = dt_util.utcnow()
    coordinator._stats.reconnects = 2
    coordinator._stats.parse_errors = 1
    coordinator._last_update_by_path = {"navigation.speedOverGround": dt_util.utcnow()}
    coordinator._last_source_by_path = {"navigation.speedOverGround": "src1"}
    coordinator._last_backoff = 3.5
    coordinator._paths = ["navigation.speedOverGround"]
    auth.mark_failure("boom")

    assert coordinator.last_message is not None
    assert coordinator.reconnect_count == 2
    assert coordinator.counters["parse_errors"] == 1
    assert coordinator.last_update_by_path
    assert coordinator.last_source_by_path
    assert coordinator.last_backoff == 3.5
    assert coordinator.subscribed_paths == ["navigation.speedOverGround"]
    assert coordinator.auth_state == "failed"
    assert coordinator.auth_last_error == "boom"


def test_rate_properties_compute_per_hour() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    coordinator._stats.messages = 10
    coordinator._first_message_at = dt_util.utcnow() - timedelta(hours=2)
    coordinator._notification_count = 4
    coordinator._first_notification_at = dt_util.utcnow() - timedelta(hours=1)

    assert coordinator.messages_per_hour == pytest.approx(5.0, rel=1e-2)
    assert coordinator.notifications_per_hour == pytest.approx(4.0, rel=1e-2)


def test_rate_properties_ignore_non_positive_elapsed() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    now = dt_util.utcnow()
    coordinator._stats.messages = 10
    coordinator._first_message_at = now + timedelta(seconds=5)
    coordinator._notification_count = 2
    coordinator._first_notification_at = now + timedelta(seconds=5)

    assert coordinator.messages_per_hour is None
    assert coordinator.notifications_per_hour is None


def test_rate_properties_are_rounded() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    coordinator._stats.messages = 1
    coordinator._first_message_at = dt_util.utcnow() - timedelta(seconds=3599)
    coordinator._notification_count = 1
    coordinator._first_notification_at = dt_util.utcnow() - timedelta(seconds=3599)

    messages_per_hour = coordinator.messages_per_hour
    notifications_per_hour = coordinator.notifications_per_hour

    assert messages_per_hour is not None
    assert notifications_per_hour is not None
    assert messages_per_hour == round(messages_per_hour, 2)
    assert notifications_per_hour == round(notifications_per_hour, 2)


async def test_run_inactivity_timeout_records_error(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    stop_event = asyncio.Event()

    class _FakeWS:
        def __init__(self):
            self.closed = False

        async def receive(self, timeout=None):
            raise asyncio.TimeoutError

        async def send_str(self, data):
            return None

        async def close(self):
            self.closed = True

        def exception(self):
            return None

    class _WSContext:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, exc_type, exc, tb):
            stop_event.set()
            return False

    ws = _FakeWS()
    session.ws_connect = Mock(return_value=_WSContext(ws))

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._paths = []
    coordinator._stop_event = stop_event

    await coordinator._run()

    assert coordinator.last_error == "Inactivity timeout"


def test_handle_message_updates_cache(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [
                {
                    "$source": "src1",
                    "values": [{"path": "navigation.speedOverGround", "value": 1.2}],
                }
            ],
        }
    )

    coordinator._handle_message(payload, coordinator.config)
    assert coordinator._data_cache["navigation.speedOverGround"] == 1.2
    assert coordinator.last_source_by_path["navigation.speedOverGround"] == "src1"
    if coordinator._flush_handle is not None:
        coordinator._flush_handle.cancel()
        coordinator._flush_handle = None


def test_handle_message_invalid_json(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._handle_message("invalid", coordinator.config)
    assert coordinator.counters["parse_errors"] == 1


def test_handle_message_fires_notification_event(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [
                {
                    "$source": "anchoralarm",
                    "timestamp": "2026-01-03T22:34:57.853Z",
                    "values": [
                        {
                            "path": "notifications.navigation.anchor",
                            "value": {
                                "state": "alert",
                                "method": ["sound"],
                                "message": "Anchor Alarm",
                            },
                        }
                    ],
                }
            ],
        }
    )

    coordinator._handle_message(payload, coordinator.config)
    coordinator._handle_message(payload, coordinator.config)

    assert len(events) == 1
    data = events[0].data
    assert data["path"] == "notifications.navigation.anchor"
    assert data["state"] == "alert"
    assert data["message"] == "Anchor Alarm"
    assert data["method"] == ["sound"]
    assert data["timestamp"] == "2026-01-03T22:34:57.853Z"
    assert data["source"] == "anchoralarm"
    assert data["vessel_id"] == entry.data[CONF_VESSEL_ID]
    assert data["vessel_name"] == entry.data[CONF_VESSEL_NAME]
    assert data["entry_id"] == entry.entry_id
    assert "notifications.navigation.anchor" not in coordinator._data_cache


def test_handle_message_notifications_disabled_no_event(hass) -> None:
    entry = _make_entry(options={CONF_ENABLE_NOTIFICATIONS: False})
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [
                {
                    "$source": "anchoralarm",
                    "values": [
                        {
                            "path": "notifications.navigation.anchor",
                            "value": {"state": "alert"},
                        }
                    ],
                }
            ],
        }
    )

    coordinator._handle_message(payload, coordinator.config)

    assert events == []
    assert "notifications.navigation.anchor" not in coordinator._data_cache


def test_fire_notification_skips_invalid_path(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    coordinator._fire_notification(
        {"path": "navigation.speed", "value": {"state": "alert"}}, coordinator.config
    )

    assert events == []


def test_fire_notification_dedupes_without_timestamp(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    value = {"state": "alert"}
    notification = {
        "path": "notifications.navigation.anchor",
        "value": value,
        "source": "anchoralarm",
    }
    message = "notifications.navigation.anchor (alert)"
    signature = coordinator._notification_signature(value, "alert", message, None, "anchoralarm")
    coordinator._notification_cache[notification["path"]] = (signature, None, time.monotonic())
    coordinator._fire_notification(notification, coordinator.config)

    assert events == []


def test_fire_notification_dedupes_with_timestamp(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {"state": "alert"},
        "timestamp": "2026-01-03T22:34:57.853Z",
        "source": "anchoralarm",
    }

    coordinator._fire_notification(notification, coordinator.config)
    coordinator._fire_notification(notification, coordinator.config)

    assert len(events) == 1


async def test_fire_notification_defaults_message(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {"state": "alert"},
    }

    coordinator._fire_notification(notification, coordinator.config)
    await hass.async_block_till_done()

    assert events
    assert events[0].data["message"] == "notifications.navigation.anchor (alert)"


async def test_fire_notification_defaults_message_to_path(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {},
    }

    coordinator._fire_notification(notification, coordinator.config)
    await hass.async_block_till_done()

    assert events
    assert events[0].data["message"] == "notifications.navigation.anchor"


async def test_fire_notification_non_dict_value(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    events: list = []
    hass.bus.async_listen(
        notification_event_type(entry.data[CONF_VESSEL_NAME]),
        lambda event: events.append(event),
    )

    notification = {
        "path": "notifications.navigation.anchor",
        "value": "alert",
    }

    coordinator._fire_notification(notification, coordinator.config)
    await hass.async_block_till_done()

    assert events
    assert events[0].data["message"] == "notifications.navigation.anchor"


def test_notification_signature_handles_bad_keys() -> None:
    value = {("bad",): "data"}
    signature = SignalKCoordinator._notification_signature(value, None, None, None, None)
    assert signature[-1] == repr(value)


def test_notification_signature_scalar_value() -> None:
    signature = SignalKCoordinator._notification_signature(42, None, None, None, None)
    assert signature[-1] == repr(42)


async def test_send_subscribe_payload(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._paths = ["navigation.speedOverGround"]
    coordinator._periods = {"navigation.speedOverGround": 1000}

    ws = SimpleNamespace(send_str=AsyncMock())
    await coordinator._send_subscribe(ws)

    ws.send_str.assert_called_once()
    payload = json.loads(ws.send_str.call_args.args[0])
    assert payload["subscribe"][0]["path"] == "navigation.speedOverGround"
    assert payload["subscribe"][0]["period"] == 1000
    assert payload["subscribe"][0]["minPeriod"] == 1000


def test_build_ssl_param() -> None:
    data = dict(_make_entry().data)
    data[CONF_SSL] = True
    data[CONF_VERIFY_SSL] = False
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    assert coordinator._build_ssl_param(coordinator.config) is False

    data = dict(entry.data)
    data[CONF_VERIFY_SSL] = True
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    assert coordinator._build_ssl_param(coordinator.config) is None

    data = dict(entry.data)
    data[CONF_SSL] = False
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    assert coordinator._build_ssl_param(coordinator.config) is None


async def test_async_update_paths_triggers_resubscribe(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED
    coordinator._ws = SimpleNamespace(closed=False)

    with patch.object(coordinator, "_send_subscribe", new=AsyncMock()) as send:
        await coordinator.async_update_paths(
            ["navigation.speedOverGround"], {"navigation.speedOverGround": 500}
        )
        send.assert_called_once()


def test_auth_failure_triggers_reauth(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))

    async def _reauth(_hass):
        return None

    entry.async_start_reauth = AsyncMock(side_effect=_reauth)

    def _close_task(coro):
        coro.close()

    hass.async_create_task = _close_task

    coordinator._handle_auth_failure("auth failed")

    assert coordinator.auth_state == "access_request_pending"
    entry.async_start_reauth.assert_called_once()


def test_log_rate_limited_logs_once(monkeypatch) -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    logger = Mock()
    monkeypatch.setattr("custom_components.signalk_ha.coordinator._LOGGER", logger)
    coordinator._log_times["k1"] = time.monotonic() - 100.0

    coordinator._log_rate_limited(30, "message", key="k1")
    coordinator._log_rate_limited(30, "message", key="k1")

    logger.log.assert_called_once()


def test_set_state_transitions_log(hass, monkeypatch) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator.async_set_updated_data = Mock()
    logger = Mock()
    monkeypatch.setattr("custom_components.signalk_ha.coordinator._LOGGER", logger)

    coordinator._set_state(ConnectionState.CONNECTED)
    coordinator._set_state(ConnectionState.RECONNECTING)

    logger.info.assert_called()
    logger.warning.assert_called()


def test_schedule_flush_sets_handle(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator.async_set_updated_data = Mock()
    coordinator._data_cache = {"navigation.speedOverGround": 1.0}

    coordinator._schedule_flush()
    assert coordinator._flush_handle is not None
    handle = coordinator._flush_handle

    coordinator._schedule_flush()
    assert coordinator._flush_handle is handle

    coordinator._flush_handle.cancel()
    coordinator._flush_handle = None


def test_schedule_flush_immediate_resets_handle(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator.async_set_updated_data = Mock()
    coordinator._data_cache = {"navigation.speedOverGround": 1.0}
    coordinator._flush_handle = hass.loop.call_later(60, lambda: None)

    coordinator._schedule_flush(immediate=True)

    assert coordinator._flush_handle is None
    coordinator.async_set_updated_data.assert_called_once()


def test_flush_updates_resets_handle(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator.async_set_updated_data = Mock()
    coordinator._data_cache = {"navigation.speedOverGround": 1.0}
    coordinator._flush_handle = object()

    coordinator._flush_updates()
    assert coordinator._flush_handle is None
    coordinator.async_set_updated_data.assert_called_once()


def test_handle_message_sources_only_schedules_flush(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))

    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [{"$source": "src1", "values": [{"path": "navigation.speedOverGround"}]}],
        }
    )

    coordinator._schedule_flush = Mock()
    coordinator._handle_message(payload, coordinator.config)

    assert coordinator._data_cache == {}
    assert coordinator.last_source_by_path["navigation.speedOverGround"] == "src1"
    coordinator._schedule_flush.assert_called_once()


def test_handle_message_source_unchanged_no_flush(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._last_source_by_path["navigation.speedOverGround"] = "src1"

    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [{"$source": "src1", "values": [{"path": "navigation.speedOverGround"}]}],
        }
    )

    coordinator._schedule_flush = Mock()
    coordinator._handle_message(payload, coordinator.config)

    assert coordinator._data_cache == {}
    coordinator._schedule_flush.assert_not_called()


def test_start_reauth_noop_when_started(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator._reauth_started = True
    coordinator._entry.async_start_reauth = AsyncMock()
    coordinator._start_reauth()
    coordinator._entry.async_start_reauth.assert_not_called()


def test_schedule_stale_checks_is_idempotent(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator._schedule_stale_checks()
    handle = coordinator._stale_unsub
    coordinator._schedule_stale_checks()
    assert coordinator._stale_unsub is handle
    if handle:
        handle.cancel()
        coordinator._stale_unsub = None


def test_stale_tick_reschedules(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator._schedule_flush = Mock()
    coordinator._schedule_stale_checks = Mock()
    coordinator._stale_tick()
    coordinator._schedule_flush.assert_called_once_with(immediate=True)
    coordinator._schedule_stale_checks.assert_called_once()


def test_stale_tick_does_not_reschedule_when_stopping(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator._stop_event.set()
    coordinator._schedule_flush = Mock()
    coordinator._schedule_stale_checks = Mock()

    coordinator._stale_tick()

    coordinator._schedule_flush.assert_called_once_with(immediate=True)
    coordinator._schedule_stale_checks.assert_not_called()


async def test_run_processes_messages_and_disconnects(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    stop_event = asyncio.Event()
    payload = json.dumps(
        {
            "context": "vessels.self",
            "updates": [{"values": [{"path": "navigation.speedOverGround", "value": 1.2}]}],
        }
    )

    class _FakeWS:
        def __init__(self):
            self.closed = False
            self.sent = None
            self._messages = [
                SimpleNamespace(type=WSMsgType.TEXT, data=payload),
                SimpleNamespace(type=WSMsgType.CLOSED),
            ]

        async def receive(self, timeout=None):
            return self._messages.pop(0)

        async def send_str(self, data):
            self.sent = data

        async def close(self):
            self.closed = True

        def exception(self):
            return None

    class _WSContext:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, exc_type, exc, tb):
            stop_event.set()
            return False

    ws = _FakeWS()
    session.ws_connect = Mock(return_value=_WSContext(ws))

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._paths = ["navigation.speedOverGround"]
    coordinator._periods = {"navigation.speedOverGround": 1000}
    coordinator._stop_event = stop_event

    await coordinator._run()

    assert coordinator.counters["messages"] == 1
    assert coordinator.connection_state == "disconnected"
    assert ws.sent is not None
    if coordinator._flush_handle is not None:
        coordinator._flush_handle.cancel()
        coordinator._flush_handle = None


async def test_run_exits_when_stop_event_set(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._stop_event.set()

    await coordinator._run()

    assert coordinator.connection_state == "disconnected"


async def test_run_handles_ws_auth_failure(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    session.ws_connect = Mock(
        side_effect=WSServerHandshakeError(None, tuple(), status=401, message="unauthorized")
    )

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    with patch.object(coordinator, "_handle_auth_failure") as auth_failure:
        await coordinator._run()

    auth_failure.assert_called_once()


async def test_run_handles_ws_error_message(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    stop_event = asyncio.Event()

    class _FakeWS:
        def __init__(self):
            self.closed = False
            self._messages = [
                SimpleNamespace(type=WSMsgType.ERROR),
            ]

        async def receive(self, timeout=None):
            return self._messages.pop(0)

        async def send_str(self, data):
            return None

        async def close(self):
            self.closed = True

        def exception(self):
            return RuntimeError("boom")

    class _WSContext:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, exc_type, exc, tb):
            stop_event.set()
            return False

    ws = _FakeWS()
    session.ws_connect = Mock(return_value=_WSContext(ws))

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._paths = []
    coordinator._stop_event = stop_event

    await coordinator._run()
    assert coordinator.last_error is not None


async def test_run_handles_ws_error_message_without_exception(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    stop_event = asyncio.Event()

    class _FakeWS:
        def __init__(self):
            self.closed = False
            self._messages = [SimpleNamespace(type=WSMsgType.ERROR)]

        async def receive(self, timeout=None):
            return self._messages.pop(0)

        async def send_str(self, data):
            return None

        async def close(self):
            self.closed = True

        def exception(self):
            return None

    class _WSContext:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, exc_type, exc, tb):
            stop_event.set()
            return False

    ws = _FakeWS()
    session.ws_connect = Mock(return_value=_WSContext(ws))

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._paths = []
    coordinator._stop_event = stop_event

    await coordinator._run()
    assert coordinator.last_error is None or "websocket" in coordinator.last_error.lower()


async def test_run_handles_cancelled_error(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    session.ws_connect = Mock(side_effect=asyncio.CancelledError)
    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))

    await coordinator._run()

    assert coordinator._ws is None


async def test_run_disconnect_warning_when_reconnecting(hass, monkeypatch) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    stop_event = asyncio.Event()

    class _FakeWS:
        def __init__(self):
            self.closed = False
            self._messages = [SimpleNamespace(type=WSMsgType.ERROR)]

        async def receive(self, timeout=None):
            return self._messages.pop(0)

        async def send_str(self, data):
            return None

        async def close(self):
            self.closed = True

        def exception(self):
            return None

    class _WSContext:
        def __init__(self, ws):
            self._ws = ws

        async def __aenter__(self):
            return self._ws

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def _sleep(delay: float) -> None:
        stop_event.set()

    monkeypatch.setattr(coordinator_module.random, "uniform", lambda *_: 0.0)
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", _sleep)

    ws = _FakeWS()
    session.ws_connect = Mock(return_value=_WSContext(ws))

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._paths = []
    coordinator._stop_event = stop_event

    await coordinator._run()
    assert coordinator.reconnect_count == 1


async def test_run_handles_unexpected_exception(hass, monkeypatch) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    session.ws_connect = Mock(side_effect=ValueError("boom"))
    stop_event = asyncio.Event()

    async def _sleep(delay: float) -> None:
        stop_event.set()

    monkeypatch.setattr(coordinator_module.random, "uniform", lambda *_: 0.0)
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", _sleep)

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._stop_event = stop_event

    await coordinator._run()
    assert coordinator.last_error is not None


async def test_run_reconnects_with_backoff(hass, monkeypatch) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    session.ws_connect = Mock(side_effect=OSError("boom"))
    stop_event = asyncio.Event()

    async def _sleep(delay: float) -> None:
        stop_event.set()

    monkeypatch.setattr(coordinator_module.random, "uniform", lambda *_: 0.0)
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", _sleep)

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._stop_event = stop_event

    await coordinator._run()

    assert coordinator.reconnect_count == 1
    assert coordinator.last_backoff == pytest.approx(coordinator_module._BACKOFF_MIN)
    assert coordinator.connection_state == "disconnected"


async def test_run_backoff_increases_on_retries(hass, monkeypatch) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    session.ws_connect = Mock(side_effect=[OSError("boom1"), OSError("boom2")])
    stop_event = asyncio.Event()
    sleep_calls = 0

    async def _sleep(delay: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 2:
            stop_event.set()

    monkeypatch.setattr(coordinator_module.random, "uniform", lambda *_: 0.0)
    monkeypatch.setattr(coordinator_module.asyncio, "sleep", _sleep)

    coordinator = SignalKCoordinator(hass, entry, session, Mock(), SignalKAuthManager(None))
    coordinator._stop_event = stop_event

    await coordinator._run()

    assert coordinator.reconnect_count == 2
    assert coordinator.last_backoff == pytest.approx(coordinator_module._BACKOFF_MIN * 2)


def test_start_reauth_skips_when_stopping(hass) -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._stop_event.set()
    entry.async_start_reauth = Mock()

    coordinator._start_reauth()

    entry.async_start_reauth.assert_not_called()


def test_start_reauth_ignores_none(hass) -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    entry.async_start_reauth = Mock(return_value=None)

    coordinator._start_reauth()

    entry.async_start_reauth.assert_called_once()


async def test_discovery_coordinator_updates_identity(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Old Vessel",
        model="old-server",
        sw_version="1.0",
        configuration_url="http://sk.local:3000",
    )
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)
    vessel = {"name": "New Name", "mmsi": "261006533"}
    discovery_info = DiscoveryInfo(
        base_url="https://sk.local:3443/signalk/v1/api/",
        ws_url="wss://sk.local:3443/signalk/v1/stream?subscribe=none",
        server_id="signalk-server-node",
        server_version="2.20.0",
    )

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(return_value=discovery_info),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(return_value=vessel),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.discover_entities",
            return_value=DiscoveryResult(entities=[], conflicts=[]),
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        result = await discovery._async_update_data()

    assert result.entities == []
    update_entry.assert_called_once()
    updated = update_entry.call_args.kwargs["data"]
    assert updated[CONF_VESSEL_NAME] == "New Name"
    assert updated[CONF_BASE_URL] == discovery_info.base_url
    assert updated[CONF_WS_URL] == discovery_info.ws_url
    assert updated[CONF_SERVER_ID] == discovery_info.server_id
    assert updated[CONF_SERVER_VERSION] == discovery_info.server_version
    device = registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    assert device.name == "New Name"
    assert device.model == "signalk-server-node"
    assert device.sw_version == "2.20.0"
    assert device.configuration_url == discovery_info.base_url
    assert discovery.last_refresh is not None


async def test_discovery_coordinator_applies_override_flag_on_refresh(hass) -> None:
    from custom_components.signalk_ha.const import (
        CONF_ENTITY_ID_PREFIX,
        CONF_OVERRIDE_DISCOVERED_HOST,
    )

    # User chose to override during setup; subsequent refreshes must keep using
    # the entered host even when the SK server still reports its own.
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "192.168.1.5",
            CONF_PORT: 3000,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_BASE_URL: "http://192.168.1.5:3000/signalk/v1/api/",
            CONF_WS_URL: "ws://192.168.1.5:3000/signalk/v1/stream?subscribe=none",
            CONF_VESSEL_ID: "mmsi:261006533",
            CONF_VESSEL_NAME: "ONA",
            CONF_ENTITY_ID_PREFIX: "",
            CONF_OVERRIDE_DISCOVERED_HOST: True,
        },
    )
    entry.add_to_hass(hass)
    discovery = SignalKDiscoveryCoordinator(hass, entry, Mock(), SignalKAuthManager(None))
    server_reported = DiscoveryInfo(
        base_url="http://rpi.local:3000/signalk/v1/api/",
        ws_url="ws://rpi.local:3000/signalk/v1/stream?subscribe=none",
        server_id="signalk-server-node",
        server_version="2.20.0",
    )

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(return_value=server_reported),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(return_value={"name": "ONA", "mmsi": "261006533"}),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.discover_entities",
            return_value=DiscoveryResult(entities=[], conflicts=[]),
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        await discovery._async_update_data()

    # The stored URLs should still point at 192.168.1.5, not rpi.local.
    if update_entry.called:
        updated = update_entry.call_args.kwargs["data"]
        assert updated.get(CONF_BASE_URL, "").startswith("http://192.168.1.5:3000/")
        assert updated.get(CONF_WS_URL, "").startswith("ws://192.168.1.5:3000/")


async def test_discovery_coordinator_no_entry_updates_when_unchanged(hass) -> None:
    base = _make_entry().data
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **base,
            CONF_SERVER_ID: "signalk-server-node",
            CONF_SERVER_VERSION: "2.20.0",
        },
    )
    entry.add_to_hass(hass)
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)
    vessel = {"name": "ONA", "mmsi": "261006533"}
    discovery_info = DiscoveryInfo(
        base_url=entry.data[CONF_BASE_URL],
        ws_url=entry.data[CONF_WS_URL],
        server_id=entry.data[CONF_SERVER_ID],
        server_version=entry.data[CONF_SERVER_VERSION],
    )

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(return_value=discovery_info),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(return_value=vessel),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.discover_entities",
            return_value=DiscoveryResult(entities=[], conflicts=[]),
        ),
        patch.object(hass.config_entries, "async_update_entry") as update_entry,
    ):
        await discovery._async_update_data()

    update_entry.assert_not_called()


async def test_discovery_coordinator_no_device_updates(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data[CONF_VESSEL_NAME],
        model="signalk-server-node",
        sw_version="2.20.0",
        configuration_url=entry.data[CONF_BASE_URL],
    )
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)

    with patch.object(registry, "async_update_device") as update_device:
        discovery._async_update_device_registry(
            vessel_name=device.name,
            server_id=device.model,
            server_version=device.sw_version,
            configuration_url=device.configuration_url,
        )

    update_device.assert_not_called()


async def test_discovery_coordinator_discovery_failure(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)
    vessel = {"name": "ONA", "mmsi": "261006533"}

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(side_effect=ClientError("boom")),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(return_value=vessel),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.discover_entities",
            return_value=DiscoveryResult(entities=[], conflicts=[]),
        ),
    ):
        result = await discovery._async_update_data()

    assert result.entities == []
    assert discovery.last_refresh is not None


def test_discovery_coordinator_updates_device_registry_fields(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Old Vessel",
        model="old-server",
        sw_version="1.0",
        configuration_url="http://old",
    )

    discovery = SignalKDiscoveryCoordinator(hass, entry, Mock(), SignalKAuthManager(None))
    discovery._async_update_device_registry(
        vessel_name="New Vessel",
        server_id="signalk-server-node",
        server_version="2.20.0",
        configuration_url="http://new",
    )

    device = registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device is not None
    assert device.name == "New Vessel"
    assert device.model == "signalk-server-node"
    assert device.sw_version == "2.20.0"
    assert device.configuration_url == "http://new"


async def test_discovery_coordinator_async_stop_calls_shutdown(hass) -> None:
    entry = _make_entry()
    discovery = SignalKDiscoveryCoordinator(hass, entry, Mock(), SignalKAuthManager(None))

    with patch.object(discovery, "async_shutdown", new=AsyncMock()) as shutdown:
        await discovery.async_stop()

    shutdown.assert_awaited_once()


async def test_discovery_coordinator_warns_on_identity_change(hass, monkeypatch) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)
    logger = Mock()
    monkeypatch.setattr("custom_components.signalk_ha.coordinator._LOGGER", logger)

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(return_value={"name": "ONA"}),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.resolve_vessel_identity",
            return_value=VesselIdentity(vessel_id="mmsi:123", vessel_name="ONA"),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.discover_entities",
            return_value=DiscoveryResult(entities=[], conflicts=[]),
        ),
    ):
        await discovery._async_update_data()

    logger.warning.assert_called_once()
    assert discovery.conflicts == []


async def test_discovery_coordinator_auth_required(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    session = Mock()
    auth = SignalKAuthManager(None)
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)

    with (
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_discovery",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "custom_components.signalk_ha.coordinator.async_fetch_vessel_self",
            new=AsyncMock(side_effect=AuthRequired("auth")),
        ),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await discovery._async_update_data()


def test_discovery_coordinator_config_defaults(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "sk.local",
            CONF_PORT: 3000,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_VESSEL_ID: "mmsi:261006533",
            CONF_VESSEL_NAME: "ONA",
        },
    )
    discovery = SignalKDiscoveryCoordinator(hass, entry, Mock(), SignalKAuthManager(None))
    cfg = discovery._config()
    assert cfg.base_url.endswith("/signalk/v1/api/")
    assert cfg.ws_url.endswith("/signalk/v1/stream?subscribe=none")


def test_coordinator_auth_properties(hass) -> None:
    entry = _make_entry()
    auth = SignalKAuthManager("token")
    auth.mark_success()
    auth.mark_access_request_active()

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), auth)
    assert coordinator.auth_last_success is not None
    assert coordinator.auth_access_request_active is True
    assert coordinator.auth_token_present is True


def test_notification_listener_remove(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    listener = Mock()
    remove = coordinator.async_add_notification_listener(listener)
    assert listener in coordinator._notification_listeners
    remove()
    remove()
    assert listener not in coordinator._notification_listeners


@pytest.mark.real_ws_start
async def test_coordinator_async_start_creates_background_task(hass, monkeypatch) -> None:
    entry = _make_entry()
    mock_hass = SimpleNamespace(
        loop=hass.loop,
        async_create_background_task=Mock(),
        async_create_task=Mock(),
    )
    coordinator = SignalKCoordinator(mock_hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    created: list[asyncio.Task] = []

    async def _noop_run() -> None:
        return None

    def _create_task(coro, name=None):
        task = hass.async_create_task(coro)
        created.append(task)
        return task

    mock_hass.async_create_background_task = Mock(side_effect=_create_task)
    coordinator._run = _noop_run

    await coordinator.async_start()
    assert created
    assert coordinator._task is created[0]
    mock_hass.async_create_background_task.assert_called_once()
    await coordinator.async_stop()


@pytest.mark.real_ws_start
async def test_coordinator_async_start_fallback_task(hass, monkeypatch) -> None:
    entry = _make_entry()
    mock_hass = SimpleNamespace(
        loop=hass.loop,
        async_create_task=Mock(),
    )
    coordinator = SignalKCoordinator(mock_hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    created: list[asyncio.Task] = []

    async def _noop_run() -> None:
        return None

    def _create_task(coro):
        task = hass.async_create_task(coro)
        created.append(task)
        return task

    mock_hass.async_create_task = Mock(side_effect=_create_task)
    coordinator._run = _noop_run

    await coordinator.async_start()
    assert created
    assert coordinator._task is created[0]
    mock_hass.async_create_task.assert_called_once()
    await coordinator.async_stop()


@pytest.mark.real_ws_start
async def test_coordinator_async_start_noop_when_running(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    existing_task = AsyncMock()
    coordinator._task = existing_task

    await coordinator.async_start()
    assert coordinator._task is existing_task


async def test_coordinator_async_stop_cleans_resources(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    ws = SimpleNamespace(closed=False, close=AsyncMock())
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._ws = ws
    coordinator._flush_handle = hass.loop.call_later(60, lambda: None)
    coordinator._stale_unsub = hass.loop.call_later(60, lambda: None)
    coordinator._task = asyncio.create_task(asyncio.sleep(0))

    await coordinator.async_stop()

    ws.close.assert_awaited_once()
    assert coordinator._task is None
    assert coordinator.connection_state == "disconnected"


async def test_coordinator_async_stop_without_resources(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))

    await coordinator.async_stop()

    assert coordinator._task is None
    assert coordinator._ws is None


async def test_async_update_paths_no_change(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._paths = ["navigation.speedOverGround"]
    coordinator._periods = {"navigation.speedOverGround": 1000}
    coordinator._ws = SimpleNamespace(closed=False)
    coordinator._state = ConnectionState.CONNECTED

    with patch.object(coordinator, "_send_subscribe", new=AsyncMock()) as send:
        await coordinator.async_update_paths(
            ["navigation.speedOverGround"], {"navigation.speedOverGround": 1000}
        )
        send.assert_not_called()


def test_record_error_truncates_message(hass) -> None:
    coordinator = SignalKCoordinator(hass, _make_entry(), Mock(), Mock(), SignalKAuthManager(None))
    coordinator.async_set_updated_data = Mock()
    coordinator._record_error("x" * 500)
    assert coordinator.last_error == "x" * 200
