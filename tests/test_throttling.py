import time
from unittest.mock import Mock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.signalk_ha.auth import SignalKAuthManager
from custom_components.signalk_ha.const import (
    CONF_BASE_URL,
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DOMAIN,
)
from custom_components.signalk_ha.coordinator import SignalKCoordinator
from custom_components.signalk_ha.discovery import DiscoveredEntity
from custom_components.signalk_ha.sensor import SignalKSensor


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
        },
    )


def test_tolerance_allows_small_changes(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed",
        kind="sensor",
        unit="kn",
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=60.0,
    )
    sensor = SignalKSensor(coordinator, Mock(), entry, spec)

    sensor._last_native_value = 1.0
    sensor._last_available = True
    sensor._last_write = time.monotonic()

    assert sensor._should_write_state(1.05, True) is False


def test_tolerance_triggers_large_changes(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed",
        kind="sensor",
        unit="kn",
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=60.0,
    )
    sensor = SignalKSensor(coordinator, Mock(), entry, spec)

    sensor._last_native_value = 1.0
    sensor._last_available = True
    sensor._last_write = time.monotonic()

    sensor._last_write = time.monotonic() - 120.0
    assert sensor._should_write_state(1.5, True) is True


def test_min_interval_blocks_large_changes(hass) -> None:
    entry = _make_entry()
    entry.add_to_hass(hass)

    coordinator = SignalKCoordinator(hass, entry, Mock(), Mock(), SignalKAuthManager(None))
    spec = DiscoveredEntity(
        path="navigation.speedOverGround",
        name="Speed",
        kind="sensor",
        unit="kn",
        device_class=None,
        state_class=None,
        conversion=None,
        tolerance=0.1,
        min_update_seconds=60.0,
    )
    sensor = SignalKSensor(coordinator, Mock(), entry, spec)

    sensor._last_native_value = 1.0
    sensor._last_available = True
    sensor._last_write = time.monotonic()

    assert sensor._should_write_state(2.0, True) is False
