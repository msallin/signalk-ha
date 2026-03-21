"""Geo-location entity for vessel position updates."""

from __future__ import annotations

import math
import time
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_MAX_IDLE_WRITE_SECONDS,
    DEFAULT_MIN_UPDATE_MS,
    DEFAULT_PERIOD_MS,
    DEFAULT_POSITION_TOLERANCE_M,
    DEFAULT_STALE_SECONDS,
    SK_PATH_POSITION,
)
from .coordinator import SignalKCoordinator, SignalKDiscoveryCoordinator
from .device_info import build_device_info
from .entity_utils import build_object_id, entity_id_prefix_for_entry

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = entry.runtime_data
    if runtime is None:
        return
    coordinator: SignalKCoordinator = runtime.coordinator
    discovery: SignalKDiscoveryCoordinator = runtime.discovery

    should_create = _should_create_geolocation(discovery) or _registry_has_geolocation(hass, entry)
    if should_create:
        async_add_entities([SignalKPositionGeolocation(coordinator, discovery, entry)])

    listener = _SignalKDiscoveryListener(
        coordinator,
        discovery,
        entry,
        async_add_entities,
        created=should_create,
    )
    entry.async_on_unload(discovery.async_add_listener(listener.handle_update))


def _should_create_geolocation(discovery: SignalKDiscoveryCoordinator) -> bool:
    data = discovery.data
    if not data:
        return False
    return any(
        spec.path == SK_PATH_POSITION and spec.kind == "geo_location" for spec in data.entities
    )


def _registry_has_geolocation(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    unique_id = f"signalk:{entry.entry_id}:{SK_PATH_POSITION}"
    return any(
        reg_entry.domain == "geo_location" and reg_entry.unique_id == unique_id
        for reg_entry in entries
    )


class SignalKPositionGeolocation(CoordinatorEntity, GeolocationEvent):
    _attr_entity_registry_enabled_default = False
    _attr_source = "Signal K"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SignalKCoordinator,
        discovery: SignalKDiscoveryCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._discovery = discovery
        self._entity_id_prefix = entity_id_prefix_for_entry(entry)
        self._suggested_object_id = build_object_id(SK_PATH_POSITION, prefix=self._entity_id_prefix)
        self._attr_device_info = build_device_info(entry)
        self._description = _position_description(discovery)
        self._spec_known = _position_spec_known(discovery)

        self._attr_name = "Position"
        self._attr_unique_id = f"signalk:{entry.entry_id}:{SK_PATH_POSITION}"
        self._last_coords: tuple[float, float] | None = None
        self._last_write: float | None = None
        self._last_available: bool | None = None
        self._last_seen_at: dt_util.dt | None = None

    @property
    def suggested_object_id(self) -> str | None:
        if not self._entity_id_prefix:
            return super().suggested_object_id
        return self._suggested_object_id

    @property
    def available(self) -> bool:
        if not self.coordinator.is_connected:
            return False
        if not _path_available(self._discovery):
            return False
        raw = self.coordinator.data.get(SK_PATH_POSITION)
        if not isinstance(raw, dict):
            return False
        return not _is_stale(self.coordinator)

    @property
    def latitude(self) -> float | None:
        raw = self.coordinator.data.get(SK_PATH_POSITION)
        if not isinstance(raw, dict):
            return None
        value = raw.get("latitude")
        return float(value) if value is not None else None

    @property
    def longitude(self) -> float | None:
        raw = self.coordinator.data.get(SK_PATH_POSITION)
        if not isinstance(raw, dict):
            return None
        value = raw.get("longitude")
        return float(value) if value is not None else None

    @property
    def distance(self) -> float | None:
        if self.latitude is None or self.longitude is None:
            return None
        # The device represents the vessel running HA, so distance to itself is always zero.
        return 0.0

    @property
    def state_attributes(self) -> dict[str, Any]:
        data = super().state_attributes
        data["path"] = SK_PATH_POSITION
        data["spec_known"] = self._spec_known
        data["subscription_period_seconds"] = DEFAULT_PERIOD_MS / 1000.0
        data["min_update_ms"] = DEFAULT_MIN_UPDATE_MS
        data["stale_seconds"] = DEFAULT_STALE_SECONDS
        data["tolerance"] = DEFAULT_POSITION_TOLERANCE_M
        if self._description:
            data["description"] = self._description
        source = self.coordinator.last_source_by_path.get(SK_PATH_POSITION)
        if source:
            data["source"] = source
        last_seen = _last_seen(self.coordinator)
        if last_seen is not None:
            data["last_seen"] = last_seen
        return data

    @callback
    def _handle_coordinator_update(self) -> None:
        available = self.available
        coords = self._coords()
        if self._should_write_state(coords, available):
            self._last_coords = coords
            self._last_available = available
            self._last_write = time.monotonic()
            last_seen = self._current_seen_at()
            if last_seen is not None:
                self._last_seen_at = last_seen
            self.async_write_ha_state()

    def _coords(self) -> tuple[float, float] | None:
        lat = self.latitude
        lon = self.longitude
        if lat is None or lon is None:
            return None
        return (lat, lon)

    def _should_write_state(self, coords: tuple[float, float] | None, available: bool) -> bool:
        if self._last_write is None:
            return True
        if available != self._last_available:
            return True

        now = time.monotonic()
        if now - self._last_write < DEFAULT_MIN_UPDATE_MS / 1000.0:
            return False
        if now - self._last_write >= DEFAULT_MAX_IDLE_WRITE_SECONDS:
            last_seen = self._current_seen_at()
            if last_seen is not None and (
                self._last_seen_at is None or last_seen > self._last_seen_at
            ):
                return True

        if coords is None and self._last_coords is not None:
            return True

        if coords and self._last_coords:
            # Position tolerance reduces churn from GPS jitter while anchored.
            return _coord_distance(coords, self._last_coords) > DEFAULT_POSITION_TOLERANCE_M
        return coords != self._last_coords

    def _current_seen_at(self) -> dt_util.dt | None:
        return self.coordinator.last_update_by_path.get(SK_PATH_POSITION)


def _coord_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    # Haversine distance on a sphere:
    # 1) Convert lat/lon deltas to radians.
    # 2) Compute haversine of the central angle (sin²(Δφ/2) + cosφ1·cosφ2·sin²(Δλ/2)).
    # 3) Convert the central angle back to meters using Earth's mean radius.
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    sin_dlat = math.sin(dlat / 2.0)
    sin_dlon = math.sin(dlon / 2.0)
    hav = (
        sin_dlat * sin_dlat
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * sin_dlon * sin_dlon
    )
    return 2.0 * 6371000.0 * math.asin(math.sqrt(hav))


def _last_seen(coordinator: SignalKCoordinator) -> str | None:
    timestamp = coordinator.last_update_by_path.get(SK_PATH_POSITION)
    if not timestamp:
        return None
    return dt_util.as_utc(timestamp).isoformat()


def _is_stale(coordinator: SignalKCoordinator) -> bool:
    timestamp = coordinator.last_update_by_path.get(SK_PATH_POSITION)
    if not timestamp:
        return True
    age = dt_util.utcnow() - timestamp
    return age.total_seconds() > DEFAULT_STALE_SECONDS


def _path_available(discovery: SignalKDiscoveryCoordinator) -> bool:
    if not discovery.data:
        return True
    return (SK_PATH_POSITION, "geo_location") in discovery.data.path_kinds


def _position_description(discovery: SignalKDiscoveryCoordinator) -> str | None:
    if not discovery.data:
        return None
    for spec in discovery.data.entities:
        if spec.path == SK_PATH_POSITION and spec.kind == "geo_location":
            return spec.description
    return None


def _position_spec_known(discovery: SignalKDiscoveryCoordinator) -> bool:
    if not discovery.data:
        return False
    for spec in discovery.data.entities:
        if spec.path == SK_PATH_POSITION and spec.kind == "geo_location":
            return spec.spec_known
    return False


class _SignalKDiscoveryListener:
    def __init__(
        self,
        coordinator: SignalKCoordinator,
        discovery: SignalKDiscoveryCoordinator,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
        *,
        created: bool,
    ) -> None:
        self._coordinator = coordinator
        self._discovery = discovery
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._created = created

    @callback
    def handle_update(self) -> None:
        if self._created:
            return
        if not _should_create_geolocation(self._discovery):
            return
        self._created = True
        self._async_add_entities(
            [SignalKPositionGeolocation(self._coordinator, self._discovery, self._entry)]
        )
