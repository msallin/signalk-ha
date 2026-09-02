"""Fallback state class for paths with no explicit mapping."""

from homeassistant.components.sensor import SensorStateClass

from custom_components.signalk_ha.discovery import (
    _conversion_from_meta,
    _unit_from_meta,
    discover_entities,
)
from custom_components.signalk_ha.mapping import (
    SETTLED_UNITS,
    Conversion,
    lookup_mapping,
    path_words,
    state_class_for_unit,
)
from custom_components.signalk_ha.schema import lookup_schema, schema_entries, schema_units
from custom_components.signalk_ha.sensor import _conversion_for_path, _fallback_unit_for_schema


def test_settled_units_get_measurement() -> None:
    """Unmapped paths reporting a settled unit produce long-term statistics."""
    for path, unit in (
        ("propulsion.port.temperature", "°C"),
        ("environment.outside.pressure", "hPa"),
        ("propulsion.port.alternatorVoltage", "V"),
        ("electrical.ac.0.phase.A.frequency", "Hz"),
        ("electrical.batteries.house.current", "A"),
        ("electrical.inverters.main.load", "W"),
    ):
        assert state_class_for_unit(path, unit) is SensorStateClass.MEASUREMENT


def test_unsettled_units_are_left_alone() -> None:
    """Totals, circular angles and units still open to conversion stay out.

    Starting statistics on a unit the integration may still convert would cost every
    user a units_changed repair the day that conversion lands.
    """
    for path, unit in (
        ("electrical.solar.1.yieldToday", "J"),
        ("electrical.batteries.house.lifetimeDischarge", "C"),
        ("navigation.trip.daily.log", "m"),
        ("electrical.batteries.house.capacity.timeRemaining", "s"),
        ("electrical.batteries.house.capacity.stateOfCharge", "ratio"),
        ("navigation.course.calcValues.velocityMadeGood", "m/s"),
        ("tanks.fuel.0.capacity", "m3"),
        ("navigation.headingTrue", "°"),
        ("environment.inside.saloon.relativeHumidity", "%"),
    ):
        assert state_class_for_unit(path, unit) is None


def test_raw_signalk_units_are_not_settled() -> None:
    """The gate is on the reported unit, so an unconverted path stays out.

    `K` and `Pa` only reach Home Assistant as Celsius and hPa. A path still carrying the
    raw unit is one no conversion caught, and converting it later would cost a repair.
    """
    assert state_class_for_unit("propulsion.port.coolantTemperature", "K") is None
    assert state_class_for_unit("propulsion.port.oilPressure", "Pa") is None


def test_non_numeric_units_are_ignored() -> None:
    """`meta.units` is not validated by the server, so gate on the allowlist."""
    assert state_class_for_unit("electrical.displays.helm1.nightMode.state", "bool") is None
    assert state_class_for_unit("some.path", "") is None
    assert state_class_for_unit("some.path", None) is None
    assert state_class_for_unit("some.path", 5) is None


def test_configuration_paths_are_skipped() -> None:
    """Thresholds and setpoints carry the unit of the value they bound."""
    for path in (
        "electrical.chargers.1.setpointVoltage",
        "electrical.batteries.house.temperature.warnUpper",
        "electrical.batteries.house.faultLower",
        "electrical.batteries.house.limitDischargeUpper",
        "electrical.batteries.house.capacity.nominal",
    ):
        assert state_class_for_unit(path, "V") is None


def test_instance_ids_are_not_mistaken_for_configuration() -> None:
    """`default` is a common Signal K instance id and contains `fault`."""
    for path in (
        "electrical.chargers.default.voltage",
        "electrical.displays.navico.default.current",
    ):
        assert state_class_for_unit(path, "V") is SensorStateClass.MEASUREMENT


def test_revolutions_stay_out_while_frequency_does_not() -> None:
    """`Hz` is settled for AC frequency, but a rotation rate may still become RPM."""
    assert state_class_for_unit("propulsion.port.revolutions", "Hz") is None
    assert state_class_for_unit("electrical.alternators.0.revolutions", "Hz") is None
    assert (
        state_class_for_unit("electrical.ac.0.phase.A.frequency", "Hz")
        is SensorStateClass.MEASUREMENT
    )


def test_units_are_matched_case_insensitively() -> None:
    """`_conversion_from_meta` lowercases the same string, so this must agree."""
    assert state_class_for_unit("propulsion.port.temperature", "°c") is (
        SensorStateClass.MEASUREMENT
    )
    assert state_class_for_unit("electrical.batteries.house.voltage", "v") is (
        SensorStateClass.MEASUREMENT
    )


def test_path_words_split_on_dots_and_camel_case() -> None:
    assert path_words("electrical.batteries.house.temperature.limitDischargeUpper") == {
        "electrical",
        "batteries",
        "house",
        "temperature",
        "limit",
        "discharge",
        "upper",
    }
    assert "fault" not in path_words("electrical.chargers.default.voltage")


def test_settled_units_are_reported_units_not_signalk_units() -> None:
    """The allowlist names what Home Assistant reports, not what Signal K sends."""
    assert {"K", "Pa"} <= schema_units()
    assert SETTLED_UNITS.isdisjoint({"K", "Pa"})


def test_every_kelvin_path_in_the_schema_reaches_celsius() -> None:
    """Kelvin only measures temperature, so no schema path may keep the raw unit.

    One left behind would sit next to a sibling in Celsius, and could not be converted
    afterwards without a statistics repair for everyone who already has history.
    """
    kelvin = [path for path, entry in schema_entries() if entry.units == "K"]
    assert kelvin, "the bundled schema should carry Kelvin paths"
    for path in kelvin:
        assert _conversion_from_meta(path, "K") is Conversion.K_TO_C, path
        assert str(_unit_from_meta(path, "K", Conversion.K_TO_C)) == "°C", path


def test_derived_temperatures_are_converted_like_plain_ones() -> None:
    """The leaf naming varies; the unit must not."""
    for path in (
        "environment.outside.temperature",
        "environment.outside.dewPointTemperature",
        "environment.outside.heatIndexTemperature",
        "environment.inside.saloon.dewPoint",
        "electrical.alternators.0.regulatorTemperature",
        "propulsion.port.coolantTemperature",
    ):
        conversion = _conversion_from_meta(path, "K")
        unit = _unit_from_meta(path, "K", conversion)
        assert conversion is Conversion.K_TO_C, path
        assert state_class_for_unit(path, unit) is SensorStateClass.MEASUREMENT, path


def test_discovery_and_registry_restore_agree_on_every_schema_path() -> None:
    """The two call sites must produce the same unit, conversion and state class.

    They run on different inputs -- discovery has `meta.units`, the restore has only
    what the registry kept -- so a rule added to one and not the other shows up as an
    entity that changes unit depending on whether the server was reachable at startup.
    """
    disagreements = []
    for pattern, entry in schema_entries():
        path = pattern.replace("*", "0")
        schema = lookup_schema(path)
        if not entry.units or lookup_mapping(path) or (schema and not schema.units):
            continue

        conversion = _conversion_from_meta(path, entry.units)
        unit = _unit_from_meta(path, entry.units, conversion)
        discovered = (conversion, str(unit), state_class_for_unit(path, unit))

        restored_conversion = _conversion_for_path(path, schema, str(unit))
        restored_unit = _fallback_unit_for_schema(schema, str(unit), restored_conversion)
        restored = (
            restored_conversion,
            str(restored_unit),
            state_class_for_unit(path, restored_unit),
        )

        if discovered != restored:
            disagreements.append((path, discovered, restored))

    assert not disagreements


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
