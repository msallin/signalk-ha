"""Path mappings, unit conversions and the unit fallback for unmapped Signal K fields."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

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


# Units the integration has settled on, as Home Assistant reports them. The check runs
# against the unit the sensor actually publishes -- after conversion -- rather than the
# Signal K unit, because a path the conversion does not catch keeps its raw unit and is
# therefore not settled: propulsion.port.oilPressure stays "Pa" while
# environment.outside.pressure becomes "hPa". Gating on the reported unit leaves those
# alone on its own, with no list of conversion suffixes to keep in step.
#
# Deliberately narrower than the Signal K vocabulary. Units still open to conversion
# (`m`, `s`, `m/s`, `m3`, `ratio`, `%`) are left out, because changing the unit of a
# sensor that already has statistics costs every user a units_changed repair. `J` and
# `C` are out because they carry running totals, which need TOTAL_INCREASING rather than
# MEASUREMENT, and `rad` because the arithmetic mean of a bearing points the wrong way.
#
# When adding a unit here:
# 1. Make sure the integration reports it directly, or converts to it in
#    `discovery._conversion_from_meta` for every path that carries the Signal K unit.
# 2. Make sure it is a settled choice -- statistics cannot change unit afterwards
#    without a repair issue for existing installs.
SETTLED_UNITS: frozenset[str] = frozenset(
    {
        UnitOfTemperature.CELSIUS,
        UnitOfPressure.HPA,
        UnitOfElectricPotential.VOLT,
        UnitOfElectricCurrent.AMPERE,
        UnitOfPower.WATT,
        UnitOfFrequency.HERTZ,
    }
)

# Matched case-insensitively, as `_conversion_from_meta` already does for the same string.
_SETTLED_LOWER: frozenset[str] = frozenset(unit.lower() for unit in SETTLED_UNITS)

# Thresholds and setpoints share their unit with the value they bound, so the unit alone
# cannot tell them apart. They are configuration, not measurements.
_CONFIG_WORDS: frozenset[str] = frozenset({"setpoint", "warn", "fault", "limit", "nominal"})

# `Hz` is settled for AC frequency but not for a rotation rate: revolutions are the
# obvious candidate for an RPM conversion, and converting after statistics exist costs a
# repair issue.
_UNSETTLED_WORDS: frozenset[str] = frozenset({"revolutions"})

_PATH_WORD = re.compile(r"[a-z]+|[A-Z][a-z]*")


def path_words(path: str) -> set[str]:
    """Split a Signal K path into lowercase words, on both dots and camelCase.

    Matching whole words rather than substrings matters: "default" is a common Signal K
    instance id and contains "fault".

    "electrical.batteries.house.temperature.limitDischargeUpper"
        -> {electrical, batteries, house, temperature, limit, discharge, upper}
    "electrical.chargers.default.voltage"
        -> {electrical, chargers, default, voltage}
    """
    return {word.lower() for word in _PATH_WORD.findall(path)}


def is_temperature_path(path: str) -> bool:
    """Whether a Kelvin path is a temperature, and so should be reported in Celsius.

    Kelvin only ever measures temperature, but the leaf naming varies, so match on the
    words rather than on an exact suffix. Anything left in Kelvin would sit next to a
    sibling in Celsius and could not be converted afterwards without a statistics repair.
    Both discovery and the registry restore share this, or the same path would come back
    in a different unit depending on which one created the entity.

    "environment.outside.temperature"               -> temperature              -> True
    "propulsion.port.coolantTemperature"            -> coolant, temperature     -> True
    "electrical.batteries.0.temperature.warnUpper"  -> temperature, warn, upper -> True
    "environment.inside.saloon.dewPoint"            -> dew, point               -> True
    """
    if "temperature" in path_words(path):
        return True
    return path.rsplit(".", 1)[-1].lower().endswith("dewpoint")


def state_class_for_unit(path: str, unit: Any) -> SensorStateClass | None:
    """Fallback state class for a path with no explicit mapping.

    `unit` is the unit the sensor reports, not the raw `meta.units`. That value comes
    from the server and is not validated against the schema -- real data carries things
    like "bool" -- so gate on the allowlist rather than on the unit being truthy.
    """
    if not isinstance(unit, str) or unit.lower() not in _SETTLED_LOWER:
        return None
    if path_words(path) & (_CONFIG_WORDS | _UNSETTLED_WORDS):
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
