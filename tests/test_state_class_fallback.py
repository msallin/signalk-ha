"""Fallback state class for paths with no explicit mapping."""

from homeassistant.components.sensor import SensorStateClass

from custom_components.signalk_ha.discovery import discover_entities
from custom_components.signalk_ha.mapping import (
    NON_WRAPPING_ANGLE_PATHS,
    NUMERIC_UNITS,
    state_class_for_units,
)


def test_numeric_units_get_measurement() -> None:
    """Unmapped paths with a numeric unit produce long-term statistics."""
    for path, units in (
        ("propulsion.port.temperature", "K"),
        ("propulsion.port.oilPressure", "Pa"),
        ("propulsion.port.alternatorVoltage", "V"),
        ("propulsion.port.revolutions", "Hz"),
        ("electrical.batteries.house.current", "A"),
        ("tanks.fuel.0.currentLevel", "ratio"),
    ):
        assert state_class_for_units(path, units) is SensorStateClass.MEASUREMENT


def test_non_numeric_units_are_ignored() -> None:
    """`meta.units` is not validated by the server, so gate on the vocabulary."""
    assert state_class_for_units("electrical.displays.helm1.nightMode.state", "bool") is None
    assert state_class_for_units("some.path", "") is None
    assert state_class_for_units("some.path", None) is None
    assert state_class_for_units("some.path", 5) is None


def test_circular_angles_get_no_state_class() -> None:
    """An arithmetic mean of 359 and 1 is 180: the opposite direction."""
    for path in (
        "navigation.headingTrue",
        "navigation.courseOverGroundTrue",
        "environment.wind.angleApparent",
        "environment.wind.angleTrueWater",
        "navigation.course.calcValues.bearingTrue",
        "navigation.courseGreatCircle.nextPoint.bearingTrue",
        "steering.autopilot.target.headingMagnetic",
    ):
        assert state_class_for_units(path, "rad") is None


def test_non_wrapping_angles_keep_measurement() -> None:
    """Rudder, variation, leeway and attitude never wrap."""
    for path in NON_WRAPPING_ANGLE_PATHS:
        assert state_class_for_units(path, "rad") is SensorStateClass.MEASUREMENT


def test_rate_of_turn_is_not_circular() -> None:
    """`rad/s` is a rate, not a bearing."""
    assert state_class_for_units("navigation.rateOfTurn", "rad/s") is SensorStateClass.MEASUREMENT


def test_vocabulary_is_the_closed_schema_set() -> None:
    assert "rad" in NUMERIC_UNITS
    assert "bool" not in NUMERIC_UNITS
    assert len(NUMERIC_UNITS) == 21


def test_null_value_still_gets_a_state_class() -> None:
    """Many real paths are null in a REST snapshot; that must not skip them."""
    data = {
        "propulsion": {
            "port": {
                "temperature": {"value": None, "meta": {"units": "K"}},
            }
        }
    }
    result = discover_entities(data, ["propulsion"])
    entity = next(e for e in result.entities if e.path == "propulsion.port.temperature")
    assert entity.state_class is SensorStateClass.MEASUREMENT
