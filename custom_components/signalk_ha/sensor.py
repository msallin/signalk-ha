"""Sensor entities and health metrics for Signal K data."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_MAX_IDLE_WRITE_SECONDS,
    DEFAULT_MIN_UPDATE_MS,
    DEFAULT_STALE_SECONDS,
    HEALTH_SENSOR_CONNECTION_STATE,
    HEALTH_SENSOR_LAST_ERROR,
    HEALTH_SENSOR_LAST_MESSAGE,
    HEALTH_SENSOR_LAST_NOTIFICATION,
    HEALTH_SENSOR_MESSAGE_COUNT,
    HEALTH_SENSOR_MESSAGES_PER_HOUR,
    HEALTH_SENSOR_NOTIFICATION_COUNT,
    HEALTH_SENSOR_NOTIFICATIONS_PER_HOUR,
    HEALTH_SENSOR_RECONNECT_COUNT,
)
from .coordinator import SignalKCoordinator, SignalKDiscoveryCoordinator
from .device_info import build_device_info
from .discovery import DiscoveredEntity, convert_value
from .entity_utils import build_object_id, entity_id_prefix_for_entry, path_from_unique_id
from .policy import default_policy_from_entry, path_policies_from_entry

PARALLEL_UPDATES = 1


@dataclass(frozen=True)
class HealthSpec:
    key: str
    name: str
    value_fn: Callable[[Any], Any]
    device_class: SensorDeviceClass | None = None
    always_available: bool = True
    enabled_default: bool = True
    attributes_fn: Callable[[Any], dict[str, Any]] | None = None
    unit: str | None = None
    suggested_display_precision: int | None = None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    if runtime is None:
        return
    coordinator: SignalKCoordinator = runtime.coordinator
    discovery: SignalKDiscoveryCoordinator = runtime.discovery

    entities: list[SensorEntity] = []
    specs = _sensor_specs(discovery)
    if not specs:
        specs = _registry_sensor_specs(hass, entry)

    for spec in specs:
        entities.append(SignalKSensor(coordinator, discovery, entry, spec))

    health_specs = [
        HealthSpec(
            HEALTH_SENSOR_CONNECTION_STATE,
            "Connection State",
            lambda coord: coord.connection_state,
        ),
        HealthSpec(
            HEALTH_SENSOR_LAST_MESSAGE,
            "Last Message",
            lambda coord: coord.last_message,
            device_class=SensorDeviceClass.TIMESTAMP,
            enabled_default=False,
        ),
        HealthSpec(
            HEALTH_SENSOR_MESSAGE_COUNT,
            "Message Count",
            lambda coord: coord.message_count,
            enabled_default=False,
        ),
        HealthSpec(
            HEALTH_SENSOR_RECONNECT_COUNT,
            "Reconnect Count",
            lambda coord: coord.reconnect_count,
        ),
        HealthSpec(
            HEALTH_SENSOR_LAST_ERROR,
            "Last Error",
            lambda coord: coord.last_error,
        ),
        HealthSpec(
            HEALTH_SENSOR_NOTIFICATION_COUNT,
            "Notification Count",
            lambda coord: coord.notification_count,
        ),
        HealthSpec(
            HEALTH_SENSOR_MESSAGES_PER_HOUR,
            "Messages per Hour",
            lambda coord: coord.messages_per_hour,
            unit="1/h",
            enabled_default=False,
            suggested_display_precision=2,
        ),
        HealthSpec(
            HEALTH_SENSOR_LAST_NOTIFICATION,
            "Last Notification",
            lambda coord: coord.last_notification_timestamp,
            device_class=SensorDeviceClass.TIMESTAMP,
            attributes_fn=_last_notification_attributes,
        ),
        HealthSpec(
            HEALTH_SENSOR_NOTIFICATIONS_PER_HOUR,
            "Notifications per Hour",
            lambda coord: coord.notifications_per_hour,
            unit="1/h",
            enabled_default=False,
            suggested_display_precision=2,
        ),
    ]

    for spec in health_specs:
        entities.append(SignalKHealthSensor(coordinator, entry, spec))

    async_add_entities(entities)

    manager = _SignalKDiscoveryListener(
        coordinator, discovery, entry, async_add_entities, known_paths={spec.path for spec in specs}
    )
    entry.async_on_unload(discovery.async_add_listener(manager.handle_update))


def _sensor_specs(discovery: SignalKDiscoveryCoordinator) -> list[DiscoveredEntity]:
    data = discovery.data
    if not data:
        return []
    return [spec for spec in data.entities if spec.kind == "sensor"]


def _registry_sensor_specs(hass: HomeAssistant, entry: ConfigEntry) -> list[DiscoveredEntity]:
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    specs: list[DiscoveredEntity] = []
    default_period_ms, default_min_update_seconds = default_policy_from_entry(entry)
    path_policies = path_policies_from_entry(entry)
    for registry_entry in entries:
        if registry_entry.domain != "sensor":
            continue
        path = path_from_unique_id(registry_entry.unique_id)
        if not path:
            continue
        name = registry_entry.original_name or registry_entry.name or path.split(".")[-1]
        override = path_policies.get(path)
        period_ms = override.period_ms if override is not None else default_period_ms
        min_update_seconds = (
            override.min_update_seconds if override is not None else default_min_update_seconds
        )
        tolerance = override.tolerance if override is not None else None
        specs.append(
            DiscoveredEntity(
                path=path,
                name=name,
                kind="sensor",
                unit=None,
                device_class=None,
                state_class=None,
                conversion=None,
                tolerance=tolerance,
                min_update_seconds=min_update_seconds,
                period_ms=period_ms,
            )
        )
    return specs


class SignalKBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SignalKCoordinator,
        discovery: SignalKDiscoveryCoordinator | None,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._discovery = discovery
        self._entity_id_prefix = entity_id_prefix_for_entry(entry)
        self._suggested_object_id: str | None = None
        self._attr_device_info = build_device_info(entry)
        self._last_native_value: Any = None
        self._last_write: float | None = None
        self._last_available: bool | None = None

    @property
    def suggested_object_id(self) -> str | None:
        if self._entity_id_prefix:
            return self._suggested_object_id
        return super().suggested_object_id

    @callback
    def _handle_coordinator_update(self) -> None:
        available = self.available
        value = self.native_value
        if self._should_write_state(value, available):
            self._last_native_value = value
            self._last_available = available
            self._last_write = time.monotonic()
            self._record_write()
            self.async_write_ha_state()

    def _should_write_state(self, value: Any, available: bool) -> bool:
        if self._last_write is None:
            return True
        if available != self._last_available:
            return True

        now = time.monotonic()
        min_interval = self._min_update_seconds()
        # Enforce a minimum write interval to protect the recorder/UI from WS bursts.
        if now - self._last_write < min_interval:
            return False
        # Refresh state periodically only when fresh updates are arriving from the server.
        if (
            now - self._last_write >= DEFAULT_MAX_IDLE_WRITE_SECONDS
            and self._should_refresh_on_idle()
        ):
            return True

        if value is None and self._last_native_value is not None:
            return True

        if isinstance(value, (int, float)) and isinstance(self._last_native_value, (int, float)):
            tolerance = self._tolerance()
            if tolerance is None:
                return value != self._last_native_value
            return abs(value - self._last_native_value) > tolerance

        return value != self._last_native_value

    def _tolerance(self) -> float | None:
        return None

    def _min_update_seconds(self) -> float:
        return DEFAULT_MIN_UPDATE_MS / 1000.0

    def _should_refresh_on_idle(self) -> bool:
        return True

    def _record_write(self) -> None:
        return None


class SignalKSensor(SignalKBaseSensor):
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: SignalKCoordinator,
        discovery: SignalKDiscoveryCoordinator,
        entry: ConfigEntry,
        spec: DiscoveredEntity,
    ) -> None:
        super().__init__(coordinator, discovery, entry)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_unique_id = f"signalk:{entry.entry_id}:{spec.path}"
        if self._entity_id_prefix:
            self._suggested_object_id = build_object_id(spec.path, prefix=self._entity_id_prefix)
        self._last_seen_at: dt_util.dt | None = None
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.state_class:
            self._attr_state_class = spec.state_class
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.icon:
            self._attr_icon = spec.icon
        if spec.suggested_display_precision is not None:
            self._attr_suggested_display_precision = spec.suggested_display_precision

    @property
    def available(self) -> bool:
        if not self.coordinator.is_connected:
            return False
        if not _path_available(self._spec.path, self._discovery):
            return False
        raw = self.coordinator.data.get(self._spec.path)
        if raw is None:
            return False
        return not _is_stale(self._spec.path, self.coordinator)

    @property
    def native_value(self) -> Any:
        raw = self.coordinator.data.get(self._spec.path)
        return convert_value(raw, self._spec.conversion)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last_seen = _last_seen(self._spec.path, self.coordinator)
        attrs: dict[str, Any] = {
            "path": self._spec.path,
            "last_seen": last_seen,
            "spec_known": self._spec.spec_known,
            "subscription_period_seconds": self._spec.period_ms / 1000.0,
            "min_update_seconds": self._min_update_seconds(),
            "stale_seconds": DEFAULT_STALE_SECONDS,
        }
        if self._spec.description:
            attrs["description"] = self._spec.description
        source = self.coordinator.last_source_by_path.get(self._spec.path)
        if source:
            attrs["source"] = source
        if self._spec.tolerance is not None:
            attrs["tolerance"] = self._spec.tolerance
        return attrs

    def _tolerance(self) -> float | None:
        return self._spec.tolerance

    def _min_update_seconds(self) -> float:
        if self._spec.min_update_seconds is None:
            return DEFAULT_MIN_UPDATE_MS / 1000.0
        return self._spec.min_update_seconds

    def _should_refresh_on_idle(self) -> bool:
        last_seen = self._current_seen_at()
        if last_seen is None:
            return False
        if getattr(self, "_last_seen_at", None) is None:
            # Force a first write once we see data so attributes reflect initial timestamps.
            return True
        return last_seen > self._last_seen_at

    def _record_write(self) -> None:
        last_seen = self._current_seen_at()
        if last_seen is not None:
            # Track the last payload timestamp to suppress idle writes without new data.
            self._last_seen_at = last_seen

    def _current_seen_at(self) -> dt_util.dt | None:
        return self.coordinator.last_update_by_path.get(self._spec.path)


class SignalKHealthSensor(SignalKBaseSensor):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: SignalKCoordinator, entry: ConfigEntry, spec: HealthSpec
    ) -> None:
        super().__init__(coordinator, None, entry)
        self._spec = spec
        self._attr_name = spec.name
        self._attr_unique_id = f"signalk:{entry.entry_id}:health:{spec.key}"
        if self._entity_id_prefix:
            self._suggested_object_id = build_object_id(
                f"health_{spec.key}", prefix=self._entity_id_prefix
            )
        self._attr_entity_registry_enabled_default = spec.enabled_default
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.suggested_display_precision is not None:
            self._attr_suggested_display_precision = spec.suggested_display_precision

    @property
    def available(self) -> bool:
        return self._spec.always_available

    @property
    def native_value(self) -> Any:
        return self._spec.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if not self._spec.attributes_fn:
            return {}
        return self._spec.attributes_fn(self.coordinator) or {}

    def _should_refresh_on_idle(self) -> bool:
        return False


class _SignalKDiscoveryListener:
    def __init__(
        self,
        coordinator: SignalKCoordinator,
        discovery: SignalKDiscoveryCoordinator,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        *,
        known_paths: set[str] | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._discovery = discovery
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._known_paths: set[str] = known_paths or set()

    @callback
    def handle_update(self) -> None:
        specs = _sensor_specs(self._discovery)
        new_entities: list[SensorEntity] = []
        for spec in specs:
            if spec.path in self._known_paths:
                continue
            self._known_paths.add(spec.path)
            new_entities.append(
                SignalKSensor(self._coordinator, self._discovery, self._entry, spec)
            )

        if new_entities:
            self._async_add_entities(new_entities)


def _last_seen(path: str, coordinator: SignalKCoordinator) -> str | None:
    timestamp = coordinator.last_update_by_path.get(path)
    if not timestamp:
        return None
    return dt_util.as_utc(timestamp).isoformat()


def _is_stale(path: str, coordinator: SignalKCoordinator) -> bool:
    timestamp = coordinator.last_update_by_path.get(path)
    if not timestamp:
        return True
    age = dt_util.utcnow() - timestamp
    return age.total_seconds() > DEFAULT_STALE_SECONDS


def _path_available(path: str, discovery: SignalKDiscoveryCoordinator | None) -> bool:
    if not discovery or not discovery.data:
        return True
    return path in discovery.data.paths


def _last_notification_attributes(coordinator: SignalKCoordinator) -> dict[str, Any] | None:
    notification = coordinator.last_notification
    if not notification:
        return None
    attrs = dict(notification)
    received_at = attrs.get("received_at")
    if received_at:
        attrs["received_at"] = dt_util.as_utc(received_at).isoformat()
    return attrs
