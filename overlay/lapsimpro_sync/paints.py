"""House-livery contract for the overlay paint installer.

The marketing site publishes ``data/liveries.json`` (schema ``lapsimpro.liveries.v1``).
Download CTAs use ``lapsimpro://paint/install?...``. When the overlay PR lands, register
that protocol and copy TGA files into the matching iRacing ``car_path`` folder:

    {Documents}/iRacing/paint/{car_path}/car_{customer_id}.tga

Asset drop path on the website repo (Pages-served):

    assets/liveries/{car_path}/car.tga
    assets/liveries/{car_path}/car_spec.tga
    assets/liveries/{car_path}/preview.svg  (or preview.png)

This module does not invent TGA pixels. If ``assets_ready`` is false, show the
existing preview and skip the copy.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

SCHEMA = "lapsimpro.liveries.v1"
PACK_ID = "lapsimpro-house-gt3"
PROTOCOL = "lapsimpro"
PROTOCOL_ACTION = "paint/install"
MANIFEST_PUBLIC_PATH = "/data/liveries.json"
ASSET_DROP_TEMPLATE = "assets/liveries/{car_path}/"

# Official iRacing paint folders (support article, May 2026) plus EVO alias.
CATALOG_CAR_PATHS = {
    "ferrari-296-gt3": "ferrari296gt3",
    "mustang-gt3": "fordmustanggt3",
    "bmw-m4-gt3": "bmwm4gt3",
    "huracan-gt3-evo": "lamborghinievogt3",
    "porsche-992-gt3r": "porsche992rgt3",
    "mclaren-720s": "mclaren720sgt3",
    "amg-gt3": "mercedesamgevogt3",
}

CAR_PATH_ALIASES = {
    "bmwm4gt3": ("bmwm4gt3evo",),
}


def default_paint_root() -> Path:
    override = os.environ.get("LAPSIMPRO_PAINT_ROOT")
    if override:
        return Path(override)
    return Path.home() / "Documents" / "iRacing" / "paint"


def paint_dest(car_path: str, documents: Path | None = None) -> Path:
    root = documents if documents is not None else default_paint_root()
    return Path(root) / car_path


def install_filenames(customer_id: str) -> dict[str, str]:
    cid = str(customer_id).strip()
    return {
        "car": f"car_{cid}.tga",
        "car_spec": f"car_spec_{cid}.tga",
        "car_num": f"car_num_{cid}.tga",
        "decal": f"decal_{cid}.tga",
    }


def install_files(car_path: str, customer_id: str, documents: Path | None = None) -> dict[str, Path]:
    dest = paint_dest(car_path, documents)
    return {key: dest / name for key, name in install_filenames(customer_id).items()}


def protocol_url(livery_id: str, car_path: str, pack_id: str = PACK_ID) -> str:
    query = urlencode({"id": livery_id, "car_path": car_path, "pack": pack_id})
    return f"{PROTOCOL}://{PROTOCOL_ACTION}?{query}"


def pack_protocol_url(pack_id: str = PACK_ID) -> str:
    return f"{PROTOCOL}://{PROTOCOL_ACTION}?{urlencode({'pack': pack_id})}"


def parse_protocol_url(href: str) -> dict[str, str]:
    parsed = urlparse(href)
    if parsed.scheme != PROTOCOL:
        raise ValueError(f"expected {PROTOCOL}:// URL")
    action = parsed.netloc + parsed.path
    action = action.replace("///", "/").strip("/")
    if action != PROTOCOL_ACTION:
        raise ValueError(f"expected action {PROTOCOL_ACTION}, got {action}")
    qs = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
    return qs


def resolve_car_paths(car_path: str) -> tuple[str, ...]:
    aliases = CAR_PATH_ALIASES.get(car_path, ())
    return (car_path, *aliases)


def source_dir(car_path: str) -> str:
    return ASSET_DROP_TEMPLATE.format(car_path=car_path)


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if data.get("pack_id") != PACK_ID:
        errors.append(f"pack_id must be {PACK_ID}")
    liveries = data.get("liveries")
    if not isinstance(liveries, list) or not liveries:
        errors.append("liveries must be a non-empty list")
        return errors
    seen: set[str] = set()
    for item in liveries:
        lid = item.get("id")
        path = item.get("car_path")
        if not lid or not path:
            errors.append("each livery needs id and car_path")
            continue
        if lid in seen:
            errors.append(f"duplicate livery id {lid}")
        seen.add(lid)
        href = (item.get("download") or {}).get("href", "")
        if not href.startswith(f"{PROTOCOL}://"):
            errors.append(f"{lid}: download.href must use {PROTOCOL}://")
        fallback = (item.get("download") or {}).get("fallback", "")
        if "github.com" in str(fallback).lower() or "github.com" in href.lower():
            errors.append(f"{lid}: public GitHub links are not allowed on paint CTAs")
    return errors
