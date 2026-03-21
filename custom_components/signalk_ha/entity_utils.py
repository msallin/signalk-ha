"""Shared helpers for entity registry identifiers."""

from __future__ import annotations

import re
from typing import Any

try:
    from homeassistant.util import slugify as _slugify
except ImportError:  # pragma: no cover - Home Assistant provides slugify at runtime

    def _slugify(value: str) -> str:
        normalized = value.strip().lower()
        normalized = re.sub(r"[^a-z0-9_]+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized)
        return normalized.strip("_")


from .const import CONF_ENTITY_ID_PREFIX


def path_from_unique_id(unique_id: str | None) -> str | None:
    if not unique_id:
        return None
    prefix = "signalk:"
    if not unique_id.startswith(prefix):
        return None
    parts = unique_id.split(":", 2)
    if len(parts) != 3:
        return None
    return parts[2]


def normalize_entity_id_prefix(prefix: Any | None) -> str:
    if not isinstance(prefix, str):
        return ""
    normalized = _slugify(prefix.strip())
    if not normalized:
        return ""
    if not normalized.endswith("_"):
        normalized = f"{normalized}_"
    return normalized


def entity_id_prefix_for_entry(entry: Any) -> str:
    return normalize_entity_id_prefix(entry.data.get(CONF_ENTITY_ID_PREFIX))


def build_object_id(base: str, *, prefix: str = "") -> str:
    base_slug = _slugify(base.replace(".", "_")) or "entity"
    return f"{prefix}{base_slug}"
