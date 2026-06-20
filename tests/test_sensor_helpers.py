import time
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from homeassistant.components.sensor import ATTR_STATE_CLASS, SensorDeviceClass, SensorStateClass
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalk_ha.auth import SignalKAuthManager
from custom_components.signalk_ha.const import (
    CONF_BASE_URL,
    CONF_HOST,
    CONF_PORT,
    CONF_SERVER_ID,
    CONF_SERVER_VERSION,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DEFAULT_MAX_IDLE_WRITE_SECONDS,
    DEFAULT_MIN_UPDATE_MS,
    DOMAIN,
)
from custom_components.signalk_ha.coordinator import ConnectionState, SignalKCoordinator
from custom_components.signalk_ha.device_info import build_device_info
from custom_components.signalk_ha.discovery import DiscoveredEntity, DiscoveryResult
from custom_components.signalk_ha.entity_utils import path_from_unique_id
from custom_components.signalk_ha.mapping import Conversion
from custom_components.signalk_ha.sensor import (
    HealthSpec,
    SignalKBaseSensor,
    SignalKHealthSensor,
    SignalKSensor,
    _is_stale,
    _last_notification_attributes,
    _last_seen,
    _path_available,
    _registry_sensor_specs,
    _sensor_specs,
    _SignalKDiscoveryListener,
)


def _make_entry() -> MockConfigEntry:
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
            CONF_SERVER_ID: "signalk-server-node",
            CONF_SERVER_VERSION: "2.19.0",
        },
    )


async def test_registry_sensor_specs(hass) -> None:
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

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    assert specs[0].path == "navigation.speedOverGround"
    assert specs[0].unit == "kn"
    assert specs[0].device_class == SensorDeviceClass.SPEED
    assert specs[0].state_class == SensorStateClass.MEASUREMENT
    assert specs[0].conversion == Conversion.MS_TO_KNOTS
    assert specs[0].spec_known is True


async def test_registry_sensor_specs_uses_registry_metadata_for_unmapped_path(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:custom.unmappedPath",
        suggested_object_id="custom_unmapped_path",
        config_entry=entry,
        unit_of_measurement="V",
        original_device_class=SensorDeviceClass.VOLTAGE,
        capabilities={ATTR_STATE_CLASS: SensorStateClass.MEASUREMENT},
    )

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    spec = specs[0]
    assert spec.path == "custom.unmappedPath"
    assert spec.unit == "V"
    assert spec.device_class == SensorDeviceClass.VOLTAGE
    assert spec.state_class == SensorStateClass.MEASUREMENT
    assert spec.conversion is None
    assert spec.spec_known is False


async def test_registry_sensor_specs_restores_registry_icon(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:custom.iconPath",
        suggested_object_id="custom_icon_path",
        config_entry=entry,
        unit_of_measurement="V",
        original_device_class=SensorDeviceClass.VOLTAGE,
        original_icon="mdi:flash",
    )

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    spec = specs[0]
    assert spec.path == "custom.iconPath"
    assert spec.icon == "mdi:flash"


async def test_registry_sensor_specs_inferrs_schema_conversion_from_registry_unit(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:environment.outside.temperature",
        suggested_object_id="outside_temperature",
        config_entry=entry,
        unit_of_measurement="°C",
        capabilities={ATTR_STATE_CLASS: SensorStateClass.MEASUREMENT},
    )

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    spec = specs[0]
    assert spec.path == "environment.outside.temperature"
    assert spec.unit == "°C"
    assert spec.state_class == SensorStateClass.MEASUREMENT
    assert spec.conversion == Conversion.K_TO_C
    assert spec.spec_known is True


async def test_registry_sensor_specs_does_not_infer_conversion_without_unit_alignment(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:environment.outside.temperature",
        suggested_object_id="outside_temperature_raw",
        config_entry=entry,
        unit_of_measurement="K",
    )

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    spec = specs[0]
    assert spec.path == "environment.outside.temperature"
    assert spec.unit == "K"
    assert spec.conversion is None
    assert spec.spec_known is True


async def test_registry_sensor_specs_uses_schema_unit_when_registry_unit_mismatches(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"signalk:{entry.entry_id}:environment.outside.temperature",
        suggested_object_id="outside_temperature_fahrenheit",
        config_entry=entry,
        unit_of_measurement="°F",
    )

    specs = _registry_sensor_specs(hass, entry)
    assert specs
    spec = specs[0]
    assert spec.path == "environment.outside.temperature"
    assert spec.unit == "K"
    assert spec.conversion is None
    assert spec.spec_known is True


async def test_registry_sensor_specs_filters_invalid(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "geo_location",
        DOMAIN,
        f"signalk:{entry.entry_id}:navigation.position",
        suggested_object_id="position",
        config_entry=entry,
    )
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
        f"signalk:{entry.entry_id}:navigation.depth",
        suggested_object_id="depth",
        config_entry=entry,
    )

    specs = _registry_sensor_specs(hass, entry)
    assert [spec.path for spec in specs] == ["navigation.depth"]


def test_health_sensor_value() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec("connection_state", "Connection State", lambda coord: coord.connection_state)
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor.native_value == coordinator.connection_state


def test_health_sensor_attributes() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._last_notification = {
        "path": "notifications.navigation.anchor",
        "state": "alert",
        "received_at": dt_util.utcnow(),
    }
    spec = HealthSpec(
        "last_notification",
        "Last Notification",
        lambda coord: coord.last_notification_timestamp,
        attributes_fn=_last_notification_attributes,
    )
    sensor = SignalKHealthSensor(coordinator, entry, spec)

    attrs = sensor.extra_state_attributes
    assert attrs["path"] == "notifications.navigation.anchor"
    assert "received_at" in attrs


def test_health_sensor_unit() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec(
        "messages_per_hour",
        "Messages per Hour",
        lambda coord: coord.messages_per_hour,
        unit="1/h",
    )
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor.native_unit_of_measurement == "1/h"


def test_health_sensor_suggested_precision() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec(
        "messages_per_hour",
        "Messages per Hour",
        lambda coord: coord.messages_per_hour,
        unit="1/h",
        suggested_display_precision=2,
    )
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor.suggested_display_precision == 2


def test_discovery_listener_adds_entities() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit="kn",
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=None,
        min_update_seconds=None,
    )
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    async_add = Mock()

    listener = _SignalKDiscoveryListener(
        coordinator, discovery, entry, async_add, known_paths=set()
    )
    listener.handle_update()

    async_add.assert_called_once()


def test_discovery_listener_skips_known_paths() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit="kn",
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=None,
        min_update_seconds=None,
    )
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    async_add = Mock()

    listener = _SignalKDiscoveryListener(
        coordinator, discovery, entry, async_add, known_paths={spec.path}
    )
    listener.handle_update()

    async_add.assert_not_called()


def test_sensor_should_write_state_on_value_change() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)

    sensor._last_native_value = "old"
    sensor._last_available = True
    assert sensor._should_write_state("new", True) is True


def test_sensor_should_write_state_respects_tolerance() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=None,
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic()
    sensor._last_native_value = 10.0
    sensor._last_available = True

    assert sensor._should_write_state(10.05, True) is False


def test_sensor_should_write_state_after_max_idle() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=None,
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic() - DEFAULT_MAX_IDLE_WRITE_SECONDS - 1.0
    sensor._last_native_value = 10.0
    sensor._last_available = True
    sensor._last_seen_at = dt_util.utcnow() - timedelta(seconds=10)
    coordinator._last_update_by_path["navigation.speedOverGround"] = dt_util.utcnow()

    assert sensor._should_write_state(10.05, True) is True


def test_sensor_should_write_state_on_availability_change() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic()
    sensor._last_available = False

    assert sensor._should_write_state(10.0, True) is True


def test_sensor_should_write_state_after_min_interval() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=None,
        min_update_seconds=0.0,
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic()
    sensor._last_available = True

    assert sensor._should_write_state(10.0, True) is True


def test_sensor_should_write_state_when_value_clears() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic() - 10.0
    sensor._last_native_value = 10.0
    sensor._last_available = True

    assert sensor._should_write_state(None, True) is True


def test_health_sensor_available() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec("connection_state", "Connection State", lambda coord: coord.connection_state)
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor.available is True


def test_sensor_handle_update_no_write_when_unchanged() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=None,
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    coordinator._state = ConnectionState.CONNECTED
    coordinator.data = {"navigation.speedOverGround": 10.0}
    coordinator._last_update_by_path["navigation.speedOverGround"] = dt_util.utcnow()

    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic()
    sensor._last_native_value = 10.0
    sensor._last_available = True
    sensor.async_write_ha_state = Mock()

    sensor._handle_coordinator_update()

    sensor.async_write_ha_state.assert_not_called()


def test_sensor_helpers_last_seen_and_stale() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    assert _last_seen("navigation.speedOverGround", coordinator) is None
    assert _is_stale("navigation.speedOverGround", coordinator) is True


def test_sensor_helpers_path_available() -> None:
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[], conflicts=[]))
    assert _path_available("navigation.speedOverGround", discovery) is False


def test_sensor_helpers_path_available_true() -> None:
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
    )
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    assert _path_available("navigation.speedOverGround", discovery) is True


def test_sensor_helpers_path_available_without_discovery() -> None:
    assert _path_available("navigation.speedOverGround", None) is True


def test_base_sensor_defaults() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec("connection_state", "Connection State", lambda coord: coord.connection_state)
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor._tolerance() is None
    assert sensor._min_update_seconds() == DEFAULT_MIN_UPDATE_MS / 1000.0


def test_health_sensor_attributes_empty() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec("connection_state", "Connection State", lambda coord: coord.connection_state)
    sensor = SignalKHealthSensor(coordinator, entry, spec)
    assert sensor.extra_state_attributes == {}


def test_sensor_should_write_state_with_min_interval() -> None:
    entry = _make_entry()
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed Over Ground",
        kind="sensor",
        unit=None,
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=None,
        min_update_seconds=0.0,
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic() - 5.0
    sensor._last_available = True

    assert sensor._should_write_state(10.0, True) is True


def test_sensor_should_write_state_numeric_change_no_tolerance() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)
    sensor._last_write = time.monotonic() - 10.0
    sensor._last_native_value = 10.0
    sensor._last_available = True

    assert sensor._should_write_state(11.0, True) is True


def test_base_sensor_idle_refresh_and_record_write() -> None:
    class _DummySensor(SignalKBaseSensor):
        @property
        def native_value(self):
            return None

    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    sensor = _DummySensor(coordinator, None, entry)

    assert sensor._should_refresh_on_idle() is True
    assert sensor._record_write() is None


def test_sensor_refresh_on_first_seen() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    coordinator._last_update_by_path[spec.path] = dt_util.utcnow()
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)

    assert sensor._should_refresh_on_idle() is True


def test_sensor_no_idle_refresh_without_seen() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)

    assert sensor._should_refresh_on_idle() is False


def test_sensor_record_write_without_last_seen() -> None:
    entry = _make_entry()
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
    )
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    discovery = SimpleNamespace(data=DiscoveryResult(entities=[spec], conflicts=[]))
    sensor = SignalKSensor(coordinator, discovery, entry, spec)

    sensor._record_write()
    assert sensor._last_seen_at is None


def test_health_sensor_does_not_idle_refresh() -> None:
    entry = _make_entry()
    coordinator = SignalKCoordinator(Mock(), entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = HealthSpec("demo", "Demo", lambda coord: coord.connection_state)
    sensor = SignalKHealthSensor(coordinator, entry, spec)

    assert sensor._should_refresh_on_idle() is False


def test_device_info_uses_base_url() -> None:
    entry = _make_entry()
    info = build_device_info(entry)
    assert info["name"] == "ONA"
    assert info["configuration_url"] == entry.data[CONF_BASE_URL]
    assert info["model"] == entry.data[CONF_SERVER_ID]
    assert info["sw_version"] == entry.data[CONF_SERVER_VERSION]


def test_last_notification_attributes_none() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    assert _last_notification_attributes(coordinator) is None


def test_last_notification_attributes_formats_timestamp() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    received_at = dt_util.utcnow()
    coordinator._last_notification = {"received_at": received_at, "message": "test"}

    attrs = _last_notification_attributes(coordinator)
    assert attrs is not None
    assert attrs["received_at"] == dt_util.as_utc(received_at).isoformat()


def test_last_notification_attributes_without_timestamp() -> None:
    coordinator = SignalKCoordinator(
        Mock(), _make_entry(), Mock(), Mock(), SignalKAuthManager(None)
    )
    coordinator._last_notification = {"message": "test"}

    attrs = _last_notification_attributes(coordinator)
    assert attrs is not None
    assert "received_at" not in attrs


def test_sensor_specs_empty_without_data() -> None:
    discovery = SimpleNamespace(data=None)
    assert _sensor_specs(discovery) == []


def test_path_from_unique_id_sensor() -> None:
    assert path_from_unique_id(None) is None
    assert path_from_unique_id("bad") is None
    assert path_from_unique_id("signalk:entry") is None
    assert path_from_unique_id("signalk:entry:navigation.speed") == "navigation.speed"
