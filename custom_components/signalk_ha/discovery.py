"""REST discovery of Signal K paths into entity specs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Iterable

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from .const import DEFAULT_PERIOD_MS, DEFAULT_POSITION_TOLERANCE_M, SK_PATH_POSITION
from .mapping import Conversion, angle_unit_for_path, apply_conversion, lookup_mapping
from .policy import default_policy_from_entry, path_policies_from_entry
from .schema import SCHEMA_GROUPS, lookup_schema

_RESERVED_KEYS = {
    "meta",
    "value",
    "$source",
    "timestamp",
    "values",
    "source",
    "pgn",
    "sentence",
}

_GENERIC_PREFIXES = frozenset(SCHEMA_GROUPS)

_ICON_PREFIXES: tuple[tuple[str, str], ...] = (
    ("navigation.anchor", "mdi:anchor"),
    ("navigation.course", "mdi:compass"),
    ("navigation.heading", "mdi:compass"),
    ("navigation.speed", "mdi:speedometer"),
    ("environment.wind", "mdi:weather-windy"),
    ("environment.depth", "mdi:waves"),
    ("environment.tide", "mdi:waves"),
    ("environment.water", "mdi:waves"),
    ("electrical.batteries", "mdi:battery"),
    ("electrical.solar", "mdi:solar-power"),
    ("electrical.chargers", "mdi:battery-charging"),
    ("electrical.inverters", "mdi:power-plug"),
    ("electrical.alternators", "mdi:engine"),
    ("electrical.ac", "mdi:sine-wave"),
    ("tanks.fuel", "mdi:fuel"),
    ("tanks.freshWater", "mdi:water"),
    ("tanks.blackWater", "mdi:water-alert"),
    ("tanks.wasteWater", "mdi:water-alert"),
    ("tanks.lubrication", "mdi:oil"),
    ("tanks.gas", "mdi:gas-cylinder"),
    ("tanks.ballast", "mdi:anchor"),
    ("tanks.liveWell", "mdi:fish"),
    ("tanks.baitWell", "mdi:fish"),
)

_ICON_SUFFIXES: tuple[tuple[str, str], ...] = (
    (".temperature", "mdi:thermometer"),
    (".pressure", "mdi:gauge"),
    (".voltage", "mdi:flash"),
    (".current", "mdi:current-dc"),
    (".realPower", "mdi:flash"),
    (".apparentPower", "mdi:flash"),
    (".reactivePower", "mdi:flash"),
    (".frequency", "mdi:sine-wave"),
    (".stateOfCharge", "mdi:battery"),
    (".stateOfHealth", "mdi:battery-heart"),
    (".timeRemaining", "mdi:timer-outline"),
)


@dataclass(frozen=True)
class MetadataConflict:
    path: str
    meta_units: str | None
    expected_units: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveredEntity:
    path: str
    name: str
    kind: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    conversion: Conversion | None
    tolerance: float | None
    min_update_seconds: float | None
    suggested_display_precision: int | None = None
    meta_units: str | None = None
    icon: str | None = None
    period_ms: int = DEFAULT_PERIOD_MS
    description: str | None = None
    spec_known: bool = False


@dataclass(frozen=True)
class DiscoveryResult:
    entities: list[DiscoveredEntity]
    conflicts: list[MetadataConflict]
    paths: frozenset[str] = field(init=False)
    path_kinds: frozenset[tuple[str, str]] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "paths", frozenset(spec.path for spec in self.entities))
        object.__setattr__(
            self,
            "path_kinds",
            frozenset((spec.path, spec.kind) for spec in self.entities),
        )


def discover_entities(data: dict[str, Any], scopes: Iterable[str]) -> DiscoveryResult:
    entities: list[DiscoveredEntity] = []
    conflicts: list[MetadataConflict] = []
    # Treat REST discovery as a snapshot; it is safe to re-run and merge without deleting.
    for scope in scopes:
        if scope == "notifications":
            continue
        node = data.get(scope)
        if isinstance(node, dict):
            _walk(node, scope, entities, conflicts)
    return DiscoveryResult(
        entities=_disambiguate_entities(entities),
        conflicts=conflicts,
    )


def apply_entry_policies(result: DiscoveryResult, entry: Any) -> DiscoveryResult:
    default_period_ms, default_min_update_seconds = default_policy_from_entry(entry)
    path_policies = path_policies_from_entry(entry)

    entities: list[DiscoveredEntity] = []
    for entity in result.entities:
        if entity.kind != "sensor":
            entities.append(entity)
            continue

        period_ms = default_period_ms
        if entity.min_update_seconds is not None:
            period_ms = entity.period_ms
        min_update_seconds = (
            entity.min_update_seconds
            if entity.min_update_seconds is not None
            else default_min_update_seconds
        )
        tolerance = entity.tolerance

        override = path_policies.get(entity.path)
        if override is not None:
            period_ms = override.period_ms
            min_update_seconds = override.min_update_seconds
            if override.tolerance is not None:
                tolerance = override.tolerance

        entities.append(
            replace(
                entity,
                period_ms=period_ms,
                min_update_seconds=min_update_seconds,
                tolerance=tolerance,
            )
        )

    return DiscoveryResult(entities=entities, conflicts=result.conflicts)


def _walk(
    node: dict[str, Any],
    prefix: str,
    entities: list[DiscoveredEntity],
    conflicts: list[MetadataConflict],
) -> None:
    # Only leaf values become entities; intermediate nodes remain structural.
    if "value" in node:
        _add_entity(prefix, node, entities, conflicts)

    for key, value in node.items():
        if key in _RESERVED_KEYS:
            continue
        if not isinstance(value, dict):
            continue
        _walk(value, f"{prefix}.{key}", entities, conflicts)


def _add_entity(
    path: str,
    node: dict[str, Any],
    entities: list[DiscoveredEntity],
    conflicts: list[MetadataConflict],
) -> None:
    value = node.get("value")
    meta: dict[str, Any]
    if isinstance(node.get("meta"), dict):
        meta = node["meta"]
    else:
        meta = {}
    meta_units = meta.get("units")
    schema_info = lookup_schema(path)
    schema_units = schema_info.units if schema_info else None
    schema_description = schema_info.description if schema_info else None
    spec_known = schema_info is not None

    if path == SK_PATH_POSITION:
        description = schema_description
        if description is None:
            meta_description = meta.get("description")
            description = meta_description if isinstance(meta_description, str) else None
        entities.append(
            DiscoveredEntity(
                path=path,
                name="Position",
                kind="geo_location",
                unit=None,
                device_class=None,
                state_class=None,
                conversion=None,
                tolerance=DEFAULT_POSITION_TOLERANCE_M,
                min_update_seconds=None,
                meta_units=meta_units,
                period_ms=DEFAULT_PERIOD_MS,
                description=description,
                spec_known=spec_known,
            )
        )
        return

    if isinstance(value, (dict, list)):
        return

    if path.endswith(".href"):
        return
    description = meta.get("description") if isinstance(meta, dict) else ""
    if isinstance(description, str) and "url" in description.lower():
        return
    description = description if isinstance(description, str) else None
    if schema_description:
        description = schema_description

    mapping = lookup_mapping(path)
    if mapping and meta_units and mapping.expected_units:
        if meta_units not in mapping.expected_units:
            conflicts.append(
                MetadataConflict(
                    path=path,
                    meta_units=meta_units,
                    expected_units=tuple(mapping.expected_units),
                )
            )

    name = _display_name(path, meta, mapping_name=mapping.display_name if mapping else None)
    units_hint = schema_units or meta_units
    conversion = mapping.conversion if mapping else _conversion_from_meta(path, units_hint)
    unit = mapping.unit if mapping else _unit_from_meta(path, units_hint, conversion)
    device_class = mapping.device_class if mapping else None
    state_class = mapping.state_class if mapping else None
    suggested_display_precision = _suggested_display_precision(path, device_class, conversion, unit)
    tolerance = mapping.tolerance if mapping else _tolerance_from_meta(units_hint)
    min_update_seconds = mapping.min_update_seconds if mapping else None
    icon = _icon_for_path(path, device_class)

    period_ms = (
        mapping.period_ms if mapping and mapping.period_ms is not None else DEFAULT_PERIOD_MS
    )

    entities.append(
        DiscoveredEntity(
            path=path,
            name=name,
            kind="sensor",
            unit=unit,
            device_class=device_class,
            state_class=state_class,
            conversion=conversion,
            tolerance=tolerance,
            min_update_seconds=min_update_seconds,
            suggested_display_precision=suggested_display_precision,
            meta_units=meta_units,
            icon=icon,
            period_ms=period_ms,
            description=description,
            spec_known=spec_known,
        )
    )


def _display_name(path: str, meta: dict[str, Any], *, mapping_name: str | None = None) -> str:
    if mapping_name:
        return mapping_name
    for key in ("displayName", "shortName"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _name_from_path(path)


def _name_from_path(path: str) -> str:
    parts = path.split(".")
    if not parts:
        return ""
    last = _humanize_segment(parts[-1])
    context_parts = _prefix_parts_for_name(path)
    if not context_parts:
        return last
    context = _humanize_parts(context_parts)
    if not context:
        return last
    return f"{context} {last}"


def _prefix_parts_for_name(path: str) -> list[str]:
    parts = path.split(".")
    if len(parts) < 2:
        return []
    context = [part for part in parts[:-1] if part and part not in _GENERIC_PREFIXES]
    if not context:
        return []
    if len(context) >= 2 and context[-1].isdigit():
        return [context[-2], context[-1]]
    if context[-1].isdigit():
        return [context[-1]]
    return context


def _humanize_segment(segment: str) -> str:
    if not segment:
        return ""
    spaced = "".join((" " + c if c.isupper() else c) for c in segment).strip()
    spaced = spaced.replace("_", " ")
    return spaced[:1].upper() + spaced[1:] if spaced else ""


def _humanize_parts(parts: Iterable[str]) -> str:
    return " ".join(_humanize_segment(part) for part in parts if part)


def _disambiguate_entities(entities: list[DiscoveredEntity]) -> list[DiscoveredEntity]:
    counts = Counter(entity.name for entity in entities)
    if not counts or max(counts.values()) <= 1:
        return entities
    # Prefix duplicates with humanized path segments to keep names stable and readable.
    disambiguated: list[DiscoveredEntity] = []
    for entity in entities:
        if counts[entity.name] <= 1:
            disambiguated.append(entity)
            continue
        disambiguated.append(
            replace(
                entity,
                name=_disambiguated_name(entity.path, entity.name),
            )
        )
    return disambiguated


def _disambiguated_name(path: str, base_name: str) -> str:
    prefix_parts = _prefix_parts_for_path(path)
    if not prefix_parts:
        return base_name
    prefix = _humanize_parts(prefix_parts)
    if not prefix:
        return base_name
    if base_name.lower().startswith(prefix.lower()):
        return base_name
    return f"{prefix} {base_name}"


def _prefix_parts_for_path(path: str) -> list[str]:
    parts = path.split(".")
    if len(parts) < 2:
        return []
    prefix_parts = parts[:-1]
    index: str | None = None
    for part in reversed(prefix_parts):
        if part.isdigit():
            if index is None:
                index = part
            continue
        if part in _GENERIC_PREFIXES:
            continue
        return [part, index] if index else [part]
    if prefix_parts and prefix_parts[-1].isdigit() and len(prefix_parts) >= 2:
        return [prefix_parts[-2], prefix_parts[-1]]
    return [prefix_parts[-1]] if prefix_parts else []


def _unit_from_meta(path: str, meta_units: Any, conversion: Conversion | None) -> str | None:
    if conversion == Conversion.K_TO_C:
        return "degC"
    if conversion == Conversion.PA_TO_HPA:
        return "hPa"
    if conversion == Conversion.RATIO_TO_PERCENT:
        return "%"
    if conversion == Conversion.RAD_TO_DEG:
        schema_info = lookup_schema(path)
        schema_description = schema_info.description if schema_info else None
        return angle_unit_for_path(path, schema_description)
    return str(meta_units) if isinstance(meta_units, str) and meta_units else None


def _conversion_from_meta(path: str, meta_units: Any) -> Conversion | None:
    if not isinstance(meta_units, str):
        return None
    units = meta_units.lower()
    if units == "k" and path.endswith(".temperature"):
        return Conversion.K_TO_C
    if units == "pa" and path.endswith(".pressure"):
        return Conversion.PA_TO_HPA
    if units == "ratio" and path.endswith("relativeHumidity"):
        return Conversion.RATIO_TO_PERCENT
    if units == "ratio" and path.endswith("currentLevel"):
        return Conversion.RATIO_TO_PERCENT
    if units == "rad":
        return Conversion.RAD_TO_DEG
    return None


def _tolerance_from_meta(meta_units: Any) -> float | None:
    if not isinstance(meta_units, str):
        return None
    units = meta_units.lower()
    if units in ("k", "degc", "c"):
        return 0.2
    if units in ("pa", "hpa"):
        return 0.5
    if units == "ratio":
        return 0.01
    return None


def _suggested_display_precision(
    path: str,
    device_class: SensorDeviceClass | None,
    conversion: Conversion | None,
    unit: str | None,
) -> int | None:
    unit_norm = unit.lower() if isinstance(unit, str) else ""
    leaf = path.split(".")[-1].lower() if isinstance(path, str) else ""

    if device_class == SensorDeviceClass.SPEED:
        return 1
    if unit_norm in {"kn", "knot", "kts", "m/s", "km/h"}:
        return 1
    if "speed" in leaf:
        return 1

    if device_class == getattr(SensorDeviceClass, "ANGLE", None):
        return 0
    if conversion == Conversion.RAD_TO_DEG:
        return 0
    if unit_norm.startswith("°") or unit_norm in {"deg", "degt", "degm"}:
        return 0
    return None


def _icon_for_path(path: str, device_class: SensorDeviceClass | None) -> str | None:
    if device_class is not None:
        return None
    for prefix, icon in _ICON_PREFIXES:
        if path.startswith(prefix):
            return icon
    for suffix, icon in _ICON_SUFFIXES:
        if path.endswith(suffix):
            return icon
    return None


def convert_value(value: Any, conversion: Conversion | None) -> Any:
    if conversion is None:
        return value
    if isinstance(value, (int, float)):
        return apply_conversion(float(value), conversion)
    return value
