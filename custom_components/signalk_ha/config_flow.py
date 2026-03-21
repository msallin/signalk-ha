"""Config and options flows for connecting to Signal K."""

from __future__ import annotations

import asyncio
import secrets
import ssl
from ipaddress import ip_address
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import ClientConnectorError, ClientError
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .auth import (
    AccessRequestInfo,
    AccessRequestRejected,
    AccessRequestUnsupported,
    AuthRequired,
    async_create_access_request,
    async_poll_access_request,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_BASE_URL,
    CONF_ENABLE_NOTIFICATIONS,
    CONF_ENTITY_ID_PREFIX,
    CONF_GROUPS,
    CONF_HOST,
    CONF_INSTANCE_ID,
    CONF_NOTIFICATION_IGNORE_PREFIXES,
    CONF_NOTIFICATION_PATHS,
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
    DEFAULT_ENTITY_ID_PREFIX,
    DEFAULT_GROUPS,
    DEFAULT_NOTIFICATION_IGNORE_PREFIXES,
    DEFAULT_NOTIFICATION_PATHS,
    DEFAULT_PORT,
    DEFAULT_REFRESH_INTERVAL_HOURS,
    DEFAULT_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .entity_utils import normalize_entity_id_prefix
from .identity import build_instance_id, resolve_vessel_identity
from .notifications import (
    normalize_notification_paths,
    normalize_notification_prefixes,
    paths_to_text,
)
from .rest import (
    DiscoveryInfo,
    async_fetch_discovery,
    async_fetch_vessel_self,
    normalize_base_url,
    normalize_host_input,
    normalize_server_url,
    normalize_ws_url,
)
from .schema import SCHEMA_GROUPS


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._pending_data: dict[str, Any] | None = None
        self._pending_access_token: str | None = None
        self._pending_vessel_data: dict[str, Any] | None = None
        self._access_request: AccessRequestInfo | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None
        self._auth_task: asyncio.Task[tuple[str, dict[str, Any]]] | None = None
        self._zeroconf_defaults: dict[str, Any] | None = None
        self._allow_ssl_fallback = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            host, port_override, scheme_override = normalize_host_input(host)
            port = port_override or user_input[CONF_PORT]
            use_ssl = user_input[CONF_SSL]
            verify_ssl = not user_input[CONF_VERIFY_SSL]
            entity_id_prefix = normalize_entity_id_prefix(user_input.get(CONF_ENTITY_ID_PREFIX))
            if scheme_override in ("http", "https"):
                use_ssl = scheme_override == "https"

            server_url = normalize_server_url(host, port, use_ssl)

            try:
                discovery, verify_ssl = await self._async_call_with_ssl_fallback(
                    self._async_discover_server,
                    server_url,
                    verify_ssl=verify_ssl,
                )
            except (asyncio.TimeoutError, ClientConnectorError, ClientError, OSError, ssl.SSLError):
                errors["base"] = "cannot_connect"
            except AuthRequired:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "discovery_failed"
            else:
                base_url = discovery.base_url
                ws_url = discovery.ws_url
                try:
                    vessel_data, verify_ssl = await self._async_call_with_ssl_fallback(
                        self._async_validate_connection,
                        base_url,
                        verify_ssl=verify_ssl,
                    )
                except AuthRequired:
                    try:
                        access_request, verify_ssl = await self._async_call_with_ssl_fallback(
                            self._async_start_access_request,
                            base_url,
                            host=host,
                            port=port,
                            verify_ssl=verify_ssl,
                        )
                    except AccessRequestUnsupported:
                        errors["base"] = "auth_not_supported"
                    except AuthRequired:
                        errors["base"] = "auth_required"
                    except (asyncio.TimeoutError, ClientConnectorError, ClientError, OSError):
                        errors["base"] = "cannot_connect"
                    else:
                        groups = _normalize_groups(user_input.get(CONF_GROUPS))
                        self._pending_data = {
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_SSL: use_ssl,
                            CONF_VERIFY_SSL: verify_ssl,
                            CONF_BASE_URL: base_url,
                            CONF_WS_URL: ws_url,
                            CONF_SERVER_ID: discovery.server_id,
                            CONF_SERVER_VERSION: discovery.server_version,
                            CONF_GROUPS: groups,
                            CONF_ENTITY_ID_PREFIX: entity_id_prefix,
                        }
                        self._access_request = access_request
                        self._auth_task = None
                        return await self.async_step_auth()
                except (
                    asyncio.TimeoutError,
                    ClientConnectorError,
                    ClientError,
                    OSError,
                    ssl.SSLError,
                ):
                    errors["base"] = "cannot_connect"
                except ValueError:
                    errors["base"] = "invalid_response"
                else:
                    groups = _normalize_groups(user_input.get(CONF_GROUPS))
                    return await self._async_start_notifications_step(
                        host=host,
                        port=port,
                        use_ssl=use_ssl,
                        verify_ssl=verify_ssl,
                        base_url=base_url,
                        ws_url=ws_url,
                        vessel_data=vessel_data,
                        access_token=None,
                        groups=groups,
                        entity_id_prefix=entity_id_prefix,
                        server_id=discovery.server_id,
                        server_version=discovery.server_version,
                    )

        defaults = self._zeroconf_defaults or {}
        group_options = _group_options()
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): cv.string,
                vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
                vol.Optional(CONF_SSL, default=defaults.get(CONF_SSL, DEFAULT_SSL)): cv.boolean,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=defaults.get(CONF_VERIFY_SSL, not DEFAULT_VERIFY_SSL),
                ): cv.boolean,
                vol.Optional(
                    CONF_GROUPS,
                    default=defaults.get(CONF_GROUPS, list(DEFAULT_GROUPS)),
                ): cv.multi_select(group_options),
                vol.Optional(
                    CONF_ENTITY_ID_PREFIX,
                    default=defaults.get(CONF_ENTITY_ID_PREFIX, DEFAULT_ENTITY_ID_PREFIX),
                ): cv.string,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zeroconf(self, discovery_info: "ZeroconfServiceInfo") -> FlowResult:
        host = _zeroconf_host(discovery_info)
        port = _zeroconf_attr(discovery_info, "port", DEFAULT_PORT) or DEFAULT_PORT
        service_type = _zeroconf_attr(discovery_info, "type", "") or ""
        if not _zeroconf_supported_service(service_type):
            return self.async_abort(reason="zeroconf_unsupported")
        display_name = _zeroconf_title(discovery_info)
        if display_name:
            self.context["title_placeholders"] = {"name": display_name}
        use_ssl = _zeroconf_use_ssl(service_type)
        self_id = _zeroconf_self_id(discovery_info)
        if self_id:
            # Dedupe discovery cards per vessel; HTTPS should replace HTTP when both exist.
            await self.async_set_unique_id(self_id, raise_on_progress=not use_ssl)
            if use_ssl:
                for progress in self._async_in_progress(
                    include_uninitialized=True, match_context={"unique_id": self_id}
                ):
                    if progress["flow_id"] != self.flow_id:
                        self.hass.config_entries.flow.async_abort(progress["flow_id"])
            for entry in self._async_current_entries():
                vessel_id = _normalize_self_id(entry.data.get(CONF_VESSEL_ID))
                if vessel_id == self_id:
                    return self.async_abort(reason="already_configured")

        self._zeroconf_defaults = {
            CONF_HOST: host or "",
            CONF_PORT: port,
            CONF_SSL: use_ssl,
            CONF_VERIFY_SSL: not DEFAULT_VERIFY_SSL,
            CONF_GROUPS: list(DEFAULT_GROUPS),
            CONF_ENTITY_ID_PREFIX: DEFAULT_ENTITY_ID_PREFIX,
        }
        # Zeroconf is a convenience path; if TLS fails, retry once with verification off.
        self._allow_ssl_fallback = True
        return await self.async_step_user()

    async def _async_discover_server(self, server_url: str, verify_ssl: bool) -> DiscoveryInfo:
        session = async_get_clientsession(self.hass)
        return await async_fetch_discovery(session, server_url, verify_ssl)

    async def _async_validate_connection(self, base_url: str, verify_ssl: bool) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        return await async_fetch_vessel_self(session, base_url, verify_ssl)

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if not self._pending_data or not self._access_request:
            return self.async_abort(reason="auth_cancelled")

        if user_input is not None:
            self._auth_task = None

        if not self._auth_task:
            self._auth_task = self.hass.async_create_task(
                self._async_poll_and_fetch(), eager_start=False
            )

        if not self._auth_task.done():
            approval_url = _admin_access_url(self._pending_data[CONF_BASE_URL])
            if not approval_url and self._access_request:
                approval_url = self._access_request.approval_url

            return self.async_show_progress(
                step_id="auth",
                progress_action="auth",
                description_placeholders={"approval_url": approval_url or ""},
                progress_task=self._auth_task,
            )

        return self.async_show_progress_done(next_step_id="auth_finish")

    async def async_step_auth_finish(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if not self._pending_data or not self._access_request or not self._auth_task:
            return self.async_abort(reason="auth_cancelled")

        errors: dict[str, str] = {}
        try:
            token, vessel_data = await self._auth_task
        except AccessRequestRejected:
            errors["base"] = "auth_rejected"
            try:
                self._access_request = await self._async_start_access_request(
                    self._pending_data[CONF_BASE_URL],
                    self._pending_data[CONF_VERIFY_SSL],
                    host=self._pending_data[CONF_HOST],
                    port=self._pending_data[CONF_PORT],
                )
            except AccessRequestUnsupported:
                errors["base"] = "auth_not_supported"
            except AuthRequired:
                errors["base"] = "auth_required"
            except (asyncio.TimeoutError, ClientConnectorError, ClientError, OSError):
                errors["base"] = "cannot_connect"
        except AccessRequestUnsupported:
            errors["base"] = "auth_not_supported"
        except asyncio.TimeoutError:
            errors["base"] = "auth_timeout"
        except AuthRequired:
            errors["base"] = "auth_failed"
        except (ClientConnectorError, ClientError, OSError, ssl.SSLError):
            errors["base"] = "cannot_connect"
        except ValueError:
            errors["base"] = "invalid_response"
        else:
            self._auth_task = None
            if self._reauth_entry is not None:
                return await self._async_finish_setup(
                    host=self._pending_data[CONF_HOST],
                    port=self._pending_data[CONF_PORT],
                    use_ssl=self._pending_data[CONF_SSL],
                    verify_ssl=self._pending_data[CONF_VERIFY_SSL],
                    base_url=self._pending_data[CONF_BASE_URL],
                    ws_url=self._pending_data[CONF_WS_URL],
                    vessel_data=vessel_data,
                    access_token=token,
                    groups=_normalize_groups(self._pending_data.get(CONF_GROUPS)),
                    entity_id_prefix=normalize_entity_id_prefix(
                        self._pending_data.get(CONF_ENTITY_ID_PREFIX)
                    ),
                    server_id=self._pending_data.get(CONF_SERVER_ID),
                    server_version=self._pending_data.get(CONF_SERVER_VERSION),
                )
            return await self._async_start_notifications_step(
                host=self._pending_data[CONF_HOST],
                port=self._pending_data[CONF_PORT],
                use_ssl=self._pending_data[CONF_SSL],
                verify_ssl=self._pending_data[CONF_VERIFY_SSL],
                base_url=self._pending_data[CONF_BASE_URL],
                ws_url=self._pending_data[CONF_WS_URL],
                vessel_data=vessel_data,
                access_token=token,
                groups=_normalize_groups(self._pending_data.get(CONF_GROUPS)),
                entity_id_prefix=normalize_entity_id_prefix(
                    self._pending_data.get(CONF_ENTITY_ID_PREFIX)
                ),
                server_id=self._pending_data.get(CONF_SERVER_ID),
                server_version=self._pending_data.get(CONF_SERVER_VERSION),
            )

        self._auth_task = None
        return self._show_auth_form(errors=errors)

    async def async_step_notifications(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if not self._pending_data or self._pending_vessel_data is None:
            return self.async_abort(reason="auth_cancelled")

        if user_input is not None:
            options = {
                CONF_ENABLE_NOTIFICATIONS: bool(
                    user_input.get(CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS)
                ),
                CONF_NOTIFICATION_PATHS: normalize_notification_paths(
                    user_input.get(CONF_NOTIFICATION_PATHS)
                ),
                CONF_NOTIFICATION_IGNORE_PREFIXES: normalize_notification_prefixes(
                    user_input.get(
                        CONF_NOTIFICATION_IGNORE_PREFIXES, DEFAULT_NOTIFICATION_IGNORE_PREFIXES
                    )
                ),
            }
            return await self._async_finish_setup(
                host=self._pending_data[CONF_HOST],
                port=self._pending_data[CONF_PORT],
                use_ssl=self._pending_data[CONF_SSL],
                verify_ssl=self._pending_data[CONF_VERIFY_SSL],
                base_url=self._pending_data[CONF_BASE_URL],
                ws_url=self._pending_data[CONF_WS_URL],
                vessel_data=self._pending_vessel_data,
                access_token=self._pending_access_token,
                groups=_normalize_groups(self._pending_data.get(CONF_GROUPS)),
                entity_id_prefix=normalize_entity_id_prefix(
                    self._pending_data.get(CONF_ENTITY_ID_PREFIX)
                ),
                server_id=self._pending_data.get(CONF_SERVER_ID),
                server_version=self._pending_data.get(CONF_SERVER_VERSION),
                notification_options=options,
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_NOTIFICATIONS, default=DEFAULT_ENABLE_NOTIFICATIONS
                ): cv.boolean,
                vol.Optional(
                    CONF_NOTIFICATION_PATHS,
                    default=paths_to_text(DEFAULT_NOTIFICATION_PATHS),
                ): cv.string,
                vol.Optional(
                    CONF_NOTIFICATION_IGNORE_PREFIXES,
                    default=paths_to_text(DEFAULT_NOTIFICATION_IGNORE_PREFIXES),
                ): cv.string,
            }
        )
        return self.async_show_form(step_id="notifications", data_schema=schema)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        entry_id = self.context.get("entry_id")
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if not entry:
            return self.async_abort(reason="auth_cancelled")
        self._reauth_entry = entry

        data = entry.data
        base_url = data.get(CONF_BASE_URL) or normalize_base_url(
            data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]
        )
        ws_url = data.get(CONF_WS_URL) or normalize_ws_url(
            data[CONF_HOST], data[CONF_PORT], data[CONF_SSL]
        )

        try:
            access_request = await self._async_start_access_request(
                base_url,
                data[CONF_VERIFY_SSL],
                host=data[CONF_HOST],
                port=data[CONF_PORT],
            )
        except AccessRequestUnsupported:
            return self.async_abort(reason="auth_not_supported")
        except AuthRequired:
            return self.async_abort(reason="auth_required")
        except (asyncio.TimeoutError, ClientConnectorError, ClientError, OSError):
            return self.async_abort(reason="cannot_connect")

        self._pending_data = {
            CONF_HOST: data[CONF_HOST],
            CONF_PORT: data[CONF_PORT],
            CONF_SSL: data[CONF_SSL],
            CONF_VERIFY_SSL: data[CONF_VERIFY_SSL],
            CONF_BASE_URL: base_url,
            CONF_WS_URL: ws_url,
            CONF_GROUPS: data.get(CONF_GROUPS),
            CONF_ENTITY_ID_PREFIX: data.get(CONF_ENTITY_ID_PREFIX, DEFAULT_ENTITY_ID_PREFIX),
            CONF_SERVER_ID: data.get(CONF_SERVER_ID),
            CONF_SERVER_VERSION: data.get(CONF_SERVER_VERSION),
        }
        self._access_request = access_request
        self._auth_task = None
        return await self.async_step_auth()

    async def _async_start_access_request(
        self, base_url: str, verify_ssl: bool, *, host: str, port: int
    ) -> AccessRequestInfo:
        session = async_get_clientsession(self.hass)
        client_id = _build_client_id()
        return await async_create_access_request(
            session,
            base_url,
            verify_ssl,
            client_id=client_id,
        )

    async def _async_call_with_ssl_fallback(
        self,
        func,
        *args: Any,
        verify_ssl: bool,
        **kwargs: Any,
    ):
        try:
            return await func(*args, verify_ssl, **kwargs), verify_ssl
        except ssl.SSLError:
            if not self._allow_ssl_fallback or not verify_ssl:
                raise
            # Zeroconf discovery might advertise https while the server has a self-signed cert.
            result = await func(*args, False, **kwargs)
            if self._zeroconf_defaults is not None:
                self._zeroconf_defaults[CONF_VERIFY_SSL] = True
            return result, False

    async def _async_start_notifications_step(
        self,
        *,
        host: str,
        port: int,
        use_ssl: bool,
        verify_ssl: bool,
        base_url: str,
        ws_url: str,
        vessel_data: dict[str, Any],
        access_token: str | None,
        groups: list[str],
        entity_id_prefix: str,
        server_id: str | None,
        server_version: str | None,
    ) -> FlowResult:
        self._pending_data = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SSL: use_ssl,
            CONF_VERIFY_SSL: verify_ssl,
            CONF_BASE_URL: base_url,
            CONF_WS_URL: ws_url,
            CONF_GROUPS: groups,
            CONF_ENTITY_ID_PREFIX: entity_id_prefix,
            CONF_SERVER_ID: server_id,
            CONF_SERVER_VERSION: server_version,
        }
        self._pending_vessel_data = vessel_data
        self._pending_access_token = access_token
        return await self.async_step_notifications()

    async def _async_finish_setup(
        self,
        *,
        host: str,
        port: int,
        use_ssl: bool,
        verify_ssl: bool,
        base_url: str,
        ws_url: str,
        vessel_data: dict[str, Any],
        access_token: str | None,
        groups: list[str],
        entity_id_prefix: str,
        server_id: str | None,
        server_version: str | None,
        notification_options: dict[str, Any] | None = None,
    ) -> FlowResult:
        identity = resolve_vessel_identity(vessel_data, base_url)
        instance_id = build_instance_id(base_url, identity.vessel_id)
        if self._reauth_entry is None:
            await self.async_set_unique_id(instance_id)
            self._abort_if_unique_id_configured()

        data = {
            **(self._reauth_entry.data if self._reauth_entry is not None else {}),
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_SSL: use_ssl,
            CONF_VERIFY_SSL: verify_ssl,
            CONF_BASE_URL: base_url,
            CONF_WS_URL: ws_url,
            CONF_VESSEL_ID: identity.vessel_id,
            CONF_VESSEL_NAME: identity.vessel_name,
            CONF_INSTANCE_ID: instance_id,
            CONF_SERVER_ID: server_id or "",
            CONF_SERVER_VERSION: server_version or "",
            CONF_REFRESH_INTERVAL_HOURS: DEFAULT_REFRESH_INTERVAL_HOURS,
            CONF_GROUPS: groups,
            CONF_ENTITY_ID_PREFIX: entity_id_prefix,
        }
        if access_token:
            data[CONF_ACCESS_TOKEN] = access_token
        else:
            data.pop(CONF_ACCESS_TOKEN, None)

        if self._reauth_entry is not None:
            self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(
            title=f"Signal K ({identity.vessel_name})",
            data=data,
            options=notification_options or {},
        )

    async def _async_poll_and_fetch(self) -> tuple[str, dict[str, Any]]:
        assert self._pending_data is not None
        assert self._access_request is not None
        session = async_get_clientsession(self.hass)
        token = await async_poll_access_request(
            session,
            self._pending_data[CONF_BASE_URL],
            self._pending_data[CONF_VERIFY_SSL],
            self._access_request,
        )
        vessel_data = await async_fetch_vessel_self(
            session,
            self._pending_data[CONF_BASE_URL],
            self._pending_data[CONF_VERIFY_SSL],
            token=token,
        )
        return token, vessel_data

    def _show_auth_form(self, errors: dict[str, str] | None = None) -> FlowResult:
        approval_url = None
        if self._pending_data:
            # Prefer the server admin URL so users land in the right UI for access requests.
            approval_url = _admin_access_url(self._pending_data[CONF_BASE_URL])
        if not approval_url and self._access_request:
            approval_url = self._access_request.approval_url

        return self.async_show_form(
            step_id="auth",
            data_schema=vol.Schema({}),
            errors=errors or {},
            description_placeholders={"approval_url": approval_url or ""},
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            hours = int(user_input[CONF_REFRESH_INTERVAL_HOURS])
            notifications_enabled = bool(user_input[CONF_ENABLE_NOTIFICATIONS])
            groups = _normalize_groups(user_input.get(CONF_GROUPS))
            notification_paths = normalize_notification_paths(
                user_input.get(CONF_NOTIFICATION_PATHS)
            )
            notification_prefixes = normalize_notification_prefixes(
                user_input.get(
                    CONF_NOTIFICATION_IGNORE_PREFIXES, DEFAULT_NOTIFICATION_IGNORE_PREFIXES
                )
            )
            return self.async_create_entry(
                title="",
                data={
                    CONF_REFRESH_INTERVAL_HOURS: hours,
                    CONF_ENABLE_NOTIFICATIONS: notifications_enabled,
                    CONF_NOTIFICATION_PATHS: notification_paths,
                    CONF_NOTIFICATION_IGNORE_PREFIXES: notification_prefixes,
                    CONF_GROUPS: groups,
                },
            )

        current = self._entry.options.get(
            CONF_REFRESH_INTERVAL_HOURS,
            self._entry.data.get(CONF_REFRESH_INTERVAL_HOURS, DEFAULT_REFRESH_INTERVAL_HOURS),
        )
        current_notifications_enabled = self._entry.options.get(
            CONF_ENABLE_NOTIFICATIONS, DEFAULT_ENABLE_NOTIFICATIONS
        )
        current_groups = _normalize_groups(
            self._entry.options.get(CONF_GROUPS, self._entry.data.get(CONF_GROUPS))
        )
        current_notification_paths = paths_to_text(
            self._entry.options.get(CONF_NOTIFICATION_PATHS, DEFAULT_NOTIFICATION_PATHS)
        )
        current_notification_prefixes = paths_to_text(
            self._entry.options.get(
                CONF_NOTIFICATION_IGNORE_PREFIXES, DEFAULT_NOTIFICATION_IGNORE_PREFIXES
            )
        )
        group_options = _group_options()
        schema = vol.Schema(
            {
                vol.Optional(CONF_REFRESH_INTERVAL_HOURS, default=current): vol.Coerce(int),
                vol.Optional(
                    CONF_ENABLE_NOTIFICATIONS, default=current_notifications_enabled
                ): cv.boolean,
                vol.Optional(
                    CONF_NOTIFICATION_PATHS, default=current_notification_paths
                ): cv.string,
                vol.Optional(
                    CONF_NOTIFICATION_IGNORE_PREFIXES, default=current_notification_prefixes
                ): cv.string,
                vol.Optional(CONF_GROUPS, default=current_groups): cv.multi_select(group_options),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _admin_access_url(base_url: str) -> str | None:
    if not base_url:
        return None
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "/admin/", "", "/security/access/requests"))


def _group_options() -> dict[str, str]:
    return {group: group.replace("_", " ").title() for group in _config_groups()}


def _normalize_groups(groups: Any | None) -> list[str]:
    # Normalize group selections so options stay valid across schema changes.
    if not groups:
        return list(DEFAULT_GROUPS)
    selected = [group for group in groups if isinstance(group, str)]
    allowed = set(_config_groups())
    filtered = [group for group in selected if group in allowed]
    return filtered or list(DEFAULT_GROUPS)


def _config_groups() -> tuple[str, ...]:
    return tuple(group for group in SCHEMA_GROUPS if group != "notifications")


def _build_client_id() -> str:
    token = secrets.token_hex(12)
    suffix = f"{token[:4]}-{token[4:8]}-{token[8:12]}-{token[12:]}"
    return f"homeassistant_{DOMAIN}-{suffix}"


def _zeroconf_attr(discovery_info: Any, name: str, default: Any | None = None) -> Any:
    if isinstance(discovery_info, dict):
        return discovery_info.get(name, default)
    return getattr(discovery_info, name, default)


def _zeroconf_properties(discovery_info: Any) -> dict[str, str]:
    props = _zeroconf_attr(discovery_info, "properties") or {}
    if not isinstance(props, dict):
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_value in props.items():
        key = raw_key.decode("utf-8", "ignore") if isinstance(raw_key, bytes) else str(raw_key)
        value = (
            raw_value.decode("utf-8", "ignore")
            if isinstance(raw_value, bytes)
            else ""
            if raw_value is None
            else str(raw_value)
        )
        normalized[key.lower()] = value
    return normalized


def _normalize_self_id(value: Any) -> str | None:
    # Normalize self identifiers so zeroconf discovery dedupes consistently.
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.startswith("vessels."):
        normalized = normalized[len("vessels.") :]
    lower = normalized.lower()
    if "mmsi" in lower:
        digits = "".join(ch for ch in normalized if ch.isdigit())
        if digits:
            return f"mmsi:{digits}"
        return None
    return lower


def _zeroconf_title(discovery_info: Any) -> str | None:
    props = _zeroconf_properties(discovery_info)
    name = props.get("vname") or props.get("name")
    mmsi = props.get("vmmsi") or props.get("mmsi")
    if name and mmsi:
        return f"{name} ({mmsi})"
    if name:
        return name
    self_id = props.get("self")
    if not self_id:
        return None
    normalized = self_id.strip()
    if normalized.startswith("vessels."):
        normalized = normalized[len("vessels.") :]
    digits = "".join(ch for ch in normalized if ch.isdigit())
    if digits and "mmsi" in normalized.lower():
        return f"MMSI {digits}"
    if "uuid:" in normalized:
        return f"Vessel {normalized.split('uuid:', 1)[1]}"
    return f"Vessel {normalized}"


def _zeroconf_self_id(discovery_info: Any) -> str | None:
    props = _zeroconf_properties(discovery_info)
    return _normalize_self_id(props.get("self"))


def _zeroconf_host(discovery_info: Any) -> str | None:
    host = _zeroconf_attr(discovery_info, "host")
    if not host:
        host = _zeroconf_attr(discovery_info, "hostname")
    if not host:
        addresses = _zeroconf_attr(discovery_info, "addresses") or []
        if not addresses:
            addresses = _zeroconf_attr(discovery_info, "ip_addresses") or []
        if addresses:
            try:
                host = str(ip_address(addresses[0]))
            except ValueError:
                host = None
    if not host:
        return None
    return host.rstrip(".").lower()


def _zeroconf_use_ssl(service_type: str) -> bool:
    service = service_type.lower()
    return service == "_signalk-https._tcp.local."


def _zeroconf_supported_service(service_type: str) -> bool:
    service = service_type.lower()
    return service in ("_signalk-http._tcp.local.", "_signalk-https._tcp.local.")
