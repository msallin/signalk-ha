"""WebSocket state machine and data coordinator for Signal K updates."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from aiohttp import ClientError, ClientSession, ClientTimeout, WSMsgType, WSServerHandshakeError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .auth import AuthRequired, SignalKAuthManager, build_auth_headers
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_GROUPS,
    CONF_HOST,
    CONF_OVERRIDE_DISCOVERED_HOST,
    CONF_PORT,
    CONF_REFRESH_INTERVAL_HOURS,
    CONF_SERVER_ID,
    CONF_SERVER_VERSION,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_VESSEL_ID,
    CONF_VESSEL_NAME,
    CONF_WS_URL,
    DEFAULT_ENABLE_NOTIFICATIONS,
    DEFAULT_FORMAT,
    DEFAULT_GROUPS,
    DEFAULT_POLICY,
    DEFAULT_REFRESH_INTERVAL_HOURS,
    DOMAIN,
    notification_event_type,
)
from .discovery import DiscoveryResult, MetadataConflict, apply_entry_policies, discover_entities
from .identity import resolve_vessel_identity
from .parser import extract_notifications, extract_sources, extract_values
from .rest import (
    async_fetch_discovery,
    async_fetch_vessel_self,
    normalize_base_url,
    normalize_server_url,
    normalize_ws_url,
    rewrite_discovery_origin,
)
from .subscription import build_subscribe_payload

_LOGGER = logging.getLogger(__name__)

_BACKOFF_MIN = 1.0
_BACKOFF_MAX = 30.0
_BACKOFF_JITTER = 1.0
_COALESCE_SECONDS = 0.5
_LOG_INTERVAL_SECONDS = 60.0
_STALE_CHECK_SECONDS = 60.0
_INACTIVITY_TIMEOUT = 45.0
_NOTIFICATION_DEDUPE_SECONDS = 5.0


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    SUBSCRIBING = "subscribing"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass(frozen=True)
class SignalKConfig:
    host: str
    port: int
    ssl: bool
    verify_ssl: bool
    base_url: str
    ws_url: str
    vessel_id: str
    vessel_name: str
    access_token: str | None = None


@dataclass
class SignalKStats:
    messages: int = 0
    parse_errors: int = 0
    reconnects: int = 0


class SignalKDiscoveryCoordinator(DataUpdateCoordinator[DiscoveryResult]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
        auth: SignalKAuthManager,
    ) -> None:
        self._entry = entry
        self._session = session
        self._auth = auth
        self._conflicts: list[MetadataConflict] = []
        self._last_refresh: datetime | None = None

        interval_hours = entry.options.get(
            CONF_REFRESH_INTERVAL_HOURS,
            entry.data.get(CONF_REFRESH_INTERVAL_HOURS, DEFAULT_REFRESH_INTERVAL_HOURS),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"Signal K Discovery {entry.entry_id}",
            update_interval=timedelta(hours=int(interval_hours)),
        )

    @property
    def conflicts(self) -> list[MetadataConflict]:
        return list(self._conflicts)

    @property
    def last_refresh(self) -> dt_util.dt | None:
        return self._last_refresh

    async def _async_update_data(self) -> DiscoveryResult:
        cfg = self._config()
        updates: dict[str, Any] = {}
        base_url = cfg.base_url
        ws_url = cfg.ws_url
        server_id = self._entry.data.get(CONF_SERVER_ID) or None
        server_version = self._entry.data.get(CONF_SERVER_VERSION) or None

        try:
            discovery = await async_fetch_discovery(
                self._session,
                normalize_server_url(cfg.host, cfg.port, cfg.ssl),
                cfg.verify_ssl,
            )
        except (AuthRequired, ClientError, OSError, ssl.SSLError, asyncio.TimeoutError) as err:
            _LOGGER.debug("Signal K discovery refresh failed: %s", err)
            discovery = None

        if discovery and self._entry.data.get(CONF_OVERRIDE_DISCOVERED_HOST):
            # Honour the user's setup-time choice to keep their entered host even
            # when the SK server reports a different one (e.g. unresolvable mDNS).
            discovery = rewrite_discovery_origin(discovery, cfg.host, cfg.port, cfg.ssl)

        if discovery:
            base_url = discovery.base_url
            ws_url = discovery.ws_url
            if base_url != self._entry.data.get(CONF_BASE_URL):
                updates[CONF_BASE_URL] = base_url
            if ws_url != self._entry.data.get(CONF_WS_URL):
                updates[CONF_WS_URL] = ws_url
            if discovery.server_id and discovery.server_id != self._entry.data.get(CONF_SERVER_ID):
                updates[CONF_SERVER_ID] = discovery.server_id
                server_id = discovery.server_id
            if discovery.server_version and discovery.server_version != self._entry.data.get(
                CONF_SERVER_VERSION
            ):
                updates[CONF_SERVER_VERSION] = discovery.server_version
                server_version = discovery.server_version
        try:
            vessel = await async_fetch_vessel_self(
                self._session, base_url, cfg.verify_ssl, cfg.access_token
            )
        except AuthRequired as exc:
            self._auth.mark_failure(str(exc))
            raise ConfigEntryAuthFailed("Signal K authentication required") from exc
        else:
            self._auth.mark_success()
        identity = resolve_vessel_identity(vessel, base_url)
        if identity.vessel_id and identity.vessel_id != cfg.vessel_id:
            _LOGGER.warning(
                "Signal K vessel identity changed from %s to %s; keeping original",
                cfg.vessel_id,
                identity.vessel_id,
            )
        if identity.vessel_name and identity.vessel_name != cfg.vessel_name:
            updates[CONF_VESSEL_NAME] = identity.vessel_name

        if updates:
            self.hass.config_entries.async_update_entry(
                self._entry, data={**self._entry.data, **updates}
            )

        self._async_update_device_registry(
            vessel_name=identity.vessel_name,
            server_id=server_id,
            server_version=server_version,
            configuration_url=base_url,
        )

        groups = self._entry.options.get(
            CONF_GROUPS, self._entry.data.get(CONF_GROUPS, DEFAULT_GROUPS)
        )
        scopes = [group for group in groups if isinstance(group, str)]
        result = apply_entry_policies(discover_entities(vessel, scopes=scopes), self._entry)
        self._conflicts = result.conflicts
        self._last_refresh = dt_util.utcnow()
        return result

    def _async_update_device_registry(
        self,
        *,
        vessel_name: str | None,
        server_id: str | None,
        server_version: str | None,
        configuration_url: str | None,
    ) -> None:
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, self._entry.entry_id)})
        if not device:
            return
        updates: dict[str, str] = {}
        if vessel_name and device.name != vessel_name:
            updates["name"] = vessel_name
        if server_id and device.model != server_id:
            updates["model"] = server_id
        if server_version and device.sw_version != server_version:
            updates["sw_version"] = server_version
        if configuration_url and device.configuration_url != configuration_url:
            updates["configuration_url"] = configuration_url
        if updates:
            registry.async_update_device(device.id, **updates)

    def _config(self) -> SignalKConfig:
        data = self._entry.data
        return SignalKConfig(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            ssl=data[CONF_SSL],
            verify_ssl=data[CONF_VERIFY_SSL],
            base_url=data.get(CONF_BASE_URL)
            or normalize_base_url(data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]),
            ws_url=data.get(CONF_WS_URL)
            or normalize_ws_url(data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]),
            vessel_id=data.get(CONF_VESSEL_ID, ""),
            vessel_name=data.get(CONF_VESSEL_NAME, "Unknown Vessel"),
            access_token=data.get(CONF_ACCESS_TOKEN),
        )

    async def async_stop(self) -> None:
        await self.async_shutdown()


class SignalKCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
        discovery: SignalKDiscoveryCoordinator,
        auth: SignalKAuthManager,
    ) -> None:
        super().__init__(hass, _LOGGER, name=f"Signal K {entry.entry_id}")
        self._entry = entry
        self._session = session
        self._discovery = discovery
        self._auth = auth
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._ws = None
        self._flush_handle: asyncio.TimerHandle | None = None
        self._log_times: dict[str, float] = {}
        self._stale_unsub: asyncio.TimerHandle | None = None
        self._reauth_started = False

        self._state = ConnectionState.DISCONNECTED
        self._last_error: str | None = None
        self._last_message = None
        self._last_update_by_path: dict[str, Any] = {}
        self._last_source_by_path: dict[str, str] = {}
        self._stats = SignalKStats()
        self._data_cache: dict[str, Any] = {}
        self._paths: list[str] = []
        self._periods: dict[str, int] = {}
        # Cache signatures per path to dedupe bursty notifications without losing state changes.
        self._notification_cache: dict[str, tuple[tuple[Any, ...], str | None, float]] = {}
        self._notification_listeners: list[Callable[[dict[str, Any]], None]] = []
        self._notification_count = 0
        self._last_notification: dict[str, Any] | None = None
        self._first_message_at = None
        self._first_notification_at = None
        self._last_backoff: float = 0.0

        self.data = {}

    @property
    def config(self) -> SignalKConfig:
        data = self._entry.data
        return SignalKConfig(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            ssl=data[CONF_SSL],
            verify_ssl=data[CONF_VERIFY_SSL],
            base_url=data.get(CONF_BASE_URL)
            or normalize_base_url(data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]),
            ws_url=data.get(CONF_WS_URL)
            or normalize_ws_url(data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]),
            vessel_id=data.get(CONF_VESSEL_ID, ""),
            vessel_name=data.get(CONF_VESSEL_NAME, "Unknown Vessel"),
            access_token=data.get(CONF_ACCESS_TOKEN),
        )

    @property
    def connection_state(self) -> str:
        return self._state.value

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_message(self):
        return self._last_message

    @property
    def reconnect_count(self) -> int:
        return self._stats.reconnects

    @property
    def counters(self) -> dict[str, int]:
        return {
            "messages": self._stats.messages,
            "parse_errors": self._stats.parse_errors,
            "reconnects": self._stats.reconnects,
        }

    @property
    def last_update_by_path(self) -> dict[str, Any]:
        return dict(self._last_update_by_path)

    @property
    def last_source_by_path(self) -> dict[str, str]:
        return dict(self._last_source_by_path)

    @property
    def last_backoff(self) -> float:
        return self._last_backoff

    @property
    def subscribed_paths(self) -> list[str]:
        return list(self._paths)

    @property
    def auth_state(self) -> str:
        return self._auth.state.value

    @property
    def auth_last_error(self) -> str | None:
        return self._auth.last_error

    @property
    def auth_last_success(self):
        return self._auth.last_success

    @property
    def auth_access_request_active(self) -> bool:
        return self._auth.access_request_active

    @property
    def auth_token_present(self) -> bool:
        return self._auth.token_present

    @property
    def notifications_enabled(self) -> bool:
        return bool(
            self._entry.options.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
        )

    @property
    def notification_count(self) -> int:
        return self._notification_count

    @property
    def last_notification(self) -> dict[str, Any] | None:
        return dict(self._last_notification) if self._last_notification else None

    @property
    def last_notification_timestamp(self):
        if not self._last_notification:
            return None
        return self._last_notification.get("received_at")

    @property
    def message_count(self) -> int:
        return self._stats.messages

    @property
    def messages_per_hour(self) -> float | None:
        if not self._first_message_at:
            return None
        elapsed = (dt_util.utcnow() - self._first_message_at).total_seconds()
        if elapsed <= 0:
            return None
        return round(self._stats.messages / (elapsed / 3600.0), 2)

    @property
    def notifications_per_hour(self) -> float | None:
        if not self._first_notification_at:
            return None
        elapsed = (dt_util.utcnow() - self._first_notification_at).total_seconds()
        if elapsed <= 0:
            return None
        return round(self._notification_count / (elapsed / 3600.0), 2)

    def async_add_notification_listener(
        self, listener: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        self._notification_listeners.append(listener)

        def _remove() -> None:
            if listener in self._notification_listeners:
                self._notification_listeners.remove(listener)

        return _remove

    async def async_start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        # Keep the WS loop off the bootstrap task graph; it is intentionally long-lived.
        if hasattr(self.hass, "async_create_background_task"):
            self._task = self.hass.async_create_background_task(
                self._run(), name=f"signalk_ha_ws_{self._entry.entry_id}"
            )
        else:
            self._task = self.hass.async_create_task(self._run())
        self._schedule_stale_checks()

    async def async_stop(self) -> None:
        self._stop_event.set()
        if self._flush_handle is not None:
            self._flush_handle.cancel()
            self._flush_handle = None
        if self._stale_unsub is not None:
            self._stale_unsub.cancel()
            self._stale_unsub = None

        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._set_state(ConnectionState.DISCONNECTED)

    async def async_update_paths(
        self, paths: list[str], periods: dict[str, int] | None = None
    ) -> None:
        cleaned = sorted({path for path in paths if isinstance(path, str)})
        periods = periods or {}
        cleaned_periods = {path: int(periods[path]) for path in cleaned if path in periods}
        if cleaned == self._paths and cleaned_periods == self._periods:
            return
        self._paths = cleaned
        self._periods = cleaned_periods
        if (
            self._ws is not None
            and not self._ws.closed
            and self._state == ConnectionState.CONNECTED
        ):
            await self._send_subscribe(self._ws)

    async def _run(self) -> None:
        backoff = _BACKOFF_MIN
        # WS loop isolates transport concerns from HA state updates and recovery logic.
        while not self._stop_event.is_set():
            cfg = self.config
            url = cfg.ws_url
            ssl_context = self._build_ssl_param(cfg)
            headers = build_auth_headers(self._auth.token)
            disconnect_reason: str | None = None

            self._set_state(ConnectionState.CONNECTING)
            try:
                _LOGGER.info("Connecting to Signal K: %s", url)
                async with self._session.ws_connect(
                    url,
                    heartbeat=30,
                    timeout=ClientTimeout(total=10),
                    ssl=ssl_context,
                    headers=headers,
                ) as ws:
                    self._ws = ws
                    backoff = _BACKOFF_MIN
                    self._last_backoff = 0.0
                    self._auth.mark_success()

                    self._set_state(ConnectionState.SUBSCRIBING)
                    await self._send_subscribe(ws)

                    self._set_state(ConnectionState.CONNECTED)

                    while not self._stop_event.is_set():  # pragma: no branch
                        try:
                            msg = await ws.receive(timeout=_INACTIVITY_TIMEOUT)
                        except asyncio.TimeoutError:
                            self._record_error("Inactivity timeout")
                            disconnect_reason = "inactivity timeout"
                            break

                        if msg.type == WSMsgType.TEXT:
                            self._handle_message(msg.data, cfg)
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSE, WSMsgType.CLOSING):
                            disconnect_reason = "websocket closed"
                            break
                        elif msg.type == WSMsgType.ERROR:  # pragma: no branch
                            err = ws.exception()
                            if err:
                                self._record_error(f"WebSocket error: {err}")
                                disconnect_reason = f"websocket error: {err}"
                            else:
                                disconnect_reason = "websocket error"
                            break

            except (asyncio.TimeoutError, ClientError, OSError) as ex:
                if isinstance(ex, WSServerHandshakeError) and ex.status in (401, 403):
                    self._handle_auth_failure(f"WebSocket auth failed ({ex.status})")
                    return
                self._record_error(f"{type(ex).__name__}: {ex}")
                _LOGGER.warning("Signal K connection error: %s", ex)
            except asyncio.CancelledError:
                return
            except Exception as ex:  # last resort
                self._record_error(f"Unexpected: {type(ex).__name__}: {ex}")
                _LOGGER.exception("Unexpected error in Signal K loop: %s", ex)
            finally:
                self._ws = None
                if self._state == ConnectionState.CONNECTED:
                    _LOGGER.info("Disconnected from Signal K")
                if (
                    disconnect_reason
                    and not self._stop_event.is_set()
                    and self._state == ConnectionState.CONNECTED
                ):
                    _LOGGER.warning(
                        "Signal K connection interrupted (%s); reconnecting", disconnect_reason
                    )

            if self._stop_event.is_set():
                break

            self._stats.reconnects += 1
            self._set_state(ConnectionState.RECONNECTING)

            # Backoff prevents tight reconnect loops on flaky networks.
            delay = min(backoff, _BACKOFF_MAX) + random.uniform(0, _BACKOFF_JITTER)
            self._last_backoff = delay
            await asyncio.sleep(delay)
            backoff = min(backoff * 2.0, _BACKOFF_MAX)

        self._set_state(ConnectionState.DISCONNECTED)

    async def _send_subscribe(self, ws) -> None:
        payload = build_subscribe_payload(
            "vessels.self",
            [{"path": path, "period": self._periods.get(path)} for path in self._paths],
            fmt=DEFAULT_FORMAT,
            policy=DEFAULT_POLICY,
        )
        _LOGGER.debug("Signal K subscribe payload: %s", payload)
        await ws.send_str(json.dumps(payload))
        _LOGGER.info("Sent subscribe for %s paths", len(self._paths))

    def _handle_message(self, text: str, cfg: SignalKConfig) -> None:
        # Keep parsing and notification routing localized to avoid churn in the main loop.
        self._stats.messages += 1
        self._last_message = dt_util.utcnow()
        if self._first_message_at is None:
            self._first_message_at = self._last_message

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            self._stats.parse_errors += 1
            self._log_rate_limited(
                logging.WARNING,
                "Signal K message parse error (invalid JSON).",
                key="parse_error",
            )
            return

        # Filter by vessel context so data from other vessels cannot pollute this entry.
        contexts = self._expected_contexts(cfg)
        changed = extract_values(obj, contexts)
        notifications = extract_notifications(obj, contexts)
        if notifications:
            # Keep notifications out of the sensor cache; they have their own event pipeline.
            if self.notifications_enabled:
                for notification in notifications:
                    self._fire_notification(notification, cfg)
            for notification in notifications:
                changed.pop(notification["path"], None)

        sources = extract_sources(obj, contexts)
        source_changed = False
        for path, source in sources.items():
            if path.startswith("notifications."):
                continue
            if self._last_source_by_path.get(path) != source:
                self._last_source_by_path[path] = source
                source_changed = True
        if not changed:
            if source_changed:
                # Source changes should still be reflected without forcing value churn.
                self._schedule_flush()
            return

        now = dt_util.utcnow()
        for path in changed:
            self._last_update_by_path[path] = now

        self._data_cache.update(changed)
        self._schedule_flush()

    def _schedule_flush(self, immediate: bool = False) -> None:
        if immediate:
            if self._flush_handle is not None:
                self._flush_handle.cancel()
                self._flush_handle = None
            # Always pass a fresh dict to HA to keep coordinator updates immutable.
            self.async_set_updated_data(dict(self._data_cache))
            return

        if self._flush_handle is not None:
            return

        # Coalesce bursts of deltas so HA only processes state updates at a steady cadence.
        self._flush_handle = self.hass.loop.call_later(_COALESCE_SECONDS, self._flush_updates)

    def _flush_updates(self) -> None:
        self._flush_handle = None
        self.async_set_updated_data(dict(self._data_cache))

    def _set_state(self, state: ConnectionState) -> None:
        if self._state == state:
            return
        previous = self._state
        self._state = state
        if state == ConnectionState.CONNECTED:
            self._last_error = None
            if previous != ConnectionState.CONNECTED:  # pragma: no branch
                _LOGGER.info("Signal K connection restored")
        elif previous == ConnectionState.CONNECTED and state in (
            ConnectionState.DISCONNECTED,
            ConnectionState.RECONNECTING,
        ):
            _LOGGER.warning("Signal K connection unavailable")
        # Health sensors reflect state transitions immediately.
        self._schedule_flush(immediate=True)

    def _record_error(self, message: str) -> None:
        self._last_error = message[:200]
        self._schedule_flush(immediate=True)

    def _handle_auth_failure(self, message: str) -> None:
        self._record_error(message)
        self._auth.mark_failure(message)
        self._set_state(ConnectionState.DISCONNECTED)
        _LOGGER.warning("Signal K authentication failed: %s", message)
        self._start_reauth()

    def _log_rate_limited(self, level: int, message: str, *, key: str) -> None:
        now = time.monotonic()
        last = self._log_times.get(key, 0.0)
        if now - last < _LOG_INTERVAL_SECONDS:
            return
        self._log_times[key] = now
        _LOGGER.log(level, message)

    def _expected_contexts(self, cfg: SignalKConfig) -> list[str]:
        contexts = ["vessels.self"]
        vessel_id = cfg.vessel_id
        if vessel_id:
            if vessel_id.startswith("vessels."):
                contexts.append(vessel_id)
            else:
                contexts.append(f"vessels.{vessel_id}")
                contexts.append(vessel_id)
        return contexts

    def _fire_notification(self, notification: dict[str, Any], cfg: SignalKConfig) -> None:
        path = notification.get("path")
        if not isinstance(path, str) or not path.startswith("notifications."):
            return
        value = notification.get("value")
        source = notification.get("source") if isinstance(notification.get("source"), str) else None
        timestamp = (
            notification.get("timestamp")
            if isinstance(notification.get("timestamp"), str)
            else None
        )

        state = None
        message = None
        method = None
        if isinstance(value, dict):
            state = value.get("state")
            message = value.get("message")
            method = value.get("method")
        if not isinstance(message, str) or not message.strip():
            if isinstance(state, str) and state.strip():
                message = f"{path} ({state})"
            else:
                message = path

        signature = self._notification_signature(value, state, message, method, source)
        now = time.monotonic()
        last = self._notification_cache.get(path)
        if last:
            last_signature, last_timestamp, last_seen = last
            if timestamp and timestamp == last_timestamp and signature == last_signature:
                return
            if (
                not timestamp
                and signature == last_signature
                and now - last_seen < _NOTIFICATION_DEDUPE_SECONDS
            ):
                return

        self._notification_cache[path] = (signature, timestamp, now)
        received_at = dt_util.utcnow()
        if self._first_notification_at is None:
            self._first_notification_at = received_at
        event_data = {
            "path": path,
            "value": value,
            "state": state,
            "message": message,
            "method": method,
            "timestamp": timestamp,
            "source": source,
            "vessel_id": cfg.vessel_id,
            "vessel_name": cfg.vessel_name,
            "entry_id": self._entry.entry_id,
            "received_at": received_at,
        }
        self._notification_count += 1
        self._last_notification = event_data
        _LOGGER.debug("Signal K notification: %s", event_data)
        if self.notifications_enabled:
            for listener in list(self._notification_listeners):
                try:
                    listener(dict(event_data))
                except Exception:  # pragma: no cover - defensive
                    _LOGGER.exception("Signal K notification listener failed")
            event_type = notification_event_type(cfg.vessel_name)
            self.hass.bus.async_fire(event_type, event_data)

    @staticmethod
    def _notification_signature(
        value: Any,
        state: Any,
        message: Any,
        method: Any,
        source: str | None,
    ) -> tuple[Any, ...]:
        if isinstance(value, (dict, list)):
            try:
                value_repr = json.dumps(value, sort_keys=True, default=str)
            except TypeError:
                value_repr = repr(value)
        else:
            value_repr = repr(value)
        return (state, message, method, source, value_repr)

    @staticmethod
    def _build_ssl_param(cfg: SignalKConfig) -> ssl.SSLContext | bool | None:
        if not cfg.ssl or cfg.verify_ssl:
            return None
        return False

    def _start_reauth(self) -> None:
        if self._reauth_started or self._stop_event.is_set():
            return
        # Avoid stacking reauth flows on repeated auth failures.
        self._reauth_started = True
        self._auth.mark_access_request_active()
        reauth_coro = self._entry.async_start_reauth(self.hass)
        if asyncio.iscoroutine(reauth_coro):
            self.hass.async_create_task(reauth_coro)

    def _schedule_stale_checks(self) -> None:
        if self._stale_unsub is not None:
            return
        self._stale_unsub = self.hass.loop.call_later(_STALE_CHECK_SECONDS, self._stale_tick)

    def _stale_tick(self) -> None:
        self._stale_unsub = None
        self._schedule_flush(immediate=True)
        if not self._stop_event.is_set():
            self._schedule_stale_checks()
