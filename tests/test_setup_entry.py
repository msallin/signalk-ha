from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalk_ha import (
    _async_entry_updated,
    _async_register_services,
    _async_update_subscriptions,
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.signalk_ha.const import (
    CONF_BASE_URL,
    CONF_DEFAULT_PERIOD_MS,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_HOST,
    CONF_INSTANCE_ID,
    CONF_PATH_POLICIES,
    CONF_PORT,
    CONF_REFRESH_INTERVAL_HOURS,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DEFAULT_PERIOD_MS,
    DEFAULT_REFRESH_INTERVAL_HOURS,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SK_PATH_NOTIFICATIONS,
)
from custom_components.signalk_ha.discovery import DiscoveredEntity, DiscoveryResult
from custom_components.signalk_ha.entity_utils import path_from_unique_id
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


async def test_setup_entry_sets_runtime_data_and_subscriptions(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    )

    refresh = AsyncMock()
    with (
        patch(
            "custom_components.signalk_ha.__init__.SignalKDiscoveryCoordinator.async_config_entry_first_refresh",
            new=refresh,
        ),
        patch(
            "custom_components.signalk_ha.async_get_clientsession",
            return_value=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_start",
            new=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_update_paths",
            new=AsyncMock(),
        ) as update_paths,
        patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()),
    ):
        assert await async_setup_entry(hass, entry) is True

    runtime = entry.runtime_data
    assert isinstance(runtime, SignalKRuntimeData)
    refresh.assert_awaited_once()
    update_paths.assert_called_once()


async def test_setup_entry_continues_on_discovery_error(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.signalk_ha.__init__.SignalKDiscoveryCoordinator.async_config_entry_first_refresh",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "custom_components.signalk_ha.async_get_clientsession",
            return_value=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_start",
            new=AsyncMock(),
        ),
        patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()),
    ):
        assert await async_setup_entry(hass, entry) is True


async def test_setup_entry_uses_registry_defaults_when_discovery_missing(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    )

    async def _refresh(self):
        self.last_update_success = False
        self.data = None

    with (
        patch(
            "custom_components.signalk_ha.__init__.SignalKDiscoveryCoordinator.async_config_entry_first_refresh",
            new=_refresh,
        ),
        patch(
            "custom_components.signalk_ha.async_get_clientsession",
            return_value=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_start",
            new=AsyncMock(),
        ),
        patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_update_paths",
            new=AsyncMock(),
        ) as update_paths,
    ):
        assert await async_setup_entry(hass, entry) is True

    update_paths.assert_called_once()
    paths, periods = update_paths.call_args.args
    assert paths == ["navigation.speedOverGround", SK_PATH_NOTIFICATIONS]
    assert periods["navigation.speedOverGround"] == DEFAULT_PERIOD_MS


async def test_unload_entry_stops_runtime(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    runtime = SignalKRuntimeData(
        coordinator=AsyncMock(),
        discovery=AsyncMock(),
        auth=AsyncMock(),
    )
    entry.runtime_data = runtime

    with patch.object(
        hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)
    ):
        assert await async_unload_entry(hass, entry) is True

    runtime.coordinator.async_stop.assert_awaited_once()
    runtime.discovery.async_stop.assert_awaited_once()
    assert entry.runtime_data is None


async def test_unload_entry_without_runtime(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    with patch.object(
        hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True)
    ):
        assert await async_unload_entry(hass, entry) is True


async def test_migrate_entry_sets_defaults(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "sk.local", CONF_PORT: 3000, CONF_SSL: False},
        version=1,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.version == 2
    assert entry.data[CONF_BASE_URL].endswith("/signalk/v1/api/")
    assert entry.data[CONF_WS_URL].endswith("/signalk/v1/stream?subscribe=none")
    assert entry.data[CONF_VERIFY_SSL] == DEFAULT_VERIFY_SSL
    assert entry.data[CONF_VESSEL_ID] == ""
    assert entry.data[CONF_VESSEL_NAME] == "Unknown Vessel"
    assert entry.data[CONF_REFRESH_INTERVAL_HOURS] == DEFAULT_REFRESH_INTERVAL_HOURS


async def test_migrate_entry_skips_host_defaults(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, version=1)
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert CONF_BASE_URL not in entry.data
    assert CONF_WS_URL not in entry.data


async def test_migrate_entry_preserves_instance_id(hass) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_INSTANCE_ID: "instance:fixed"},
        version=1,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.data[CONF_INSTANCE_ID] == "instance:fixed"


async def test_migrate_entry_noop_on_current_version(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, version=2)
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_update_entry") as update:
        assert await async_migrate_entry(hass, entry) is True
    update.assert_not_called()


async def test_update_subscriptions_uses_registry_and_periods(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    ).entity_id
    disabled_id = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.depth",
        suggested_object_id="depth",
        config_entry=entry,
    ).entity_id
    registry.async_update_entity(disabled_id, disabled_by=er.RegistryEntryDisabler.USER)

    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=None,
        min_update_seconds=None,
        period_ms=750,
    )
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    coordinator = AsyncMock()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=discovery,
        auth=AsyncMock(),
    )

    await _async_update_subscriptions(hass, entry)

    coordinator.async_update_paths.assert_awaited_once()
    paths, periods = coordinator.async_update_paths.call_args.args
    assert paths == ["navigation.speedOverGround", SK_PATH_NOTIFICATIONS]
    assert periods == {
        "navigation.speedOverGround": 750,
        SK_PATH_NOTIFICATIONS: DEFAULT_PERIOD_MS,
    }


async def test_update_subscriptions_disable_notifications(hass) -> None:
    entry = _make_entry(options={CONF_ENABLE_NOTIFICATIONS: False})
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    ).entity_id

    coordinator = AsyncMock()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=SimpleNamespace(data=None),
        auth=AsyncMock(),
    )

    await _async_update_subscriptions(hass, entry)

    paths, periods = coordinator.async_update_paths.call_args.args
    assert paths == ["navigation.speedOverGround"]
    assert SK_PATH_NOTIFICATIONS not in periods


async def test_update_subscriptions_applies_path_policy_override(hass) -> None:
    entry = _make_entry(
        options={
            CONF_DEFAULT_PERIOD_MS: 2000,
            CONF_PATH_POLICIES: {
                "navigation.speedOverGround": {
                    "period_ms": 1000,
                    "min_update_seconds": 1.0,
                }
            },
        }
    )
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    ).entity_id

    coordinator = AsyncMock()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=SimpleNamespace(data=None),
        auth=AsyncMock(),
    )

    await _async_update_subscriptions(hass, entry)

    _, periods = coordinator.async_update_paths.call_args.args
    assert periods["navigation.speedOverGround"] == 1000


async def test_set_path_policy_service_updates_options_and_reloads(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    _async_register_services(hass)

    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload_entry:
        await hass.services.async_call(
            DOMAIN,
            "set_path_policy",
            {
                "entry_id": entry.entry_id,
                "path": "environment.wind.speedTrue",
                "period_ms": 1000,
                "min_update_seconds": 1.0,
                "tolerance": 0.2,
            },
            blocking=True,
        )

    assert entry.options[CONF_PATH_POLICIES]["environment.wind.speedTrue"]["period_ms"] == 1000
    assert (
        entry.options[CONF_PATH_POLICIES]["environment.wind.speedTrue"]["min_update_seconds"] == 1.0
    )
    assert entry.options[CONF_PATH_POLICIES]["environment.wind.speedTrue"]["tolerance"] == 0.2
    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_update_subscriptions_skips_invalid_and_notification_dup(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "invalid",
        suggested_object_id="invalid",
        config_entry=entry,
    )
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:{SK_PATH_NOTIFICATIONS}",
        suggested_object_id="notifications_all",
        config_entry=entry,
    )

    coordinator = AsyncMock()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=SimpleNamespace(data=None),
        auth=AsyncMock(),
    )

    await _async_update_subscriptions(hass, entry)

    paths, periods = coordinator.async_update_paths.call_args.args
    assert paths == [SK_PATH_NOTIFICATIONS]
    assert periods == {SK_PATH_NOTIFICATIONS: DEFAULT_PERIOD_MS}


def test_path_from_unique_id() -> None:
    assert path_from_unique_id(None) is None
    assert path_from_unique_id("invalid") is None
    assert path_from_unique_id("signalk:entry") is None
    assert path_from_unique_id("signalk:entry:navigation.speed") == "navigation.speed"


async def test_registry_update_triggers_subscription_refresh(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry_entry = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    )

    listener_holder = {}

    def _listen(event_type, listener):
        assert event_type == EVENT_ENTITY_REGISTRY_UPDATED
        listener_holder["listener"] = listener
        return lambda: None

    created: list = []

    def _create_task(coro):
        created.append(coro)
        coro.close()

    with (
        patch(
            "custom_components.signalk_ha.__init__.SignalKDiscoveryCoordinator.async_config_entry_first_refresh",
            new=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.async_get_clientsession",
            return_value=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha.__init__.SignalKCoordinator.async_start",
            new=AsyncMock(),
        ),
        patch(
            "custom_components.signalk_ha._async_update_subscriptions",
            new=AsyncMock(),
        ) as update_subs,
        patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()),
        patch.object(hass, "async_create_task", side_effect=_create_task),
        patch("homeassistant.core.EventBus.async_listen", side_effect=_listen),
    ):
        assert await async_setup_entry(hass, entry) is True

        event = SimpleNamespace(data={"action": "update"})
        listener_holder["listener"](event)
        assert update_subs.call_count == 1

        with patch(
            "custom_components.signalk_ha.__init__.er.async_get",
            return_value=SimpleNamespace(
                async_get=lambda entity_id: SimpleNamespace(config_entry_id="other")
            ),
        ):
            event = SimpleNamespace(
                data={"entity_id": registry_entry.entity_id, "action": "update"},
            )
            listener_holder["listener"](event)
        assert update_subs.call_count == 1

        event = SimpleNamespace(
            data={
                "entity_id": registry_entry.entity_id,
                "action": "update",
                "changes": {"name": ("old", "new")},
            },
        )
        listener_holder["listener"](event)
        assert update_subs.call_count == 1

        event = SimpleNamespace(
            data={
                "entity_id": registry_entry.entity_id,
                "action": "create",
            },
        )
        listener_holder["listener"](event)
        assert update_subs.call_count == 2

        event = SimpleNamespace(
            data={
                "entity_id": "sensor.unknown",
                "action": "create",
            },
        )
        listener_holder["listener"](event)
        assert update_subs.call_count == 2

        event = SimpleNamespace(
            data={
                "entity_id": registry_entry.entity_id,
                "action": "update",
                "changes": {"disabled_by": (None, "user")},
            },
        )
        listener_holder["listener"](event)
        assert update_subs.call_count == 3

    assert update_subs.call_count == 3
    assert created


async def test_entry_updated_triggers_reload(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    with patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload_entry:
        await _async_entry_updated(hass, entry)

    reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_update_subscriptions_no_runtime(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    entry.runtime_data = None

    await _async_update_subscriptions(hass, entry)


async def test_update_subscriptions_skips_event_entities(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.speedOverGround",
        suggested_object_id="speed_over_ground",
        config_entry=entry,
    ).entity_id
    registry.async_get_or_create(
        "event",
        DOMAIN,
        f"signalk:{entry.entry_id}:notifications.navigation.anchor",
        suggested_object_id="navigation_anchor_notification",
        config_entry=entry,
    )

    coordinator = AsyncMock()
    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=SimpleNamespace(data=None),
        auth=AsyncMock(),
    )

    await _async_update_subscriptions(hass, entry)

    paths, _ = coordinator.async_update_paths.call_args.args
    assert "notifications.navigation.anchor" not in paths
    assert SK_PATH_NOTIFICATIONS in paths
