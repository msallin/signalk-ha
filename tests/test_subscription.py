from custom_components.signalk_ha.const import (
    DEFAULT_MIN_UPDATE_MS,
    DEFAULT_PERIOD_MS,
    DEFAULT_STALE_SECONDS,
)
from custom_components.signalk_ha.subscription import build_subscribe_payload


def test_build_subscribe_payload_sanitizes_paths() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "  navigation.speedOverGround  ", "period": 1000},
            {"path": "", "period": 1000},
            {"path": "#comment", "period": 1000},
            {"path": "   ", "period": 1000},
            {"path": "navigation.speedOverGround", "period": 1000},
        ],
    )
    assert payload == {
        "context": "vessels.self",
        "subscribe": [
            {
                "path": "navigation.speedOverGround",
                "period": 1000,
                "minPeriod": 1000,
                "format": "delta",
                "policy": "ideal",
            }
        ],
    }


def test_build_subscribe_payload_skips_invalid_items() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            "not-a-dict",
            {"path": "navigation.speedOverGround"},
            {"path": "navigation.depth", "period": 500},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": DEFAULT_PERIOD_MS,
            "minPeriod": DEFAULT_PERIOD_MS,
            "format": "delta",
            "policy": "ideal",
        },
        {
            "path": "navigation.depth",
            "period": 500,
            "minPeriod": 500,
            "format": "delta",
            "policy": "ideal",
        },
    ]


def test_build_subscribe_payload_defaults_period() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround"},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": DEFAULT_PERIOD_MS,
            "minPeriod": DEFAULT_PERIOD_MS,
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_handles_none_periods() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.depth", "period": None, "minPeriod": None},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.depth",
            "period": DEFAULT_PERIOD_MS,
            "minPeriod": DEFAULT_PERIOD_MS,
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_respects_min_period_override() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": 5000, "minPeriod": 1000},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": 5000,
            "minPeriod": 1000,
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_caps_min_period_to_period() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": 1000, "minPeriod": 5000},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": 1000,
            "minPeriod": 1000,
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_defaults_min_period_to_guard() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": 10000},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": 10000,
            "minPeriod": DEFAULT_MIN_UPDATE_MS,
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_clamps_period_below_stale() -> None:
    stale_limit = int(DEFAULT_STALE_SECONDS * 1000)
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": stale_limit},
        ],
    )
    expected_period = max(stale_limit - 1000, 1000)
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": expected_period,
            "minPeriod": min(DEFAULT_MIN_UPDATE_MS, expected_period),
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_defaults_zero_period() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": 0},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": DEFAULT_PERIOD_MS,
            "minPeriod": min(DEFAULT_MIN_UPDATE_MS, DEFAULT_PERIOD_MS),
            "format": "delta",
            "policy": "ideal",
        }
    ]


def test_build_subscribe_payload_defaults_zero_min_period() -> None:
    payload = build_subscribe_payload(
        "vessels.self",
        [
            {"path": "navigation.speedOverGround", "period": 2000, "minPeriod": 0},
        ],
    )
    assert payload["subscribe"] == [
        {
            "path": "navigation.speedOverGround",
            "period": 2000,
            "minPeriod": min(DEFAULT_MIN_UPDATE_MS, 2000),
            "format": "delta",
            "policy": "ideal",
        }
    ]
