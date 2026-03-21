# Signal K (signalk_ha)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?color=%2318BCF2)](https://github.com/hacs/integration)
![GitHub Release](https://img.shields.io/github/v/release/msallin/signalk-ha?include_prereleases&sort=semver&color=%2318BCF2&link=https%3A%2F%2Fgithub.com%2Fmsallin%2Fsignalk-ha%2Freleases)

[Signal K](https://signalk.org) is an open marine data platform and standard. This integration connects it to Home Assistant, turning vessel data into native entities and automation‑ready notification events. It discovers data via REST, then updates entities via the Signal K WebSocket delta stream. Multiple instances are supported: each config entry represents one Signal K server and one vessel device.

## Installation

### HACS

To add the Signal K integration to your Home Assistant instance, use this My button:  
  
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=msallin&repository=signalk_ha&category=integration)

Ensure you have [HACS installed](https://www.hacs.xyz/docs/use/configuration/basic/) in your Home Assistant instance before clicking the button.

### Manual installation

If you prefer to install manually:

1. Download the latest release ZIP from `https://github.com/msallin/signalk-ha/releases`.
2. Extract the ZIP and copy `custom_components/signalk_ha` into your Home Assistant `config/custom_components` directory.
3. Restart Home Assistant.

## Configuration

1. Open Settings > Devices & Services > Add Integration > Signal K.
   - If Signal K is discovered via mDNS/zeroconf, Home Assistant will offer a pre-filled setup flow (`_signalk-http` and `_signalk-https`).
2. Enter parameters (see Setup parameters below).
3. Enable notifications and configure notification paths used for Event entities.
4. If the Signal K server requires authentication, Home Assistant creates an access request. Approve it in the Signal K admin UI (Security > Access Requests); Home Assistant continues automatically after approval.
5. The integration fetches vessel data and creates entities (all disabled by default).
6. Enable the entities you want in the entity registry and wait for updates.

### Setup parameters

| Parameter | Description | Default |
| --- | --- | --- |
| Host | Hostname or URL (http/https). If you include a scheme, TLS and port are inferred. | Required |
| Port | Signal K port. | 3000 |
| Use TLS (https/wss) | Enable if your Signal K uses HTTPS/WSS. | Off |
| Ignore certificate errors | Allow self-signed certificates. | Off |
| Entity ID prefix | Optional prefix added to all entity IDs (e.g. `boat` produces `sensor.boat_sog`). Leave empty for default naming. | Empty |

### Options

| Option | Description | Default |
| --- | --- | --- |
| Data groups to include | Which Signal K groups are discovered (navigation, environment, tanks, etc.). | Navigation, Environment, Tanks |
| Discovery refresh interval (hours) | How often REST discovery refreshes entity metadata. | 24 |
| Enable notifications | Subscribe to all `notifications.*` updates and publish them on the HA event bus. | On |
| Notification paths | Paths to create event entities for (one per line, empty to disable). Use `notifications.*` to expose all. | `notifications.*` |

## How it works

Signal K is broad and high‑rate, so the integration intentionally separates discovery from live updates. It discovers the full data model, creates entities (disabled by default), and then subscribes only to the enabled entity paths. This limits data churn in Home Assistant and keeps CPU usage low.

### Discovery

Discovery starts with mDNS/zeroconf (HTTP/HTTPS records only), then uses the Signal K server discovery document (`GET /signalk`) to resolve the REST and WebSocket endpoints, and finally fetches `/signalk/v1/api/vessels/self` to build the entity catalog for the selected data groups.
REST discovery runs on startup and every 24 hours (configurable in Options); missing paths are marked unavailable with `last_seen`, and entities are never deleted automatically.
Discovery is idempotent: re-runs can add new entities or refresh metadata without breaking existing entity IDs.

### Entity creation

Entities are created from discovered paths and start disabled by default so you can choose what you actually want to update in Home Assistant.
For each path, the integration first consults the Signal K schema metadata, then merges in vessel‑specific metadata from `/vessels/self`. The entity attribute `spec_known` indicates whether the path exists in the Signal K specification.
Units and icons are suggested when metadata is available, and names are made human‑readable; if duplicates exist, names are disambiguated using their path context (e.g., “Navigation Speed Over Ground” vs “Wind Speed Over Ground”).
`navigation.position` is exposed as a Geo Location entity.

### Subscriptions

WebSocket subscriptions use the discovered stream endpoint and resubscribe after reconnects.
Only enabled entity paths are subscribed using `format=delta` and `policy=ideal`. If notifications are enabled, the integration also subscribes to `notifications.*` so alerts stay reliable.
Per‑path periods are applied when available so high‑rate signals don’t overwhelm Home Assistant.

### Updates

Incoming deltas update an internal cache and are throttled before writing state to Home Assistant, reducing recorder and UI load.
The churn‑reduction pipeline has multiple layers that work together:

- Server-side throttling: subscriptions send `minPeriod` (max rate) and `period` (keepalive) so the Signal K server reduces bursts before HA sees them.
- Coordinator coalescing: updates are buffered for a short window so many deltas collapse into a single HA state update.
- Entity throttling: each entity enforces `min_update_ms` plus per‑path tolerances so tiny changes do not trigger writes.
- Staleness: if updates stop, entities are marked unavailable after `stale_seconds`.

### Notifications

When notifications are enabled, Signal K notifications (`notifications.*`) are forwarded as Home Assistant events. The event type is `signalk_<vesselname>_notification`. Notifications are also exposed as Event entities (domain `event`) so you can build automations in the UI. The Notification Paths option controls which Event entities are created.

The Home Assistant event payload includes:

- Event: `signalk_<vesselname>_notification` (example: `signalk_ona_notification`)
- Payload includes: `path`, `value`, `state`, `message`, `method`, `timestamp`, `source`, `vessel_id`, `vessel_name`, `entry_id`

The following automation creates a persistent notification in Home Assistant when an anchor alarm is raised:

```yaml
alias: Signal K Anchor Alarm
description: ""
mode: single
triggers:
  - event_type: signalk_ona_notification
    event_data:
      path: notifications.navigation.anchor
    trigger: event
conditions:
  - condition: template
    value_template: |
      {{ trigger.event.data.state in ['warn', 'alarm', 'emergency'] }}
actions:
  - action: persistent_notification.create
    metadata: {}
    data:
      message: "{{ trigger.event.data.message }}"
```

### Diagnostic sensors

Diagnostic sensors summarize connection health and message flow (disabled by default).

| Sensor | Description | Default |
| --- | --- | --- |
| Connection State | WebSocket connection state (`connected`, `connecting`, `reconnecting`, `disconnected`). | On |
| Last Error | Last recorded connection or parsing error (if any). | On |
| Reconnect Count | Number of reconnects since startup. | On |
| Last Message | Timestamp of the last received WebSocket message. | On |
| Notification Count | Number of notifications received since startup. | On |
| Last Notification | Timestamp and attributes for the last notification event. | On |
| Message Count | Total messages received since startup. | Off |
| Messages per Hour | Average messages per hour since the first message. | Off |
| Notifications per Hour | Average notifications per hour since the first notification. | Off |

## Troubleshooting

- Verify the REST URL is reachable in a browser or `curl`.
- If you use a self-signed certificate, enable "Ignore certificate errors".
- If authentication is required, approve the access request in Signal K and wait for Home Assistant to continue automatically.
- If approval times out, reopen the config flow to retry the access request.
- Use the Diagnostics panel for connection state, counters, and last update timestamps.
- Reload the integration after connection settings change.

## Removal

1. Disable the integration in Home Assistant.
2. Remove the config entry from the Integrations UI.
3. Revoke the Home Assistant access in the Signal K admin UI (Security > Devices > look for `signalk_ha`).
4. (Optional) Delete any entities you no longer want in the entity registry.
