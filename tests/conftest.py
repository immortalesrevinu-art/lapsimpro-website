from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "overlay") not in sys.path:
    sys.path.insert(0, str(ROOT / "overlay"))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LAPSIMPRO_SECRET", "test-secret-please-change")
    monkeypatch.setenv("LAPSIMPRO_DB", str(tmp_path / "lapsimpro.db"))
    monkeypatch.setenv("LAPSIMPRO_DEV_ENTITLEMENT", "1")
    monkeypatch.setenv("LAPSIMPRO_PUBLIC_URL", "http://testserver")
    monkeypatch.delenv("LAPSIMPRO_DOWNLOAD_URL", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    from server import app as appmod
    from server.config import load_settings

    appmod.settings = load_settings()
    from fastapi.testclient import TestClient

    with TestClient(appmod.app) as test_client:
        yield test_client


@pytest.fixture
def gated_client(tmp_path, monkeypatch):
    monkeypatch.setenv("LAPSIMPRO_SECRET", "test-secret-please-change")
    monkeypatch.setenv("LAPSIMPRO_DB", str(tmp_path / "gated.db"))
    monkeypatch.setenv("LAPSIMPRO_DEV_ENTITLEMENT", "0")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    from server import app as appmod
    from server.config import load_settings

    appmod.settings = load_settings()
    from fastapi.testclient import TestClient

    with TestClient(appmod.app) as test_client:
        yield test_client
