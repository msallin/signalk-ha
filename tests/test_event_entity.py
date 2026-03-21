from unittest.mock import Mock

from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalk_ha.auth import SignalKAuthManager
from custom_components.signalk_ha.const import (
    CONF_BASE_URL,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_ENTITY_ID_PREFIX,
    CONF_HOST,
    CONF_NOTIFICATION_PATHS,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DOMAIN,
)
from custom_components.signalk_ha.coordinator import ConnectionState, SignalKCoordinator
from custom_components.signalk_ha.event import (
    SignalKNotificationEvent,
    _humanize_segment,
    _is_ignored_path,
    _notification_attributes,
    _notification_event_type,
    _notification_name,
    _SignalKNotificationListener,
    async_setup_entry,
)
from custom_components.signalk_ha.runtime import SignalKRuntimeData


def _make_entry(options=None) -> MockConfigEntry:
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


def test_notification_event_type_normalizes() -> None:
    assert _notification_event_type("ALERT") == "alert"
    assert _notification_event_type(None) == "unknown"
    assert _notification_event_type("not-a-level") == "unknown"


def test_notification_name_humanizes() -> None:
    assert _humanize_segment("speedOverGround") == "Speed Over Ground"
    assert _humanize_segment("") == ""
    assert _notification_name("notifications.navigation.anchor") == "Navigation Anchor Notification"
    assert _notification_name("notifications") == "Notification"
    assert _notification_name("custom.path") == "Custom Path Notification"
    assert (
        _is_ignored_path("notifications.security.accessRequest.any", ["notifications.security."])
        is True
    )
    assert _is_ignored_path("notifications.navigation.anchor", ["notifications.security."]) is False


def test_notification_attributes_formats_received_at() -> None:
    received_at = dt_util.utcnow()
    attrs = _notification_attributes(
        {
            "path": "notifications.navigation.anchor",
            "state": "alert",
            "message": "Anchor Alarm",
            "received_at": received_at,
        }
    )
    assert attrs["path"] == "notifications.navigation.anchor"
    assert attrs["received_at"] == dt_util.as_utc(received_at).isoformat()


def test_notification_attributes_without_received_at() -> None:
    attrs = _notification_attributes(
        {
            "path": "notifications.navigation.anchor",
            "state": "alert",
            "message": "Anchor Alarm",
        }
    )
    assert "received_at" not in attrs


async def test_event_setup_skips_without_runtime(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)
    entry.runtime_data = None

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    assert added == []


async def test_event_entity_updates_on_notification(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added = []
    await async_setup_entry(hass, entry, added.extend)

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {"state": "alert", "method": ["visual"], "message": "Anchor Alarm"},
        "source": "anchoralarm",
        "timestamp": "2026-01-03T22:34:57.853Z",
    }

    coordinator._fire_notification(notification, coordinator.config)

    assert len(added) == 1
    entity = added[0]
    assert entity.state is not None
    attrs = entity.state_attributes
    assert attrs["event_type"] == "alert"
    assert attrs["path"] == "notifications.navigation.anchor"
    assert attrs["message"] == "Anchor Alarm"
    assert attrs["source"] == "anchoralarm"
    assert attrs["timestamp"] == "2026-01-03T22:34:57.853Z"
    assert attrs["received_at"]


async def test_event_entity_available_respects_notifications_toggle(hass) -> None:
    entry = _make_entry(options={CONF_ENABLE_NOTIFICATIONS: False})
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")
    assert entity.available is False


async def test_event_entity_suggested_object_id_uses_configured_prefix(hass) -> None:
    entry = MockConfigEntry(
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
            CONF_ENTITY_ID_PREFIX: "signalk_",
        },
    )
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")

    assert entity.suggested_object_id == "signalk_notifications_navigation_anchor"


async def test_event_entity_suggested_object_id_uses_default_when_prefix_empty(hass) -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")

    assert entity.suggested_object_id == "Navigation Anchor Notification"


async def test_event_setup_skips_when_notifications_disabled(hass) -> None:
    entry = _make_entry(
        options={
            CONF_ENABLE_NOTIFICATIONS: False,
            CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"],
        }
    )
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    coordinator._fire_notification(
        {"path": "notifications.navigation.anchor", "value": {"state": "alert"}},
        coordinator.config,
    )

    assert added == []


async def test_event_setup_skips_disabled_specific_path(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    registry = er.async_get(hass)
    unique_id = f"signalk:{entry.entry_id}:notifications.navigation.anchor"
    entity_id = registry.async_get_or_create(
        "event",
        DOMAIN,
        unique_id,
        suggested_object_id="anchor",
        config_entry=entry,
    ).entity_id
    registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    assert added == []


async def test_event_setup_keeps_enabled_registry_entity(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    registry = er.async_get(hass)
    unique_id = f"signalk:{entry.entry_id}:notifications.navigation.anchor"
    registry.async_get_or_create(
        "event",
        DOMAIN,
        unique_id,
        suggested_object_id="anchor",
        config_entry=entry,
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    assert len(added) == 1


async def test_event_setup_skips_when_registry_disabled(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    registry = er.async_get(hass)
    unique_id = f"signalk:{entry.entry_id}:notifications.navigation.anchor"
    entity_id = registry.async_get_or_create(
        "event",
        DOMAIN,
        unique_id,
        suggested_object_id="anchor",
        config_entry=entry,
    ).entity_id
    registry.async_update_entity(entity_id, disabled_by=er.RegistryEntryDisabler.USER)

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    assert added == []


async def test_event_setup_skips_without_paths(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: []})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    coordinator._fire_notification(
        {"path": "notifications.navigation.anchor", "value": {"state": "alert"}},
        coordinator.config,
    )

    assert added == []


async def test_event_setup_ignores_security_paths(hass) -> None:
    entry = _make_entry(
        options={CONF_NOTIFICATION_PATHS: ["notifications.security.accessRequest.any"]}
    )
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    coordinator._fire_notification(
        {"path": "notifications.security.accessRequest.any", "value": {"state": "alert"}},
        coordinator.config,
    )

    assert added == []


async def test_event_entity_handles_mismatched_path(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")
    entity.hass = hass

    entity.handle_notification(
        {"path": "notifications.navigation.other", "value": {"state": "alert"}}
    )

    assert entity.state is None


async def test_event_entity_skips_when_notifications_disabled(hass) -> None:
    entry = _make_entry(options={CONF_ENABLE_NOTIFICATIONS: False})
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")
    entity.hass = hass

    entity.handle_notification(
        {"path": "notifications.navigation.anchor", "value": {"state": "alert"}}
    )

    assert entity.state is None


async def test_event_entity_writes_state_when_hass_present(hass) -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entity = SignalKNotificationEvent(coordinator, entry, "notifications.navigation.anchor")
    entity.hass = hass
    entity._trigger_event = Mock()
    entity.async_write_ha_state = Mock()

    entity.handle_notification(
        {"path": "notifications.navigation.anchor", "value": {"state": "alert"}}
    )

    entity.async_write_ha_state.assert_called_once()


async def test_event_listener_skips_disabled_entity(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.*"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    registry = er.async_get(hass)
    unique_id = f"signalk:{entry.entry_id}:notifications.navigation.anchor"
    registry.async_get_or_create(
        "event",
        DOMAIN,
        unique_id,
        suggested_object_id="anchor",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {"state": "alert"},
        "timestamp": dt_util.utcnow().isoformat(),
    }

    coordinator._fire_notification(notification, coordinator.config)
    assert added == []


def test_notification_listener_skips_invalid_or_disallowed_path(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.navigation.anchor"]})
    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    registry = er.async_get(hass)
    created: list = []

    listener = _SignalKNotificationListener(
        coordinator,
        entry,
        registry,
        created.extend,
        allowed_paths={"notifications.navigation.anchor"},
        allow_all=False,
        ignored_prefixes=[],
        entities={},
    )

    listener.handle_notification({"path": 123})
    listener.handle_notification(
        {"path": "notifications.navigation.other", "value": {"state": "alert"}}
    )

    assert created == []


async def test_event_listener_creates_entity_for_wildcard(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.*"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    notification = {
        "path": "notifications.navigation.anchor",
        "value": {"state": "alert"},
        "timestamp": "2026-01-03T22:34:57.853Z",
    }

    coordinator._fire_notification(notification, coordinator.config)
    assert len(added) == 1


async def test_event_listener_skips_security_path_for_wildcard(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.*"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    coordinator._fire_notification(
        {"path": "notifications.security.accessRequest.any", "value": {"state": "alert"}},
        coordinator.config,
    )
    assert added == []


async def test_event_listener_creates_after_reenable(hass) -> None:
    entry = _make_entry(options={CONF_NOTIFICATION_PATHS: ["notifications.*"]})
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._state = ConnectionState.CONNECTED

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=Mock(),
        auth=SignalKAuthManager(None),
    )

    registry = er.async_get(hass)
    unique_id = f"signalk:{entry.entry_id}:notifications.navigation.anchor"
    disabled_id = registry.async_get_or_create(
        "event",
        DOMAIN,
        unique_id,
        suggested_object_id="anchor",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    ).entity_id

    added: list = []
    await async_setup_entry(hass, entry, added.extend)

    coordinator._fire_notification(
        {"path": "notifications.navigation.anchor", "value": {"state": "alert"}},
        coordinator.config,
    )
    assert added == []

    registry.async_update_entity(disabled_id, disabled_by=None)

    coordinator._fire_notification(
        {
            "path": "notifications.navigation.anchor",
            "value": {"state": "alert"},
            "timestamp": "2026-01-03T22:34:57.853Z",
        },
        coordinator.config,
    )
    assert len(added) == 1
