from types import SimpleNamespace

from custom_components.signalk_ha.const import (
    CONF_DEFAULT_MIN_UPDATE_SECONDS,
    CONF_DEFAULT_PERIOD_MS,
    CONF_PATH_POLICIES,
)
from custom_components.signalk_ha.policy import (
    PathPolicy,
    default_policy_from_entry,
    merge_path_policy,
    parse_path_policies_text,
    path_policies_from_entry,
    path_policies_to_text,
    remove_path_policy,
    resolve_effective_policy,
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


def test_path_policies_from_entry_partial_override_uses_entry_defaults() -> None:
    entry = SimpleNamespace(
        options={
            CONF_DEFAULT_PERIOD_MS: 2500,
            CONF_DEFAULT_MIN_UPDATE_SECONDS: 2.5,
            CONF_PATH_POLICIES: {
                "environment.wind.speedTrue": {
                    "tolerance": 0.2,
                }
            },
        }
    )

    policy = path_policies_from_entry(entry)["environment.wind.speedTrue"]
    assert policy.period_ms == 2500
    assert policy.min_update_seconds == 2.5
    assert policy.tolerance == 0.2


def test_path_policies_reject_negative_tolerance() -> None:
    parsed = parse_path_policies_text(
        "environment.wind.speedTrue, period_ms=1000, min_update_seconds=1.0, tolerance=-0.1"
    )
    assert "tolerance" not in parsed["environment.wind.speedTrue"]

    entry = SimpleNamespace(
        options={
            CONF_PATH_POLICIES: {
                "environment.wind.speedTrue": {
                    "period_ms": 1000,
                    "min_update_seconds": 1.0,
                    "tolerance": -0.1,
                }
            }
        }
    )
    policy = path_policies_from_entry(entry)["environment.wind.speedTrue"]
    assert policy.tolerance is None


def test_merge_path_policy_updates_existing() -> None:
    merged = merge_path_policy(
        {"environment.wind.speedTrue": {"period_ms": 5000}},
        path="environment.wind.speedTrue",
        min_update_seconds=1.0,
    )
    assert merged["environment.wind.speedTrue"]["period_ms"] == 5000
    assert merged["environment.wind.speedTrue"]["min_update_seconds"] == 1.0


def test_merge_path_policy_does_not_mutate_existing() -> None:
    # The set_path_policy service passes entry.options straight in. Mutating the
    # stored dict in place makes the updated options compare equal to the old
    # ones, so async_update_entry detects no change and never persists or
    # reloads. Updating an existing path must therefore leave the input intact.
    existing = {"environment.wind.speedTrue": {"period_ms": 5000}}
    original_inner = existing["environment.wind.speedTrue"]

    merged = merge_path_policy(
        existing,
        path="environment.wind.speedTrue",
        min_update_seconds=1.0,
    )

    assert existing == {"environment.wind.speedTrue": {"period_ms": 5000}}
    assert "min_update_seconds" not in original_inner
    assert merged is not existing
    assert merged["environment.wind.speedTrue"] is not original_inner
    assert merged["environment.wind.speedTrue"]["min_update_seconds"] == 1.0


def test_merge_path_policy_rejects_negative_tolerance() -> None:
    try:
        merge_path_policy(
            {"environment.wind.speedTrue": {"period_ms": 5000}},
            path="environment.wind.speedTrue",
            tolerance=-0.1,
        )
    except ValueError:
        pass
    else:  # pragma: no cover - defensive
        assert False, "Expected ValueError for negative tolerance"


def test_remove_path_policy() -> None:
    existing = {
        "environment.wind.speedTrue": {"period_ms": 1000},
        "navigation.speedOverGround": {"period_ms": 2000},
    }
    merged = remove_path_policy(existing, path="environment.wind.speedTrue")
    assert "environment.wind.speedTrue" not in merged
    assert "navigation.speedOverGround" in merged
    # Original is left untouched.
    assert "environment.wind.speedTrue" in existing
    # Removing an absent path is a no-op rather than an error.
    assert remove_path_policy(None, path="does.not.exist") == {}


def test_resolve_effective_policy_precedence() -> None:
    policies = {
        "a.b": PathPolicy(path="a.b", period_ms=1000, min_update_seconds=1.0, tolerance=0.2),
        "c.d": PathPolicy(path="c.d", period_ms=1500, min_update_seconds=1.5, tolerance=None),
    }

    # Per-path override wins over the discovery base and the global defaults.
    eff = resolve_effective_policy(
        "a.b",
        default_period_ms=5000,
        default_min_update_seconds=5.0,
        path_policies=policies,
        base_min_update_seconds=3.0,
        base_tolerance=0.9,
    )
    assert (eff.period_ms, eff.min_update_seconds, eff.tolerance) == (1000, 1.0, 0.2)

    # Override without a tolerance keeps the discovery-provided (base) tolerance.
    eff = resolve_effective_policy(
        "c.d",
        default_period_ms=5000,
        default_min_update_seconds=5.0,
        path_policies=policies,
        base_tolerance=0.4,
    )
    assert (eff.period_ms, eff.min_update_seconds, eff.tolerance) == (1500, 1.5, 0.4)

    # No override: the base value is used where present, the global default otherwise.
    eff = resolve_effective_policy(
        "x.y",
        default_period_ms=5000,
        default_min_update_seconds=5.0,
        path_policies=policies,
        base_min_update_seconds=3.0,
        base_tolerance=0.9,
    )
    assert (eff.period_ms, eff.min_update_seconds, eff.tolerance) == (5000, 3.0, 0.9)

    # No override and no base: pure global defaults with no tolerance.
    eff = resolve_effective_policy(
        "x.y",
        default_period_ms=5000,
        default_min_update_seconds=5.0,
        path_policies={},
    )
    assert (eff.period_ms, eff.min_update_seconds, eff.tolerance) == (5000, 5.0, None)
