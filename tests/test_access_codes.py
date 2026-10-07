"""Free-access codes match by SHA-256 digest. Plaintext codes are not stored."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "assets" / "access-codes.js"
PAGE = ROOT / "download.html"
RELEASES = ROOT / "releases" / "index.html"
FREE_ACCESS = ROOT / "assets" / "free-access.js"
INSTALLER = ROOT / "assets" / "installer.js"
DOWNLOAD_PAGE = ROOT / "assets" / "download-page.js"

PUBLIC_HTML = (
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

# Generated for this test only. It is not an access code shipped with the site.
TEST_CODE = "test-only-8f3c1b6e9a24"
PUBLISHED_HASH = "f9c67c5045d2151dcb760b4871fbd9c1b292294d72380a1d0ed35e3716ce1f2a"
ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_hash_match_logic(tmp_path):
    expected = hashlib.sha256(TEST_CODE.encode("utf-8")).hexdigest()
    assert expected != PUBLISHED_HASH
    assert TEST_CODE not in MODULE.read_text(encoding="utf-8")

    runner = tmp_path / "run-access-match.mjs"
    runner.write_text(
        f"""
import {{ accessCodeMatches, digestMatchesAllowed, sha256Hex, ALLOWED_ACCESS_CODE_HASHES }} from {json.dumps(MODULE.as_uri())};

const code = {json.dumps(TEST_CODE)};
const expected = {json.dumps(expected)};
const published = {json.dumps(PUBLISHED_HASH)};

const abc = await sha256Hex("abc");
if (abc !== {json.dumps(ABC_SHA256)}) {{
  console.error("sha256 vector");
  process.exit(1);
}}

const digest = await sha256Hex(code.trim().toLowerCase());
if (digest !== expected) {{
  console.error("digest");
  process.exit(2);
}}

const messy = "  " + code.toUpperCase() + "\\n";
if (!(await accessCodeMatches(messy, [expected]))) {{
  console.error("trimmed case");
  process.exit(3);
}}
if (!digestMatchesAllowed(expected.toUpperCase(), [expected])) {{
  console.error("hash case");
  process.exit(4);
}}
if (await accessCodeMatches("definitely-not-a-code", [expected])) {{
  console.error("mismatch should fail");
  process.exit(5);
}}
if (await accessCodeMatches("   ", [expected])) {{
  console.error("blank should fail");
  process.exit(6);
}}
if (digestMatchesAllowed("abcd", [expected])) {{
  console.error("short digest");
  process.exit(7);
}}
if (await accessCodeMatches(code)) {{
  console.error("test code must not match the published list");
  process.exit(8);
}}
if (!ALLOWED_ACCESS_CODE_HASHES.includes(published)) {{
  console.error("published hash missing");
  process.exit(9);
}}
if (digest === published) {{
  console.error("collision");
  process.exit(10);
}}
""",
        encoding="utf-8",
    )
    result = subprocess.run(["node", runner], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout


def _free_access_tag(html: str) -> str:
    match = re.search(r"<article class=\"card free-access\"[^>]*>", html)
    assert match, "free access card missing"
    return match.group(0)


def test_download_page_free_access_card():
    html = PAGE.read_text(encoding="utf-8")
    script = FREE_ACCESS.read_text(encoding="utf-8")
    card = _free_access_tag(html)
    assert "hidden" not in card
    assert "Free access" in html
    assert 'placeholder="Enter access code"' in html
    assert "Unlock download" in html
    assert "data-free-access-status" in html
    assert "data-download-gate" in html
    assert 'href="./pricing.html"' in html
    assert 'href="./login.html"' in html
    assert "assets/free-access.js" in html
    assert "assets/installer.js" not in html
    assert "data-installer-download" not in html
    assert "data-installer-autostart" not in html
    assert "github.com" not in html.lower()
    assert "news.html" not in html.lower()
    assert "liveries" not in html.lower()
    assert "Code accepted - your download is starting" in script
    assert "That code isn't valid" in script
    assert "startInstallerDownload" in script
    assert "localStorage" in script
    assert "login.html" not in script
    assert "account-nav" not in script
    assert "fetch(" not in script
    assert "/api/" not in script
    assert "data-free-access" not in DOWNLOAD_PAGE.read_text(encoding="utf-8")
    assert TEST_CODE not in html
    assert TEST_CODE not in script


def test_releases_page_requires_the_same_code():
    html = RELEASES.read_text(encoding="utf-8")
    card = _free_access_tag(html)
    assert "hidden" not in card
    assert "data-free-access-resume" in card
    assert 'placeholder="Enter access code"' in html
    assert "Unlock download" in html
    assert "../assets/free-access.js" in html
    assert 'href="../pricing.html"' in html
    assert "Subscribe on Pricing" in html
    assert 'href="../login.html"' in html
    assert "data-installer-autostart" not in html
    assert "data-installer-download" not in html
    assert "assets/installer.js" not in html
    assert "github.com" not in html.lower()
    assert TEST_CODE not in html


def test_public_pages_do_not_start_the_installer_directly():
    installer = INSTALLER.read_text(encoding="utf-8")
    assert "INSTALLER_URL" in installer
    assert "startInstallerDownload" in installer
    assert "data-installer-autostart" not in installer
    assert "data-installer-download" not in installer
    for name in PUBLIC_HTML:
        html = (ROOT / name).read_text(encoding="utf-8")
        assert "data-installer-autostart" not in html, name
        assert "data-installer-download" not in html, name
        assert "assets/installer.js" not in html, name
        assert "github.com" not in html.lower(), name
        if name not in {"download.html", "releases/index.html"}:
            assert "assets/free-access.js" not in html, name


def test_valid_code_starts_download_without_login():
    env = os.environ.copy()
    env["LAPSIMPRO_TEST_ACCESS_CODE"] = TEST_CODE
    result = subprocess.run(
        ["node", ROOT / "tests" / "free-access-boot.mjs"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    boot = (ROOT / "tests" / "free-access-boot.mjs").read_text(encoding="utf-8")
    assert TEST_CODE not in boot
    assert TEST_CODE not in MODULE.read_text(encoding="utf-8")
