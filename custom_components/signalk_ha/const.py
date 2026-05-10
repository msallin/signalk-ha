"""Shared constants and defaults for the Signal K integration."""

DOMAIN = "signalk_ha"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SSL = "ssl"
CONF_VERIFY_SSL = "verify_ssl"
CONF_BASE_URL = "base_url"
CONF_WS_URL = "ws_url"
CONF_VESSEL_ID = "vessel_id"
CONF_VESSEL_NAME = "vessel_name"
CONF_INSTANCE_ID = "instance_id"
CONF_REFRESH_INTERVAL_HOURS = "refresh_interval_hours"
CONF_ACCESS_TOKEN = "access_token"
CONF_ENABLE_NOTIFICATIONS = "enable_notifications"
CONF_NOTIFICATION_PATHS = "notification_paths"
CONF_NOTIFICATION_IGNORE_PREFIXES = "notification_ignore_prefixes"
CONF_GROUPS = "groups"
CONF_SERVER_ID = "server_id"
CONF_SERVER_VERSION = "server_version"
CONF_ENTITY_ID_PREFIX = "entity_id_prefix"
CONF_OVERRIDE_DISCOVERED_HOST = "override_discovered_host"

DEFAULT_PORT = 3000
DEFAULT_SSL = False
DEFAULT_VERIFY_SSL = True
DEFAULT_REFRESH_INTERVAL_HOURS = 24
DEFAULT_ENABLE_NOTIFICATIONS = True
DEFAULT_NOTIFICATION_PATHS: tuple[str, ...] = ("notifications.*",)
DEFAULT_NOTIFICATION_IGNORE_PREFIXES: tuple[str, ...] = ("notifications.security.",)
DEFAULT_GROUPS = ("navigation", "environment", "tanks")
DEFAULT_ENTITY_ID_PREFIX = ""

DEFAULT_PERIOD_MS = 5000
DEFAULT_FORMAT = "delta"
DEFAULT_POLICY = "ideal"

# Minimum write cadence guard in Home Assistant (milliseconds); we cannot rely on
# Signal K subscription periods alone to protect the recorder/UI from bursts.
DEFAULT_MIN_UPDATE_MS = 5000
# Force a periodic write even when values stay within tolerance to keep HA fresh.
DEFAULT_MAX_IDLE_WRITE_SECONDS = 300.0
DEFAULT_STALE_SECONDS = 600.0
# Position tolerance in meters.
DEFAULT_POSITION_TOLERANCE_M = 5.0

SK_PATH_POSITION = "navigation.position"
SK_PATH_NOTIFICATIONS = "notifications.*"

EVENT_SIGNAL_K_NOTIFICATION_PREFIX = "signalk"
EVENT_SIGNAL_K_NOTIFICATION_SUFFIX = "notification"

HEALTH_SENSOR_CONNECTION_STATE = "connection_state"
HEALTH_SENSOR_LAST_MESSAGE = "last_message"
HEALTH_SENSOR_RECONNECT_COUNT = "reconnect_count"
HEALTH_SENSOR_LAST_ERROR = "last_error"
HEALTH_SENSOR_NOTIFICATION_COUNT = "notification_count"
HEALTH_SENSOR_LAST_NOTIFICATION = "last_notification"
HEALTH_SENSOR_MESSAGE_COUNT = "message_count"
HEALTH_SENSOR_MESSAGES_PER_HOUR = "messages_per_hour"
HEALTH_SENSOR_NOTIFICATIONS_PER_HOUR = "notifications_per_hour"

NOTIFICATION_EVENT_TYPES = (
    "nominal",
    "normal",
    "alert",
    "warn",
    "alarm",
    "emergency",
    "unknown",
)


def notification_event_type(vessel_name: str | None) -> str:
    from homeassistant.util import slugify

    slug = slugify(vessel_name or "vessel") or "vessel"
    return f"{EVENT_SIGNAL_K_NOTIFICATION_PREFIX}_{slug}_{EVENT_SIGNAL_K_NOTIFICATION_SUFFIX}"
