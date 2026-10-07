"""Public support page and the download-recovery links that point at it."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "support.html"
INSTALLER_JS = ROOT / "assets" / "installer.js"


def test_support_page_covers_download_recovery():
    html = SUPPORT.read_text(encoding="utf-8")
    assert "Download failed?" in html
    assert 'id="after-purchase"' in html
    assert 'id="download-404"' in html
    assert 'id="login"' in html
    assert 'id="smartscreen"' in html
    assert 'id="overlay"' in html
    assert 'id="fps"' in html
    assert 'id="contact"' in html
    assert "lapsimpro.com/releases/LapSimPro-Setup.zip" in html
    assert 'href="./download.html"' in html
    assert "github.com" not in html.lower()
    assert "data-installer-download" not in html
    assert "data-installer-autostart" not in html
    assert "assets/installer.js" not in html
    assert "mailto:theuniversecontractor@gmail.com" in html
    assert "SmartScreen" in html
    assert "No active subscription" in html or "not subscribed" in html
    assert "data-nav=\"support\"" in html
    lowered = html.lower()
    assert "tel:" not in lowered
    assert "sk_live" not in lowered
    assert "whsec_" not in lowered
    assert "garage 61 token" not in lowered
    assert "github.com/immortalesrevinu-art/lapsimpro-website\"" not in html
    assert "github.com/immortalesrevinu-art/lapsimpro-website/issues" not in lowered


def test_download_flow_links_support_and_releases():
    download = (ROOT / "download.html").read_text(encoding="utf-8")
    assert 'href="./support.html#download-404"' in download
    assert 'href="./support.html"' in download or "support.html" in download
    assert 'href="./releases/"' in download
    assert "data-nav=\"support\"" in download
    assert "data-installer-download" not in download
    assert "data-installer-autostart" not in download

    started = (ROOT / "get-started.html").read_text(encoding="utf-8")
    assert 'href="./support.html"' in started
    assert 'href="./download.html"' in started
    assert "data-installer-download" not in started
    assert "assets/installer.js" not in started


def test_not_found_and_releases_link_support():
    missing = (ROOT / "404.html").read_text(encoding="utf-8")
    assert 'href="./support.html"' in missing
    assert 'id="recovery-note"' in missing
    assert 'href="./download.html"' in missing
    assert "/download.html" in missing
    assert "data-installer-download" not in missing
    assert "assets/installer.js" not in missing
    assert "github" not in missing.lower()
    assert "Download help" in missing

    releases = (ROOT / "releases" / "index.html").read_text(encoding="utf-8")
    assert 'href="../support.html"' in releases
    assert 'href="../pricing.html"' in releases
    assert "github" not in releases.lower()
    assert 'http-equiv="refresh"' not in releases
    assert "data-installer-download" not in releases
    assert "data-installer-autostart" not in releases
    assert "../assets/free-access.js" in releases
    assert "../assets/installer.js" not in releases
    script = INSTALLER_JS.read_text(encoding="utf-8")
    assert "LapSimPro-Setup.zip" in script
    assert "startInstallerDownload" in script
    assert "data-installer-download" not in script
    assert "data-installer-autostart" not in script


def test_home_footer_links_support():
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'href="./support.html"' in home
    assert "data-nav=\"support\"" in home


def test_public_pages_do_not_feature_news_or_liveries():
    pages = [
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
    ]
    for name in pages:
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "news.html" not in html, name
        assert "liveries.html" not in html, name
        assert 'data-nav="news"' not in html, name
        assert 'data-nav="liveries"' not in html, name


def test_support_page_is_served(client):
    page = client.get("/support.html")
    assert page.status_code == 200
    assert "Download failed?" in page.text
    assert "theuniversecontractor@gmail.com" in page.text
    missing = client.get("/releases/LapSimPro-Setup.zip")
    assert missing.status_code == 404
