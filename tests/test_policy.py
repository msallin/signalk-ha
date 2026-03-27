from types import SimpleNamespace

from custom_components.signalk_ha.const import (
    CONF_DEFAULT_MIN_UPDATE_SECONDS,
    CONF_DEFAULT_PERIOD_MS,
    CONF_PATH_POLICIES,
)
from custom_components.signalk_ha.policy import (
    default_policy_from_entry,
    merge_path_policy,
    parse_path_policies_text,
    path_policies_from_entry,
    path_policies_to_text,
)


def test_default_policy_from_entry() -> None:
    entry = SimpleNamespace(
        options={CONF_DEFAULT_PERIOD_MS: 1500, CONF_DEFAULT_MIN_UPDATE_SECONDS: 1.5}
    )
    period_ms, min_update_seconds = default_policy_from_entry(entry)
    assert period_ms == 1500
    assert min_update_seconds == 1.5


def test_parse_path_policies_text_roundtrip() -> None:
    text = """
    # comment
    environment.wind.speedTrue, period_ms=1000, min_update_seconds=1.0, tolerance=0.2
    navigation.speedOverGround, period_ms=2000
    """

    parsed = parse_path_policies_text(text)
    assert parsed["environment.wind.speedTrue"]["period_ms"] == 1000
    assert parsed["environment.wind.speedTrue"]["min_update_seconds"] == 1.0
    assert parsed["environment.wind.speedTrue"]["tolerance"] == 0.2
    assert parsed["navigation.speedOverGround"]["period_ms"] == 2000

    rendered = path_policies_to_text(parsed)
    assert "environment.wind.speedTrue" in rendered
    assert "period_ms=1000" in rendered
    assert "min_update_seconds=1.0" in rendered
    assert "tolerance=0.2" in rendered


def test_path_policies_from_entry() -> None:
    entry = SimpleNamespace(
        options={
            CONF_PATH_POLICIES: {
                "environment.wind.speedTrue": {
                    "period_ms": 1000,
                    "min_update_seconds": 1.0,
                    "tolerance": 0.1,
                }
            }
        }
    )
    policies = path_policies_from_entry(entry)
    policy = policies["environment.wind.speedTrue"]
    assert policy.period_ms == 1000
    assert policy.min_update_seconds == 1.0
    assert policy.tolerance == 0.1


def test_merge_path_policy_updates_existing() -> None:
    merged = merge_path_policy(
        {"environment.wind.speedTrue": {"period_ms": 5000}},
        path="environment.wind.speedTrue",
        min_update_seconds=1.0,
    )
    assert merged["environment.wind.speedTrue"]["period_ms"] == 5000
    assert merged["environment.wind.speedTrue"]["min_update_seconds"] == 1.0
