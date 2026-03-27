# Changelog

## 2.1.0

### Features

- Add configurable default subscription period and minimum update interval in integration options.
- Add per-path policy overrides in options for `period_ms`, `min_update_seconds`, and `tolerance`.
- Add `signalk_ha.set_path_policy` service with full schema and Developer Tools guidance.

## 2.0.0

### Breaking Changes

- Improved marine naming conventions and angle unit handling may rename existing entities. Review your entity IDs and automations after upgrading.

### Features

- Add optional entity ID prefix in config flow to namespace entity IDs (e.g. `boat` produces `sensor.boat_sog`).
- Default display precision for angle and speed sensors.
- Improved marine naming with proper nautical abbreviations (HDG, HDM, COG, SOG, etc.).

### Bug Fixes

- Classify angle units with schema-aware true/magnetic/compass rules.
- Preserve default entity IDs when the prefix is left empty.

## 1.2.0

### Improvements

- Add possibility to ignore specific event entities from being created.
- Reduce data churn by improving tolerance values and calculations.

### Bugfixes

- Handle case when a access request is denied.

### Miscellaneous

## 1.1.0

### Improvements

- Reduce data churn by improving tolerance values and calculations.
- Refresh doesn't only update entities but also device metadata (server version and user editable values).

### Bug Fixes

- Integration didn't handle certain edge cases after token refresh automatically.
- Already added devices were being displayed under "Discovered" in the UI.

### Miscellaneous

- Push test coverage to 100%.
- Add comments and documentation for clarity throughout the codebase.

## 1.0.0

- Initial public release.
