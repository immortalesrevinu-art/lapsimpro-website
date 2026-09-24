from __future__ import annotations

import json
from pathlib import Path

from overlay.lapsimpro_sync.paints import (
    CATALOG_CAR_PATHS,
    PACK_ID,
    SCHEMA,
    install_files,
    pack_protocol_url,
    parse_protocol_url,
    protocol_url,
    resolve_car_paths,
    source_dir,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "liveries.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_contract():
    data = _manifest()
    errors = validate_manifest(data)
    assert errors == []
    assert data["schema"] == SCHEMA
    assert data["pack_id"] == PACK_ID
    ids = {item["id"] for item in data["liveries"]}
    assert "ferrari-296-gt3-house" in ids
    assert "mustang-gt3-house" in ids
    assert "bmw-m4-gt3-house" in ids


def test_catalog_car_paths_match_iracing_folders():
    data = _manifest()
    by_catalog = {item["catalog_id"]: item for item in data["liveries"]}
    for catalog_id, car_path in CATALOG_CAR_PATHS.items():
        item = by_catalog[catalog_id]
        assert item["car_path"] == car_path
        assert item["source_dir"] == source_dir(car_path)
        preview = ROOT / item["preview"]["src"].replace("./", "")
        assert preview.is_file(), preview
        assert (ROOT / item["source_dir"]).is_dir()


def test_bmw_evo_keeps_official_paint_folder():
    bmw = next(item for item in _manifest()["liveries"] if item["catalog_id"] == "bmw-m4-gt3")
    assert bmw["name"] == "BMW M4 GT3 EVO"
    assert bmw["car_path"] == "bmwm4gt3"
    assert "bmwm4gt3evo" in bmw["car_path_aliases"]
    assert resolve_car_paths("bmwm4gt3") == ("bmwm4gt3", "bmwm4gt3evo")


def test_protocol_urls_are_overlay_installers():
    data = _manifest()
    for item in data["liveries"]:
        href = item["download"]["href"]
        parsed = parse_protocol_url(href)
        assert parsed["id"] == item["id"]
        assert parsed["car_path"] == item["car_path"]
        assert parsed["pack"] == PACK_ID
        assert item["download"]["fallback"].startswith("./download.html")
        assert "github.com" not in href
        assert "github.com" not in item["download"]["fallback"]
        assert href == protocol_url(item["id"], item["car_path"])
    assert data["install"]["pack_href"] == pack_protocol_url()


def test_install_filenames_use_customer_id(tmp_path):
    files = install_files("ferrari296gt3", "12345", documents=tmp_path)
    assert files["car"] == tmp_path / "ferrari296gt3" / "car_12345.tga"
    assert files["car_spec"].name == "car_spec_12345.tga"


def test_liveries_page_has_no_github_cta():
    html = (ROOT / "liveries.html").read_text(encoding="utf-8")
    assert "github.com" not in html.lower()
    assert 'data-nav="liveries"' not in html
    assert 'href="./news.html"' not in html
    assert "data-install-handoff" in html
    assert "./data/liveries.json" in (ROOT / "assets/liveries-page.js").read_text(encoding="utf-8")


def test_static_manifest_and_page_are_served(client):
    manifest = client.get("/data/liveries.json")
    assert manifest.status_code == 200
    assert manifest.json()["pack_id"] == PACK_ID
    page = client.get("/liveries.html")
    assert page.status_code == 200
    assert "House" in page.text
    alias = client.get("/paints.html")
    assert alias.status_code == 200
    assert "liveries.html" in alias.text
