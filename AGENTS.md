# AGENTS.md

## Mission

Build a production-grade Home Assistant custom integration (HACS) that ingests Signal K data and exposes it as high-quality Home Assistant entities with minimal user effort and maximal reliability.

Primary goals:
- Correct and complete use of the Signal K data model and delta protocol
- REST-based discovery + WebSocket-based updates
- First-class Home Assistant entity modeling, lifecycle management, and diagnostics
- Reliability and self-healing suitable for real sailors on unreliable networks
- Support multiple Signal K instances, where each config entry represents exactly one vessel

Non-negotiables:
- Correct Signal K WebSocket subscription protocol handling (handshake, subscribe, resubscribe).
- Self-healing networking (robust reconnect, backoff, lifecycle safety, clean unload).
- Diagnostics that make failures obvious and fixable without “IT time”.
- Configuration that is easy for sailors: defaults, presets, copy/paste friendly, clear validation.
- One connection per config entry, shared by all entities.
- Correctness, stability, and debuggability always beat feature breadth.

Sailors do not want to debug. Reliability beats features.

---

## Context: Current State

Integration `signalk_ha` is in active use with a production-oriented structure:

- `custom_components/signalk_ha/`
  - `__init__.py` (setup, unload, subscription refresh)
  - `auth.py` (access request flow)
  - `config_flow.py` (discovery + auth + options)
  - `coordinator.py` (WS loop + discovery coordinator + notifications)
  - `rest.py` (server discovery + REST fetch helpers)
  - `discovery.py` (entity discovery, metadata, icons)
  - `schema.py` (Signal K schema metadata, v1.7.1)
  - `mapping.py` (explicit path mappings + conversions)
  - `parser.py` (delta parsing + notifications extraction)
  - `subscription.py` (build subscribe payloads)
  - `sensor.py` (sensor + health entities)
  - `geo_location.py` (navigation.position)
  - `event.py` (notification event entities)
  - `notifications.py` (normalize notification path selection)
  - `diagnostics.py`

Core technical choices so far:
- Signal K server discovery via `GET {server_url}/signalk` (use `endpoints.v1`).
- REST discovery via `/signalk/v1/api/vessels/self`.
- WebSocket endpoint: `/signalk/v1/stream?subscribe=none` with explicit subscribe payloads.
- Delta parsing into a latest-value cache, coalesced into HA updates.
- Notifications pipeline: HA bus event (`signalk_ha_notification`) plus optional Event entities.
- Schema-driven discovery with explicit overrides in `mapping.py`.

---

## Architectural Principles (Authoritative)

- REST API is used for discovery and metadata refresh.
- WebSocket (Signal K delta protocol) is used for live updates.
- REST and WebSocket concerns must be cleanly separated.
- Entity discovery is idempotent and repeatable.
- Transport frequency and HA state update frequency are decoupled.
- Failures are expected and must be handled gracefully.
- Never delete entities automatically.

---

## Config Flow (Initial Setup)

### Connection Parameters

Remove the old path-selection page entirely.

Collect:
- host
- port
- tls (ws / wss)
- verify TLS certificate (yes/no)

Normalize:
- scheme
- default ports
- trailing slashes
- hostname casing

Derived base URLs:
- REST: from server discovery (`endpoints.v1["signalk-http"]`)
- WS: from server discovery (`endpoints.v1["signalk-ws"]`)

Validation:
- Verify Signal K discovery endpoint reachable.
- Fetch `/vessels/self`.
- Fail fast on network, TLS, authentication, or protocol errors.

Notes:
- Do not append trailing slash to WS URL unless required.
- Store server_id/server_version from discovery in the config entry.

---

## Vessel Identity and Device Registry

### Vessel Resolution

Always use:
- `GET /signalk/v1/api/vessels/self`

Do not assume MMSI is present or stable.

Persist a stable vessel identifier with priority:
1. MMSI if present and valid
2. Stable vessel URN/key if exposed
3. Fallback: hash of normalized server URL + vessel name (last resort)

Persist separately:
- vessel identifier (identity)
- vessel name (display only)

### Device Registry

- Exactly one HA device per config entry (one vessel).
- Store:
  - vessel name (display)
  - vessel identifier (identity)
  - normalized Signal K base URL or instance key

Rules:
- Vessel name is display-only.
- Entity IDs and unique_ids must not change if vessel name changes.
- Never encode vessel name into entity_id.

### unique_id Format

Preferred:
signalk:<config_entry_id>:<full_signalk_path>


Alternative (only if vessel_id is guaranteed stable):
signalk:<vessel_id>:<full_signalk_path>

## Discovery via REST

### Source and Frequency

- Use full `/vessels/self` data model.
- Discovery runs:
  - on startup
  - on configurable interval (default 24h)

Discovery failures must never remove or unload existing entities.

### Scope (Default)

- environment
- tanks
- navigation

### Entity Creation Rules

Create entities only for:
- leaf nodes with values
- explicitly supported composite types

Never create entities for:
- notifications.*
- resources
- validation
- server/internal/debug branches
- nodes with meta only and no value

All entities are created as `disabled_by_default`.

Icons:
- Set default icons only when no device_class icon applies.
- Use prefix/suffix icon hints in `discovery.py`; avoid overriding HA defaults.

---

## Metadata and Mapping

- Use Signal K metadata opportunistically.
- Be conservative:
  - assign `device_class` and `state_class` only when confident
  - otherwise fall back to plain sensors
- Maintain an explicit mapping table for well-known Signal K paths.

Metadata updates:
- Updating name/icon is allowed.
- Never change `unit_of_measurement`, `device_class`, or `state_class` after creation unless fixing a bug with migration code.
- Mapping table overrides server meta if conflicting; record conflicts in diagnostics.

---

## Unit Normalization Policy

### Core Rule
Normalize only when confident. Never be “confidently wrong”.

### Explicitly Mapped Paths

For mapped paths, normalize into canonical HA units:

- angles: degrees
- speed: knots
- depth/distance: meters
- temperature: degC
- pressure: hPa
- electrical: V / A / W
- tank level: percent (ratio) or liters (absolute)

Once chosen, units must remain stable forever.

### Unmapped Paths

- Do not normalize.
- Expose raw values.
- Set units only if clearly provided.
- Do not set `device_class` or `state_class`.

---

## Composite Values

Explicit handling:
- Position -> `geo_location`
- Wind -> speed sensor + angle sensor
- Depth -> sensor
- Heading / COG / SOG -> separate sensors

Do not collapse composite objects into attribute-only sensors.

---

## Update Frequency, Backpressure, and Recorder Safety

- WebSocket updates may arrive at high frequency.
- HA state updates must be throttled.

Rules:
- Update entity only if:
  - value changed beyond tolerance
  - minimum update interval elapsed

Defaults:
- global minimum update interval
- optional per-sensor-class defaults

Explicit float tolerances must be defined and tested.

Recorder safety:
- Set `state_class` only when semantics are guaranteed.
- If unsure, do not set it.

---

## Availability and Staleness

- Treat all timestamps as UTC.
- If missing or invalid, use receive-time timestamp.

Staleness:
- Track last update per entity.
- If stale beyond threshold, mark unavailable.
- Distinguish unavailable from valid zero values.

---

## Entity Lifecycle

- Missing path -> entity unavailable + `last_seen`
- Never delete entities automatically.
- Optional manual cleanup service only.

---

## WebSocket Protocol and Reliability

### Protocol Constraints (Critical)

- `subscribe=none` requires explicit subscribe payload.
- Subscription is not persistent across reconnects.
- Ignore non-delta frames safely.
- Handle multiple updates/values per frame.
- Context may be `vessels.self` or resolved vessel ID.

### Subscription Model

- Subscribe only to enabled entity paths.
- Maintain subscription set.
- On reconnect: resubscribe all.
- Prefer path-scoped subscriptions.
- Periods are per-path and default to `DEFAULT_PERIOD_MS` (5000 ms).

---

## Reliability and Self-Healing

- Separate failure domains:
  - REST failure must not unload entities.
  - WS failure must not unload entities.

WebSocket robustness:
- explicit connection state machine
- exponential backoff with jitter
- inactivity watchdog
- clean unload and reload

Logging:
- INFO: connect/disconnect/resubscribe
- WARNING: repeated failures
- DEBUG: delta parsing (optional, rate-limited)

---

## Reload Semantics

Reload must:
- stop WS cleanly
- preserve entity registry
- rerun discovery
- resubscribe enabled entities

Reload must be idempotent.

---

## Diagnostics (Must-Have)

Implement HA diagnostics endpoint exposing:
- normalized REST/WS URLs (redacted)
- vessel id + name
- server_id + server_version
- last REST refresh
- WS connection state
- subscribed path count
- last delta timestamp
- reconnect/backoff counters
- metadata conflicts
- notification counters + last notification

Diagnostics must allow debugging without SSH.

Optional:
- persistent notification on repeated failures.

---

## Forward Planning (Architecture Must Allow)

### Authentication (Current)
- Access request flow exists (approve in Signal K admin UI).
- REST/WS clients accept tokens; redact in diagnostics.

### Notifications (Current)
- Treat `notifications.*` as a separate pipeline.
- No sensors for notifications.
- Emit HA bus events and optional Event entities.
- Event entities are opt-in via `notification_paths` (one per line).
- `notifications.*` in options means "allow all".

---

## Refactoring for Testability (Mandatory)

Introduce pure functions (no HA, no aiohttp):

- `parser.py`
  - `parse_delta_text(...)`
  - `extract_values(...)`
- `subscription.py`
  - `build_subscribe_payload(...)`

Coordinator must call these functions.

---

## Testing Requirements (Mandatory)

### Unit Tests
- Delta parsing (invalid JSON, multiple updates, nulls, context mismatch)
- Subscription payload building
- Config parsing helpers
- Update throttling and tolerance logic
- Staleness transitions

### HA Harness Tests
- Config flow creation + uniqueness
- Options flow updates
- Entity state updates via coordinator
- Availability toggling
- Event entity updates from notifications

Snapshot tests must protect discovery behavior.

---

## CI and Quality Gates

- ruff + black (+ mypy optional)
- GitHub Actions running tests and lint
- Coverage for parsing, subscription, config flow

---

## Non-Goals (v1)

- No bidirectional control (no PUT/POST to Signal K)
- No full Signal K tree mirroring
- No notification binary_sensors (events only)

---

## Design Hints (Repo Structure)

- REST discovery + schema metadata live in `rest.py`, `schema.py`, `discovery.py`.
- Explicit conversions and tolerances live in `mapping.py`; do not add ad-hoc conversions elsewhere.
- WS loop + state machine live in `coordinator.py`; keep it single-connection per config entry.
- Notifications: parse in `parser.py`, dispatch in `coordinator.py`, surface UI in `event.py`.
- Options flow owns user-configurable scopes (groups + notification paths).
- Keep new logic testable via pure helpers in `parser.py`, `subscription.py`, `notifications.py`.

## Code Commenting Guideline (Intent-Focused)

- Add concise, high-quality comments that explain *why* a decision exists or what constraint it protects.
- Prefer module-level and lifecycle-boundary comments (setup, discovery, subscription, throttling, auth, notifications, diagnostics).
- Avoid narrating obvious code; comment only where it reduces future decision ambiguity.

---

## Definition of Done

- Installable via HACS.
- Setup via UI, sensors update within 30s.
- Survives Signal K restart or WiFi drop without user action.
- Health and diagnostics visible in HA UI.
- Unit tests cover core logic.
- Logs are actionable and rate-limited.

Correctness, stability, and debuggability outweigh completeness.
