"""Fallback state class for paths with no explicit mapping."""

from homeassistant.components.sensor import SensorStateClass

from custom_components.signalk_ha.discovery import discover_entities
from custom_components.signalk_ha.mapping import SETTLED_UNITS, state_class_for_units
from custom_components.signalk_ha.schema import _EXACT_ENTRIES, _PATTERN_ENTRIES


def test_settled_units_get_measurement() -> None:
    """Unmapped paths with a settled unit produce long-term statistics."""
    for path, units in (
        ("propulsion.port.temperature", "K"),
        ("propulsion.port.oilPressure", "Pa"),
        ("propulsion.port.alternatorVoltage", "V"),
        ("propulsion.port.revolutions", "Hz"),
        ("electrical.batteries.house.current", "A"),
        ("electrical.inverters.main.load", "W"),
    ):
        assert state_class_for_units(path, units) is SensorStateClass.MEASUREMENT


def test_unsettled_units_are_left_alone() -> None:
    """Totals, circular angles and units still open to conversion stay out."""
    for path, units in (
        ("electrical.solar.1.yieldToday", "J"),
        ("electrical.batteries.house.lifetimeDischarge", "C"),
        ("navigation.trip.daily.log", "m"),
        ("electrical.batteries.house.capacity.timeRemaining", "s"),
        ("electrical.batteries.house.capacity.stateOfCharge", "ratio"),
        ("navigation.course.calcValues.velocityMadeGood", "m/s"),
        ("tanks.fuel.0.capacity", "m3"),
        ("navigation.headingTrue", "rad"),
        ("environment.inside.saloon.relativeHumidity", "%"),
    ):
        assert state_class_for_units(path, units) is None


def test_non_numeric_units_are_ignored() -> None:
    """`meta.units` is not validated by the server, so gate on the allowlist."""
    assert state_class_for_units("electrical.displays.helm1.nightMode.state", "bool") is None
    assert state_class_for_units("some.path", "") is None
    assert state_class_for_units("some.path", None) is None
    assert state_class_for_units("some.path", 5) is None


def test_configuration_paths_are_skipped() -> None:
    """Thresholds and setpoints carry the unit of the value they bound."""
    for path in (
        "electrical.chargers.1.setpointVoltage",
        "electrical.batteries.house.temperature.warnUpper",
        "electrical.batteries.house.faultLower",
        "electrical.batteries.house.limitDischargeUpper",
        "electrical.batteries.house.capacity.nominal",
    ):
        assert state_class_for_units(path, "V") is None


def test_units_are_matched_case_insensitively() -> None:
    """`_conversion_from_meta` lowercases the same string, so this must agree."""
    assert state_class_for_units("propulsion.port.temperature", "k") is (
        SensorStateClass.MEASUREMENT
    )
    assert state_class_for_units("electrical.batteries.house.voltage", "v") is (
        SensorStateClass.MEASUREMENT
    )


def test_settled_units_are_a_subset_of_the_schema_vocabulary() -> None:
    """The allowlist narrows the schema vocabulary; it never adds to it."""
    schema_units = {entry.units for entry in _EXACT_ENTRIES.values() if entry.units} | {
        entry.units for _, entry in _PATTERN_ENTRIES if entry.units
    }
    assert SETTLED_UNITS < schema_units


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
