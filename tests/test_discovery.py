import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.signalk_ha.discovery import (
    _disambiguated_name,
    _humanize_segment,
    _prefix_parts_for_path,
    apply_entry_policies,
    convert_value,
    discover_entities,
)
from custom_components.signalk_ha.mapping import Conversion


def test_discovery_finds_expected_paths() -> None:
    data = json.loads(Path("tests/vessel_self_testdata.json").read_text(encoding="utf-8"))
    result = discover_entities(data, scopes=("environment", "tanks", "navigation"))
    paths = {entity.path for entity in result.entities}

    assert "navigation.speedOverGround" in paths
    assert "navigation.courseOverGroundTrue" in paths
    assert "environment.inside.saloon.temperature" in paths
    assert "tanks.freshWater.0.currentLevel" in paths
    assert "navigation.position" in paths
    assert "notifications.navigation.course.perpendicularPassed" not in paths


def test_discovery_position_is_geo_location() -> None:
    data = json.loads(Path("tests/vessel_self_testdata.json").read_text(encoding="utf-8"))
    result = discover_entities(data, scopes=("navigation",))
    position = [entity for entity in result.entities if entity.path == "navigation.position"]
    assert position
    assert position[0].kind == "geo_location"


def test_discovery_result_indexes() -> None:
    data = json.loads(Path("tests/vessel_self_testdata.json").read_text(encoding="utf-8"))
    result = discover_entities(data, scopes=("navigation",))
    assert "navigation.speedOverGround" in result.paths
    assert ("navigation.position", "geo_location") in result.path_kinds


def test_discovery_walks_children_when_value_present() -> None:
    data = json.loads(Path("tests/vessel_self_testdata.json").read_text(encoding="utf-8"))
    result = discover_entities(data, scopes=("navigation",))
    paths = {entity.path for entity in result.entities}

    assert "navigation.courseGreatCircle.nextPoint.arrivalCircle" in paths
    assert "navigation.courseGreatCircle.nextPoint.steerError" in paths


def test_discovery_skips_href_and_url_description() -> None:
    data = {
        "navigation": {
            "link": {"value": 1, "meta": {"description": "See URL for details"}},
            "foo": {"href": {"value": "http://example.com"}},
        }
    }
    result = discover_entities(data, scopes=("navigation",))
    paths = {entity.path for entity in result.entities}
    assert "navigation.link" not in paths
    assert "navigation.foo.href" not in paths


def test_discovery_skips_non_dict_children() -> None:
    data = {"navigation": {"speedOverGround": {"value": 1}, "foo": "bar"}}
    result = discover_entities(data, scopes=("navigation",))
    paths = {entity.path for entity in result.entities}
    assert "navigation.foo" not in paths
    assert "navigation.speedOverGround" in paths
    speed = next(spec for spec in result.entities if spec.path == "navigation.speedOverGround")
    assert speed.spec_known is True


def test_discovery_skips_non_dict_scope() -> None:
    data = {"navigation": "not-a-dict"}
    result = discover_entities(data, scopes=("navigation",))
    assert result.entities == []


def test_discovery_skips_notifications_scope() -> None:
    data = {"notifications": {"navigation": {"anchor": {"value": {"state": "alert"}}}}}
    result = discover_entities(data, scopes=("notifications",))
    assert result.entities == []


def test_discovery_position_uses_meta_description_when_schema_missing() -> None:
    data = {
        "navigation": {
            "position": {
                "value": {"latitude": 1.0, "longitude": 2.0},
                "meta": {"description": "GPS position"},
            }
        }
    }
    with patch("custom_components.signalk_ha.discovery.lookup_schema", return_value=None):
        result = discover_entities(data, scopes=("navigation",))
    entity = next(spec for spec in result.entities if spec.path == "navigation.position")
    assert entity.description == "GPS position"


def test_discovery_humanize_segment_empty() -> None:
    assert _humanize_segment("") == ""


def test_discovery_disambiguated_name_keeps_base_when_no_prefix() -> None:
    assert _disambiguated_name("speed", "Speed") == "Speed"


def test_discovery_disambiguated_name_empty_prefix() -> None:
    assert _disambiguated_name(".speed", "Speed") == "Speed"


def test_discovery_disambiguated_name_skips_when_prefix_already_present() -> None:
    name = "Navigation Speed Over Ground"
    assert _disambiguated_name("navigation.speedOverGround", name) == name


def test_discovery_disambiguated_name_prefix_case_insensitive() -> None:
    name = "navigation Speed"
    assert _disambiguated_name("navigation.speedOverGround", name) == name


def test_discovery_disambiguated_name_prefix_only() -> None:
    name = "Navigation"
    assert _disambiguated_name("navigation.speedOverGround", name) == name


def test_discovery_disambiguated_name_prefix_non_generic() -> None:
    name = "Wind Speed Over Ground"
    assert _disambiguated_name("environment.wind.speedOverGround", name) == name


def test_discovery_prefix_parts_handles_digits() -> None:
    assert _prefix_parts_for_path("tanks.fuel.0.currentLevel") == ["fuel", "0"]
    assert _prefix_parts_for_path("tanks.0.currentLevel") == ["tanks", "0"]
    assert _prefix_parts_for_path("tanks.fuel.1.2.currentLevel") == ["fuel", "2"]
    assert _prefix_parts_for_path("speed") == []


def test_discovery_disambiguates_duplicate_names() -> None:
    data = {
        "navigation": {"speedOverGround": {"value": 1}},
        "environment": {"wind": {"speedOverGround": {"value": 2}}},
    }
    result = discover_entities(data, scopes=("navigation", "environment"))
    names = {entity.path: entity.name for entity in result.entities}
    assert names["navigation.speedOverGround"] == "SOG"
    assert names["environment.wind.speedOverGround"] == "GWS"


def test_discovery_uses_marine_abbreviations_for_known_paths() -> None:
    data = {
        "navigation": {
            "speedOverGround": {"value": 1.0, "meta": {"units": "m/s"}},
            "courseOverGroundTrue": {"value": 1.0, "meta": {"units": "rad"}},
        },
        "environment": {
            "wind": {
                "speedApparent": {"value": 2.0, "meta": {"units": "m/s"}},
                "directionTrue": {"value": 1.2, "meta": {"units": "rad"}},
            }
        },
    }
    result = discover_entities(data, scopes=("navigation", "environment"))
    names = {entity.path: entity.name for entity in result.entities}
    units = {entity.path: entity.unit for entity in result.entities}
    precisions = {entity.path: entity.suggested_display_precision for entity in result.entities}

    assert names["navigation.speedOverGround"] == "SOG"
    assert names["navigation.courseOverGroundTrue"] == "COG"
    assert names["environment.wind.speedApparent"] == "AWS"
    assert names["environment.wind.directionTrue"] == "GWD"
    assert units["navigation.courseOverGroundTrue"] == "° T"
    assert units["environment.wind.directionTrue"] == "° T"
    assert precisions["navigation.speedOverGround"] == 1
    assert precisions["navigation.courseOverGroundTrue"] == 0
    assert precisions["environment.wind.directionTrue"] == 0


def test_discovery_sets_default_precision_for_speed_and_angle() -> None:
    data = {
        "navigation": {
            "rateOfTurn": {"value": 0.123, "meta": {"units": "rad"}},
            "speedThroughWater": {"value": 3.3, "meta": {"units": "m/s"}},
        },
        "environment": {
            "current": {
                "setMagnetic": {"value": 1.0, "meta": {"units": "rad"}},
            }
        },
    }

    result = discover_entities(data, scopes=("navigation", "environment"))
    precisions = {entity.path: entity.suggested_display_precision for entity in result.entities}
    units = {entity.path: entity.unit for entity in result.entities}

    assert precisions["navigation.speedThroughWater"] == 1
    assert precisions["navigation.rateOfTurn"] == 0
    assert precisions["environment.current.setMagnetic"] == 0
    assert units["environment.current.setMagnetic"] == "° M"


def test_discovery_apply_entry_policies_defaults_and_overrides() -> None:
    data = {
        "environment": {
            "wind": {
                "speedTrue": {"value": 3.0, "meta": {"units": "m/s"}},
                "speedApparent": {"value": 2.0, "meta": {"units": "m/s"}},
            }
        }
    }
    discovered = discover_entities(data, scopes=("environment",))
    entry = SimpleNamespace(
        options={
            "default_period_ms": 2000,
            "default_min_update_seconds": 2.0,
            "path_policies": {
                "environment.wind.speedTrue": {
                    "period_ms": 1000,
                    "min_update_seconds": 1.0,
                    "tolerance": 0.2,
                }
            },
        }
    )

    applied = apply_entry_policies(discovered, entry)
    by_path = {entity.path: entity for entity in applied.entities}

    assert by_path["environment.wind.speedTrue"].period_ms == 1000
    assert by_path["environment.wind.speedTrue"].min_update_seconds == 1.0
    assert by_path["environment.wind.speedTrue"].tolerance == 0.2

    assert by_path["environment.wind.speedApparent"].period_ms == 2000
    assert by_path["environment.wind.speedApparent"].min_update_seconds == 2.0


def test_discovery_uses_compass_unit_from_schema_description() -> None:
    data = {
        "navigation": {
            "headingCompass": {"value": 1.0, "meta": {"units": "rad"}},
        }
    }

    result = discover_entities(data, scopes=("navigation",))
    entity = next(spec for spec in result.entities if spec.path == "navigation.headingCompass")

    assert entity.unit == "° C"


def test_discovery_wind_direction_has_no_state_class() -> None:
    data = {
        "environment": {
            "wind": {
                "directionTrue": {"value": 1.2, "meta": {"units": "rad"}},
                "directionMagnetic": {"value": 1.2, "meta": {"units": "rad"}},
            }
        }
    }

    result = discover_entities(data, scopes=("environment",))
    state_classes = {entity.path: entity.state_class for entity in result.entities}

    assert state_classes["environment.wind.directionTrue"] is None
    assert state_classes["environment.wind.directionMagnetic"] is None


def test_discovery_uses_context_rich_fallback_names() -> None:
    data = {
        "environment": {
            "inside": {
                "engineRoom": {
                    "pressure": {
                        "value": 100000,
                        "meta": {"units": "Pa"},
                    }
                }
            }
        },
        "electrical": {
            "batteries": {
                "0": {
                    "current": {
                        "value": 12.3,
                        "meta": {"units": "A"},
                    }
                }
            }
        },
    }

    result = discover_entities(data, scopes=("environment", "electrical"))
    names = {entity.path: entity.name for entity in result.entities}

    assert names["environment.inside.engineRoom.pressure"] == "Inside Engine Room Pressure"
    assert names["electrical.batteries.0.current"] == "Batteries 0 Current"


def test_discovery_meta_display_name_and_units() -> None:
    data = {
        "environment": {
            "outside": {
                "temperature": {
                    "value": 300.0,
                    "meta": {"units": "K", "displayName": "Outside Temp"},
                }
            }
        }
    }
    result = discover_entities(data, scopes=("environment",))
    entity = next(spec for spec in result.entities if spec.path.endswith("temperature"))
    assert entity.name == "Outside Temp"
    assert entity.unit == "degC"
    assert entity.conversion is not None
    assert entity.spec_known is True


def test_discovery_schema_units_used_when_meta_missing() -> None:
    data = {
        "environment": {
            "outside": {
                "temperature": {
                    "value": 300.0,
                }
            }
        }
    }
    result = discover_entities(data, scopes=("environment",))
    entity = next(spec for spec in result.entities if spec.path.endswith("temperature"))
    assert entity.unit == "degC"
    assert entity.conversion is not None
    assert entity.spec_known is True


def test_discovery_schema_description_overrides_meta() -> None:
    data = {
        "environment": {
            "outside": {
                "temperature": {
                    "value": 300.0,
                    "meta": {"description": "Custom Temp"},
                }
            }
        }
    }
    result = discover_entities(data, scopes=("environment",))
    entity = next(spec for spec in result.entities if spec.path.endswith("temperature"))
    assert entity.description == "Current outside air temperature"


def test_discovery_ratio_current_level_conversion() -> None:
    data = {
        "tanks": {
            "fuel": {
                "0": {
                    "currentLevel": {
                        "value": 0.4,
                        "meta": {"units": "ratio", "shortName": "Fuel"},
                    }
                }
            }
        }
    }
    result = discover_entities(data, scopes=("tanks",))
    entity = next(spec for spec in result.entities if spec.path.endswith("currentLevel"))
    assert entity.unit == "%"
    assert entity.tolerance is not None


def test_discovery_records_unit_conflict() -> None:
    data = {
        "navigation": {
            "speedOverGround": {"value": 1.0, "meta": {"units": "km/h"}},
        }
    }
    result = discover_entities(data, scopes=("navigation",))
    assert result.conflicts
    conflict = result.conflicts[0]
    assert conflict.path == "navigation.speedOverGround"


def test_convert_value_non_numeric_returns_raw() -> None:
    assert convert_value("abc", None) == "abc"


def test_convert_value_numeric_conversion() -> None:
    assert convert_value(1.0, Conversion.MS_TO_KNOTS) != 1.0


def test_convert_value_non_numeric_with_conversion() -> None:
    assert convert_value("abc", Conversion.MS_TO_KNOTS) == "abc"


def test_discovery_icon_defaults() -> None:
    data = {
        "electrical": {"batteries": {"0": {"voltage": {"value": 12.4}}}},
        "tanks": {"fuel": {"0": {"currentLevel": {"value": 0.5}}}},
        "environment": {"outside": {"temperature": {"value": 300.0, "meta": {"units": "K"}}}},
    }
    result = discover_entities(data, scopes=("electrical", "tanks", "environment"))
    icons = {entity.path: entity.icon for entity in result.entities}
    assert icons["electrical.batteries.0.voltage"] == "mdi:battery"
    assert icons["tanks.fuel.0.currentLevel"] == "mdi:fuel"
    assert icons["environment.outside.temperature"] == "mdi:thermometer"
