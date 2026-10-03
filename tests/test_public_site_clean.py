"""lapsimpro.com publishes no news desk, no liveries, and no GitHub links."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOT_PUBLISHED = ("docs", "server", "overlay", "scripts", "tests", ".github")
REMOVED = (
    "news.html",
    "liveries.html",
    "paints.html",
    "data/news.json",
    "data/liveries.json",
    "assets/liveries-page.js",
    "assets/liveries",
)


def _published_html() -> list[Path]:
    pages = []
    for path in ROOT.rglob("*.html"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in NOT_PUBLISHED:
            continue
        pages.append(path)
    return pages


def test_news_and_liveries_are_gone():
    for rel in REMOVED:
        assert not (ROOT / rel).exists(), rel


def test_no_published_html_links_github():
    pages = _published_html()
    assert len(pages) >= 10
    for path in pages:
        html = path.read_text(encoding="utf-8").lower()
        assert "github.com" not in html, path
        assert "news.html" not in html, path
        assert "liveries.html" not in html, path
        assert "paints.html" not in html, path


def test_pages_build_skips_backend_docs_and_readmes():
    config = (ROOT / "_config.yml").read_text(encoding="utf-8")
    for entry in ("README.md", "docs/", "server/", "overlay/", "scripts/", "tests/"):
        assert f"- {entry}" in config, entry


def test_removed_pages_404_on_the_api_static_mount(client):
    for page in ("/news.html", "/liveries.html", "/paints.html", "/data/liveries.json"):
        assert client.get(page).status_code == 404, page
    releases = client.get("/releases/")
    assert releases.status_code == 200
    assert "github.com" not in releases.text.lower()
