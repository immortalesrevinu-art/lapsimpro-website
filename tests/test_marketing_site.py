"""Public marketing redesign: overlays, image manifest, and page links."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "assets" / "img" / "sim"
HOME = ROOT / "index.html"

OVERLAYS = (
    "coach",
    "pedals",
    "speed",
    "bias",
    "reference",
    "standings",
    "relative",
    "delta",
    "track-map",
    "fuel",
)
COMING_SOON = ("standings", "relative", "delta", "track-map", "fuel")

PUBLIC_PAGES = (
    "index.html",
    "download.html",
    "support.html",
    "get-started.html",
    "pricing.html",
    "404.html",
    "login.html",
    "account.html",
    "dashboard.html",
    "aid.html",
    "leaderboards.html",
    "coaching.html",
    "releases/index.html",
)


def manifest() -> dict:
    return json.loads((SIM / "manifest.json").read_text(encoding="utf-8"))


def test_sim_manifest_points_at_real_placeholder_files():
    data = manifest()
    items = [data["hero"], *data["overlays"], *data["gallery"]]
    ids = [item["id"] for item in items]
    assert ids[0] == "hero"
    assert len(ids) == len(set(ids))
    for item in items:
        assert item["placeholder"] is True
        assert item["alt"].lower().startswith("placeholder art")
        assert item["width"] >= 640
        assert item["height"] >= 360
        webp = SIM / item["webp"]
        fallback = SIM / item["fallback"]
        assert webp.is_file(), item["webp"]
        assert fallback.is_file(), item["fallback"]
        assert fallback.suffix == ".svg"
        assert "PLACEHOLDER" in fallback.read_text(encoding="utf-8")
        assert webp.stat().st_size < 2_000_000
        assert fallback.stat().st_size < 2_000_000
    overlay_ids = [item["id"] for item in data["overlays"]]
    assert list(OVERLAYS) == overlay_ids


def test_home_features_overlays_and_checkout_paths():
    html = HOME.read_text(encoding="utf-8")
    assert 'href="./pricing.html"' in html
    assert 'href="./download.html"' in html
    assert 'href="./get-started.html"' in html
    assert 'href="./support.html"' in html
    assert 'data-nav="support"' in html
    assert "iRacing" in html
    assert "Assetto Corsa Competizione" in html
    assert "Coming later" in html
    assert "Get faster with pro reference laps." in html
    assert "REF vs YOU" in html
    assert "Fuel Calculator" in html
    assert "Track Map" in html
    assert html.lower().count("coming soon") >= 5
    for overlay_id in OVERLAYS:
        assert f'data-sim-id="{overlay_id}"' in html
        assert f'id="panel-{overlay_id}"' in html
    for overlay_id in COMING_SOON:
        panel = html.split(f'id="panel-{overlay_id}"', 1)[1].split("</article>", 1)[0]
        assert "Coming soon" in panel
    assert 'type="image/webp"' in html
    assert 'loading="eager"' in html
    assert 'loading="lazy"' in html
    assert 'fetchpriority="high"' in html
    assert 'width="2560"' in html
    assert 'srcset="./assets/img/sim/hero.webp"' in html
    assert 'src="./assets/img/sim/hero.svg"' in html
    assert "assets/marketing.css" in html
    script = (ROOT / "assets" / "sim-images.js").read_text(encoding="utf-8")
    assert "./img/sim/manifest.json" in script
    lowered = html.lower()
    assert "news.html" not in lowered
    assert "liveries.html" not in lowered
    assert "github.com" not in lowered
    assert "testimonial" not in lowered
    assert "racelab" not in lowered


def test_public_pages_share_the_marketing_stylesheet():
    for name in PUBLIC_PAGES:
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "marketing.css" in html, name
        assert "news.html" not in html, name
        assert "liveries.html" not in html, name
        assert 'data-nav="news"' not in html, name
        assert 'data-nav="liveries"' not in html, name


def test_readme_documents_the_image_drop_folder():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/img/sim/" in readme
    assert "manifest.json" in readme
    assert "placeholder" in readme.lower()
    assert "hero.webp" in readme
    assert "Do not put `LapSimPro-Setup.zip`" in readme or "100 MB" in readme
