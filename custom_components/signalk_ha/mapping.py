"""Path mappings, unit conversions and the unit fallback for unmapped Signal K fields."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfSpeed

# UnitOfLength.NAUTICAL_MILES was added in a later HA release; use the literal
# string so the integration works across a wider range of HA versions.
_NMI = "nmi"

DEVICE_CLASS_ANGLE = getattr(SensorDeviceClass, "ANGLE", None)
DEVICE_CLASS_DEPTH = getattr(SensorDeviceClass, "DEPTH", None)


class Conversion(str, Enum):
    RAD_TO_DEG = "rad_to_deg"
    MS_TO_KNOTS = "ms_to_knots"
    K_TO_C = "k_to_c"
    PA_TO_HPA = "pa_to_hpa"
    RATIO_TO_PERCENT = "ratio_to_percent"
    M_TO_NM = "m_to_nm"


@dataclass(frozen=True)
class PathMapping:
    display_name: str | None
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    conversion: Conversion | None
    expected_units: tuple[str, ...] = ()
    tolerance: float | None = None
    min_update_seconds: float | None = None
    period_ms: int | None = None


# Units where MEASUREMENT is unambiguous and the unit is already settled. Deliberately
# narrower than the schema vocabulary: `J` and `C` carry running totals (yieldToday,
# lifetimeDischarge), and `m`, `s`, `m/s`, `m3`, `ratio` and `%` are still candidates for
# conversion, which would cost every user a units_changed repair once statistics exist.
# `rad` is circular, so an arithmetic mean points the wrong way.
SETTLED_UNITS: frozenset[str] = frozenset({"A", "Hz", "K", "Pa", "V", "W"})

# Matched case-insensitively, as `_conversion_from_meta` already does for the same
# `meta.units` string.
_SETTLED_LOWER: frozenset[str] = frozenset(unit.lower() for unit in SETTLED_UNITS)

# Thresholds and setpoints share their unit with the value they bound, so the unit alone
# cannot tell them apart. They are configuration, not measurements.
_CONFIG_MARKERS: tuple[str, ...] = ("setpoint", "warn", "fault", "limit", "nominal")


def state_class_for_units(path: str, units: Any) -> SensorStateClass | None:
    """Fallback state class for a path with no explicit mapping.

    `meta.units` comes from the server and is not validated against the schema: real
    data carries values like "bool", so gate on the allowlist rather than on `units`
    being truthy.
    """
    if not isinstance(units, str) or units.lower() not in _SETTLED_LOWER:
        return None
    lowered = path.lower()
    if any(marker in lowered for marker in _CONFIG_MARKERS):
        return None
    return SensorStateClass.MEASUREMENT


def angle_unit_for_path(path: str, description: str | None = None) -> str:
    path_lower = path.lower()
    description_lower = description.lower() if isinstance(description, str) else ""

    if "compass" in path_lower or "compass" in description_lower:
        return "° C"

    if (
        "headingtrue" in path_lower
        or "bearingtrue" in path_lower
        or "bearingtracktrue" in path_lower
        or "courseovergroundtrue" in path_lower
        or "settrue" in path_lower
        or " true north" in description_lower
        or "relative to north" in description_lower
    ):
        return "° T"

    if (
        "headingmagnetic" in path_lower
        or "bearingmagnetic" in path_lower
        or "bearingtrackmagnetic" in path_lower
        or "courseovergroundmagnetic" in path_lower
        or "setmagnetic" in path_lower
        or "magnetic north" in description_lower
    ):
        return "° M"

    if "directiontrue" in path_lower:
        return "° T"

    if "directionmagnetic" in path_lower:
        return "° M"

    return "°"


_EXACT_MAPPING: dict[str, PathMapping] = {
    "navigation.speedOverGround": PathMapping(
        display_name="SOG",
        unit=UnitOfSpeed.KNOTS,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.MS_TO_KNOTS,
        expected_units=("m/s",),
        tolerance=0.5,
    ),
    "navigation.speedThroughWater": PathMapping(
        display_name="STW",
        unit=UnitOfSpeed.KNOTS,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.MS_TO_KNOTS,
        expected_units=("m/s",),
        tolerance=0.2,
    ),
    "navigation.courseOverGroundTrue": PathMapping(
        display_name="COG",
        unit=angle_unit_for_path("navigation.courseOverGroundTrue"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "navigation.courseOverGroundMagnetic": PathMapping(
        display_name="COG Magnetic",
        unit=angle_unit_for_path("navigation.courseOverGroundMagnetic"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "navigation.headingTrue": PathMapping(
        display_name="HDT",
        unit=angle_unit_for_path("navigation.headingTrue"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "navigation.headingMagnetic": PathMapping(
        display_name="HDM",
        unit=angle_unit_for_path(
            "navigation.headingMagnetic",
            "Current magnetic heading of the vessel, equals headingCompass"
            " adjusted for magneticDeviation",
        ),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "environment.depth.belowTransducer": PathMapping(
        display_name="DBT",
        unit=UnitOfLength.METERS,
        device_class=DEVICE_CLASS_DEPTH,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=None,
        expected_units=("m",),
        tolerance=0.5,
    ),
    "environment.depth.belowSurface": PathMapping(
        display_name="DBS",
        unit=UnitOfLength.METERS,
        device_class=DEVICE_CLASS_DEPTH,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=None,
        expected_units=("m",),
        tolerance=0.5,
    ),
    "environment.depth.belowKeel": PathMapping(
        display_name="DBK",
        unit=UnitOfLength.METERS,
        device_class=DEVICE_CLASS_DEPTH,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=None,
        expected_units=("m",),
        tolerance=0.5,
    ),
    "environment.wind.speedApparent": PathMapping(
        display_name="AWS",
        unit=UnitOfSpeed.KNOTS,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.MS_TO_KNOTS,
        expected_units=("m/s",),
        tolerance=0.5,
    ),
    "environment.wind.speedTrue": PathMapping(
        display_name="TWS",
        unit=UnitOfSpeed.KNOTS,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.MS_TO_KNOTS,
        expected_units=("m/s",),
        tolerance=0.5,
    ),
    "environment.wind.speedOverGround": PathMapping(
        display_name="GWS",
        unit=UnitOfSpeed.KNOTS,
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.MS_TO_KNOTS,
        expected_units=("m/s",),
        tolerance=0.5,
    ),
    "environment.wind.angleApparent": PathMapping(
        display_name="AWA",
        unit=angle_unit_for_path("environment.wind.angleApparent"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "environment.wind.angleTrueWater": PathMapping(
        display_name="TWA",
        unit=angle_unit_for_path("environment.wind.angleTrueWater"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "environment.wind.angleTrueGround": PathMapping(
        display_name="TWA Ground",
        unit=angle_unit_for_path("environment.wind.angleTrueGround"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "environment.wind.directionTrue": PathMapping(
        display_name="GWD",
        unit=angle_unit_for_path("environment.wind.directionTrue"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=None,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "environment.wind.directionMagnetic": PathMapping(
        display_name="GWD Magnetic",
        unit=angle_unit_for_path("environment.wind.directionMagnetic"),
        device_class=DEVICE_CLASS_ANGLE,
        state_class=None,
        conversion=Conversion.RAD_TO_DEG,
        expected_units=("rad",),
        tolerance=0.1,
    ),
    "tanks.freshWater.0.currentLevel": PathMapping(
        display_name=None,
        unit=PERCENTAGE,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        conversion=Conversion.RATIO_TO_PERCENT,
        expected_units=("ratio",),
        tolerance=0.5,
    ),
    # Navigation log distances: Signal K uses metres; expose as nautical miles for
    # practical readability on a chart plotter or sailing dashboard.
    "navigation.log": PathMapping(
        display_name="Log",
        unit=_NMI,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        conversion=Conversion.M_TO_NM,
        expected_units=("m",),
        tolerance=0.01,
    ),
    "navigation.trip.log": PathMapping(
        display_name="Trip Log",
        unit=_NMI,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        conversion=Conversion.M_TO_NM,
        expected_units=("m",),
        tolerance=0.01,
    ),
}


def lookup_mapping(path: str) -> PathMapping | None:
    return _EXACT_MAPPING.get(path)


def expected_units(mapping: PathMapping | None) -> Iterable[str]:
    return mapping.expected_units if mapping else ()


def apply_conversion(value: float, conversion: Conversion | None) -> float:
    if conversion == Conversion.RAD_TO_DEG:
        return value * 57.29577951308232
    if conversion == Conversion.MS_TO_KNOTS:
        return value * 1.9438444924406
    if conversion == Conversion.K_TO_C:
        return value - 273.15
    if conversion == Conversion.PA_TO_HPA:
        return value / 100.0
    if conversion == Conversion.RATIO_TO_PERCENT:
        return value * 100.0
    if conversion == Conversion.M_TO_NM:
        return value * 0.0005399568034557236
    return value
