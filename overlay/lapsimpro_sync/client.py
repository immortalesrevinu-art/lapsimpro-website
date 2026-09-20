"""HTTP client for lapsimpro.com account + training sync."""

from __future__ import annotations

from typing import Any

import httpx

from .store import load_session, save_session


class AccountClient:
    def __init__(self, api_url: str, token: str | None = None, timeout: float = 15.0):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, url, headers=self._headers(), **kwargs)
        try:
            data = response.json()
        except ValueError:
            data = {"detail": response.text}
        if response.status_code >= 400:
            detail = data.get("detail") if isinstance(data, dict) else data
            raise RuntimeError(f"{method} {path} failed ({response.status_code}): {detail}")
        return data if isinstance(data, dict) else {"data": data}

    def login(self, email: str, password: str, device_name: str = "overlay") -> dict[str, Any]:
        data = self._request(
            "POST",
            "/api/auth/login",
            json={"email": email, "password": password, "device_name": device_name},
        )
        self.token = data.get("token") or data.get("access_token")
        save_session(self.token, self.api_url, email)
        return data

    def me(self) -> dict[str, Any]:
        return self._request("GET", "/me")

    def entitlement(self) -> dict[str, Any]:
        return self._request("GET", "/api/entitlement")

    def sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {"schema": "lapsimpro.session.v1", **payload}
        return self._request("POST", "/sessions", json=body)

    def dashboard(self) -> dict[str, Any]:
        return self._request("GET", "/api/dashboard")

    @classmethod
    def from_saved(cls) -> "AccountClient":
        saved = load_session()
        if not saved:
            raise RuntimeError("Not signed in. Run: python -m lapsimpro_sync login")
        return cls(saved["api_url"], saved["token"])
