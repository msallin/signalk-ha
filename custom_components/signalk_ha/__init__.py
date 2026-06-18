"""Integration entrypoints and lifecycle wiring for Signal K."""

from __future__ import annotations

import asyncio
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from homeassistant.helpers.typing import ConfigType

from .auth import SignalKAuthManager
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_GROUPS,
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
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_GROUPS,
    DEFAULT_PERIOD_MS,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL_HOURS,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_CLEAR_PATH_POLICY,
    SERVICE_SET_PATH_POLICY,
    SK_PATH_NOTIFICATIONS,
)
from .coordinator import SignalKCoordinator, SignalKDiscoveryCoordinator
from .entity_utils import path_from_unique_id
from .identity import build_instance_id
from .policy import (
    default_policy_from_entry,
    merge_path_policy,
    path_policies_from_entry,
    remove_path_policy,
)
from .rest import normalize_base_url, normalize_ws_url
from .runtime import SignalKRuntimeData

PLATFORMS: list[str] = ["sensor", "geo_location", "event"]
_LOGGER = logging.getLogger(__name__)

_DISCOVERY_RETRY_DELAYS = [5, 10, 15]


async def _async_refresh_with_retry(discovery: SignalKDiscoveryCoordinator) -> None:
    try:
        await discovery.async_config_entry_first_refresh()
        return
    except Exception as err:
        _LOGGER.warning("Signal K discovery failed on first attempt: %s", err)

    for attempt, delay in enumerate(_DISCOVERY_RETRY_DELAYS, start=1):
        await asyncio.sleep(delay)
        try:
            await discovery.async_refresh()
            if discovery.last_update_success:
                _LOGGER.info("Signal K discovery succeeded on retry %d", attempt)
                return
        except Exception as err:
            _LOGGER.warning(
                "Signal K discovery failed on retry %d: %s", attempt, err
            )

    _LOGGER.warning(
        "Signal K discovery unavailable after %d retries; "
        "entities will use registry fallback",
        len(_DISCOVERY_RETRY_DELAYS),
    )


_SET_PATH_POLICY_SCHEMA = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Required("path"): cv.string,
        vol.Optional("period_ms"): vol.All(vol.Coerce(int), vol.Range(min=1000)),
        vol.Optional("min_update_seconds"): vol.All(vol.Coerce(float), vol.Range(min=0.5)),
        vol.Optional("tolerance"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    }
)

_CLEAR_PATH_POLICY_SCHEMA = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Required("path"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # Services resolve their target entry dynamically, so register them once at the
    # integration level instead of per config entry.
    _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    # Keep runtime state centralized so reloads can swap components predictably.
    auth = SignalKAuthManager(entry.data.get(CONF_ACCESS_TOKEN))
    discovery = SignalKDiscoveryCoordinator(hass, entry, session, auth)
    coordinator = SignalKCoordinator(hass, entry, session, discovery, auth)

    entry.runtime_data = SignalKRuntimeData(
        coordinator=coordinator,
        discovery=discovery,
        auth=auth,
    )

    # Run an initial discovery synchronously to seed entities and subscription periods.
    # Retry transient failures so a slow SK server doesn't force the registry fallback.
    await _async_refresh_with_retry(discovery)

    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_update_subscriptions(hass, entry)
    await coordinator.async_start()

    @callback
    def _registry_updated(event):
        entity_id = event.data.get("entity_id")
        action = event.data.get("action")
        if not entity_id or action not in ("update", "create", "remove"):
            return
        if action == "update":
            changes = event.data.get("changes", {})
            if not any(key in changes for key in ("disabled_by", "disabled")):
                return
        registry = er.async_get(hass)
        entry_data = registry.async_get(entity_id)
        if entry_data and entry_data.config_entry_id == entry.entry_id:
            hass.async_create_task(_async_update_subscriptions(hass, entry))

    entry.async_on_unload(hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, _registry_updated))
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.version >= 2:
        return True

    data = {**entry.data}
    host = data.get(CONF_HOST, "")
    port = data.get(CONF_PORT, DEFAULT_PORT)
    use_ssl = data.get(CONF_SSL, DEFAULT_SSL)

    if host:
        data.setdefault(CONF_BASE_URL, normalize_base_url(host, port, use_ssl))
        data.setdefault(CONF_WS_URL, normalize_ws_url(host, port, use_ssl))

    data.setdefault(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    data.setdefault(CONF_VESSEL_ID, "")
    data.setdefault(CONF_VESSEL_NAME, "Unknown Vessel")
    data.setdefault(CONF_REFRESH_INTERVAL_HOURS, DEFAULT_REFRESH_INTERVAL_HOURS)
    data.setdefault(CONF_GROUPS, list(DEFAULT_GROUPS))

    if CONF_INSTANCE_ID not in data:
        base_url = data.get(CONF_BASE_URL, host)
        vessel_id = data.get(CONF_VESSEL_ID, "")
        data[CONF_INSTANCE_ID] = build_instance_id(base_url, vessel_id)

    hass.config_entries.async_update_entry(entry, data=data, version=2)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    runtime = entry.runtime_data
    if runtime:
        await runtime.coordinator.async_stop()
        await runtime.discovery.async_stop()
    entry.runtime_data = None

    return unload_ok


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_PATH_POLICY):
        return

    def _resolve_entry(entry_id: str) -> ConfigEntry:
        entry = hass.config_entries.async_get_entry(entry_id)
        if not entry or entry.domain != DOMAIN:
            raise ServiceValidationError(f"Unknown Signal K entry_id: {entry_id}")
        return entry

    async def _async_set_path_policy(call: ServiceCall) -> None:
        entry = _resolve_entry(call.data["entry_id"])
        current = entry.options.get(CONF_PATH_POLICIES)
        existing = current if isinstance(current, dict) else None
        merged = merge_path_policy(
            existing,
            path=call.data["path"],
            period_ms=call.data.get("period_ms"),
            min_update_seconds=call.data.get("min_update_seconds"),
            tolerance=call.data.get("tolerance"),
        )
        _async_apply_path_policies(hass, entry, merged)

    async def _async_clear_path_policy(call: ServiceCall) -> None:
        entry = _resolve_entry(call.data["entry_id"])
        current = entry.options.get(CONF_PATH_POLICIES)
        existing = current if isinstance(current, dict) else None
        merged = remove_path_policy(existing, path=call.data["path"])
        _async_apply_path_policies(hass, entry, merged)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PATH_POLICY,
        _async_set_path_policy,
        schema=_SET_PATH_POLICY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_PATH_POLICY,
        _async_clear_path_policy,
        schema=_CLEAR_PATH_POLICY_SCHEMA,
    )


@callback
def _async_apply_path_policies(hass: HomeAssistant, entry: ConfigEntry, policies: dict) -> None:
    # Persist the change and let the entry's update listener perform the reload.
    # Reloading here too would reload the entry twice for a single options change.
    current = entry.options.get(CONF_PATH_POLICIES)
    current_dict = current if isinstance(current, dict) else {}
    if policies == current_dict:
        return
    new_options = {**entry.options, CONF_PATH_POLICIES: policies}
    hass.config_entries.async_update_entry(entry, options=new_options)


async def _async_update_subscriptions(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime = entry.runtime_data
    if not runtime:
        return
    # Derive subscriptions from enabled entities to keep WS traffic aligned with user intent.
    # This prevents background data churn for entities the user has explicitly disabled.
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, entry.entry_id)
    paths: list[str] = []
    periods: dict[str, int] = {}
    discovery = runtime.discovery
    default_period_ms, _ = default_policy_from_entry(entry)
    path_policies = path_policies_from_entry(entry)
    discovery_periods: dict[str, int] = {}
    if discovery and discovery.data:
        discovery_periods = {
            spec.path: spec.period_ms for spec in discovery.data.entities if spec.period_ms
        }
    for registry_entry in entries:
        if registry_entry.disabled:
            continue
        if registry_entry.domain == "event":
            continue
        path = path_from_unique_id(registry_entry.unique_id)
        if path:
            paths.append(path)
            override = path_policies.get(path)
            if override is not None:
                periods[path] = override.period_ms
            else:
                periods[path] = discovery_periods.get(path, default_period_ms)
    if entry.options.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS):
        if SK_PATH_NOTIFICATIONS not in paths:
            paths.append(SK_PATH_NOTIFICATIONS)
            periods[SK_PATH_NOTIFICATIONS] = DEFAULT_PERIOD_MS
    await runtime.coordinator.async_update_paths(paths, periods)
