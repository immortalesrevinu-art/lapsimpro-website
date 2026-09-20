"""Catalog / reference honesty — do not invent Garage 61 traces."""

from __future__ import annotations

import re

FORBIDDEN_SOURCES = frozenset(
    {"", "none", "invented", "placeholder", "g61_placeholder", "synthetic_g61"}
)
ALLOWED_SOURCES = frozenset(
    {"catalog", "catalog_sample", "garage61", "g61", "fastest", "driver_best", "bound"}
)


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def names_match(left: str | None, right: str | None) -> bool:
    a, b = normalize_name(left), normalize_name(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def reference_allowed(source: str | None) -> bool:
    key = (source or "").strip().casefold()
    if key in FORBIDDEN_SOURCES:
        return False
    if key in ALLOWED_SOURCES:
        return True
    # Unknown but explicit sources (e.g. a future catalog id) are allowed.
    return bool(key) and "invent" not in key and "placeholder" not in key


def bind_gates(
    session_track: str | None,
    session_car: str | None,
    ref_track: str | None,
    ref_car: str | None,
    ref_source: str | None,
) -> tuple[bool, str]:
    """Track/car/fastest bind: refuse mismatched or missing catalog references."""
    if not session_track or not session_car:
        return False, "NO SESSION IDENTITY"
    if not reference_allowed(ref_source):
        return False, "NO REFERENCE FOR THIS TRACK"
    if not names_match(session_track, ref_track):
        return False, "NO REFERENCE FOR THIS TRACK"
    if not names_match(session_car, ref_car):
        return False, "NO REFERENCE FOR THIS CAR"
    return True, "BOUND"
