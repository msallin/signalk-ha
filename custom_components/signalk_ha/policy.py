"""Helpers for configurable per-path subscription and update policies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .const import (
    CONF_DEFAULT_MIN_UPDATE_SECONDS,
    CONF_DEFAULT_PERIOD_MS,
    CONF_PATH_POLICIES,
    DEFAULT_MIN_UPDATE_SECONDS,
    DEFAULT_PERIOD_MS,
)


@dataclass(frozen=True)
class PathPolicy:
    path: str
    period_ms: int
    min_update_seconds: float
    tolerance: float | None = None


@dataclass(frozen=True)
class EffectivePolicy:
    """Resolved subscription/update policy for a single path."""

    period_ms: int
    min_update_seconds: float
    tolerance: float | None


def resolve_effective_policy(
    path: str,
    *,
    default_period_ms: int,
    default_min_update_seconds: float,
    path_policies: Mapping[str, PathPolicy],
    base_min_update_seconds: float | None = None,
    base_tolerance: float | None = None,
) -> EffectivePolicy:
    """Resolve the effective policy for ``path``.

    Precedence is: an explicit per-path override wins; otherwise a value
    supplied by discovery (the ``base_*`` arguments) is used; otherwise the
    configured global default applies. Pass ``base_*`` as ``None`` when no
    discovery value exists for the path (for example registry-only specs).

    Discovery does not currently assign per-path subscription periods, so the
    global default is authoritative for ``period_ms`` unless a per-path override
    is set. If discovery ever needs to carry a period, add a ``base_period_ms``
    argument here rather than inferring it from another field.
    """
    period_ms = default_period_ms
    min_update_seconds = (
        base_min_update_seconds
        if base_min_update_seconds is not None
        else default_min_update_seconds
    )
    tolerance = base_tolerance

    override = path_policies.get(path)
    if override is not None:
        period_ms = override.period_ms
        min_update_seconds = override.min_update_seconds
        if override.tolerance is not None:
            tolerance = override.tolerance

    return EffectivePolicy(
        period_ms=period_ms,
        min_update_seconds=min_update_seconds,
        tolerance=tolerance,
    )


def default_policy_from_entry(entry: Any) -> tuple[int, float]:
    options = _entry_options(entry)
    period = _coerce_period_ms(options.get(CONF_DEFAULT_PERIOD_MS), DEFAULT_PERIOD_MS)
    min_update = _coerce_min_update_seconds(
        options.get(CONF_DEFAULT_MIN_UPDATE_SECONDS), DEFAULT_MIN_UPDATE_SECONDS
    )
    return period, min_update


def path_policies_from_entry(entry: Any) -> dict[str, PathPolicy]:
    options = _entry_options(entry)
    default_period_ms, default_min_update_seconds = default_policy_from_entry(entry)
    raw = options.get(CONF_PATH_POLICIES)
    if not isinstance(raw, dict):
        return {}
    policies: dict[str, PathPolicy] = {}
    for path, cfg in raw.items():
        normalized_path = _normalize_path(path)
        if not normalized_path:
            continue
        if not isinstance(cfg, dict):
            continue
        period_ms = _coerce_period_ms(cfg.get("period_ms"), default_period_ms)
        min_update_seconds = _coerce_min_update_seconds(
            cfg.get("min_update_seconds"), default_min_update_seconds
        )
        tolerance = _coerce_optional_float(cfg.get("tolerance"), min_value=0.0)
        policies[normalized_path] = PathPolicy(
            path=normalized_path,
            period_ms=period_ms,
            min_update_seconds=min_update_seconds,
            tolerance=tolerance,
        )
    return policies


def merge_path_policy(
    existing: dict[str, dict[str, Any]] | None,
    *,
    path: str,
    period_ms: int | None = None,
    min_update_seconds: float | None = None,
    tolerance: float | None = None,
) -> dict[str, dict[str, Any]]:
    normalized_path = _normalize_path(path)
    if not normalized_path:
        raise ValueError("Invalid path")

    # Copy the existing per-path entry instead of aliasing it: callers pass in
    # the stored options dict, and mutating it in place would let the updated
    # options compare equal to the originals (no persist, no reload).
    merged: dict[str, dict[str, Any]] = dict(existing or {})
    existing_policy = merged.get(normalized_path)
    current = dict(existing_policy) if isinstance(existing_policy, dict) else {}

    if period_ms is not None:
        current["period_ms"] = _coerce_period_ms(period_ms, DEFAULT_PERIOD_MS)
    if min_update_seconds is not None:
        current["min_update_seconds"] = _coerce_min_update_seconds(
            min_update_seconds, DEFAULT_MIN_UPDATE_SECONDS
        )
    if tolerance is not None:
        parsed_tolerance = _coerce_optional_float(tolerance, min_value=0.0)
        if parsed_tolerance is None:
            raise ValueError("tolerance must be a non-negative number")
        current["tolerance"] = parsed_tolerance

    merged[normalized_path] = current
    return merged


def remove_path_policy(
    existing: dict[str, dict[str, Any]] | None, *, path: str
) -> dict[str, dict[str, Any]]:
    """Return a copy of ``existing`` with ``path`` removed (no-op if absent)."""
    normalized_path = _normalize_path(path)
    if not normalized_path:
        raise ValueError("Invalid path")

    merged: dict[str, dict[str, Any]] = dict(existing or {})
    merged.pop(normalized_path, None)
    return merged


def parse_path_policies_text(text: str | None) -> dict[str, dict[str, Any]]:
    if not text:
        return {}

    policies: dict[str, dict[str, Any]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(",") if part.strip()]
        if not parts:
            continue
        path = _normalize_path(parts[0])
        if not path:
            continue

        item: dict[str, Any] = {}
        for field in parts[1:]:
            if "=" not in field:
                continue
            key, value = [segment.strip() for segment in field.split("=", 1)]
            key_lower = key.lower()
            if key_lower == "period_ms":
                item["period_ms"] = _coerce_period_ms(value, DEFAULT_PERIOD_MS)
            elif key_lower == "min_update_seconds":
                item["min_update_seconds"] = _coerce_min_update_seconds(
                    value, DEFAULT_MIN_UPDATE_SECONDS
                )
            elif key_lower == "tolerance":
                parsed = _coerce_optional_float(value, min_value=0.0)
                if parsed is not None:
                    item["tolerance"] = parsed

        policies[path] = item
    return policies


def path_policies_to_text(policies: Any) -> str:
    if not isinstance(policies, dict):
        return ""
    lines: list[str] = []
    for path in sorted(policies):
        cfg = policies[path]
        if not isinstance(cfg, dict):
            continue
        fields = [path]
        if "period_ms" in cfg:
            fields.append(f"period_ms={int(cfg['period_ms'])}")
        if "min_update_seconds" in cfg:
            fields.append(f"min_update_seconds={float(cfg['min_update_seconds'])}")
        if "tolerance" in cfg:
            fields.append(f"tolerance={float(cfg['tolerance'])}")
        lines.append(", ".join(fields))
    return "\n".join(lines)


def _entry_options(entry: Any) -> dict[str, Any]:
    options = getattr(entry, "options", None)
    if isinstance(options, Mapping):
        return dict(options)
    return {}


def _normalize_path(path: Any) -> str:
    if not isinstance(path, str):
        return ""
    return path.strip()


# Free-form text input (the options textarea) is clamped to the valid range rather
# than rejected, so a single typo doesn't fail the whole save. Structured inputs
# (the options number fields and the services) are range-validated by their schema.
def _coerce_period_ms(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1000:
        return 1000
    return parsed


def _coerce_min_update_seconds(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0.5:
        return 0.5
    return parsed


def _coerce_optional_float(value: Any, *, min_value: float | None = None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if min_value is not None and parsed < min_value:
        return None
    return parsed
