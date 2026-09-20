"""Secure local session storage for the overlay device token."""

from __future__ import annotations

import json
import os
from pathlib import Path


def default_path() -> Path:
    override = os.environ.get("LAPSIMPRO_SESSION_FILE")
    if override:
        return Path(override)
    return Path.home() / ".lapsimpro" / "session.json"


def save_session(token: str, api_url: str, email: str, path: Path | None = None) -> Path:
    dest = path or default_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"token": token, "api_url": api_url.rstrip("/"), "email": email}
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(dest, 0o600)
        os.chmod(dest.parent, 0o700)
    except OSError:
        pass
    return dest


def load_session(path: Path | None = None) -> dict | None:
    dest = path or default_path()
    if not dest.exists():
        return None
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not data.get("token"):
        return None
    return data


def clear_session(path: Path | None = None) -> None:
    dest = path or default_path()
    if dest.exists():
        dest.unlink()
