"""UniFi Network API Client (minimal)

Supports common controller endpoints for:
- login
- list sites
- device inventory
- health stats

Read-only usage for the SHTops context layer.
"""

from __future__ import annotations

from typing import Any, Dict, List

import requests


class UniFiClient:
    def __init__(self, url: str, username: str, password: str, verify_ssl: bool = True):
        self.url = url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        # UniFi OS controllers often require /proxy/network.
        self._prefix: str = ""

    def _request(self, method: str, path: str, **kwargs) -> Any:
        kwargs.setdefault("verify", self.verify_ssl)
        url = f"{self.url}{self._prefix}{path}"
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        if resp.content:
            return resp.json()
        return {}

    def login(self) -> None:
        payload = {"username": self.username, "password": self.password, "rememberMe": True}

        # Try (modern, legacy) x (direct, unifi-os proxy).
        for prefix in ("", "/proxy/network"):
            self._prefix = prefix
            for path in ("/api/auth/login", "/api/login"):
                try:
                    self._request("POST", path, json=payload)
                    return
                except Exception:
                    continue

        raise ConnectionError("UniFi login failed (tried /api/auth/login and /api/login with/without /proxy/network)")

    def list_sites(self) -> List[Dict[str, Any]]:
        data = self._request("GET", "/api/self/sites")
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data, list):
            return data
        return []

    def get_devices(self, site: str = "default") -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/s/{site}/stat/device")
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []

    def get_health(self, site: str = "default") -> List[Dict[str, Any]]:
        data = self._request("GET", f"/api/s/{site}/stat/health")
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            return data["data"]
        return []

    def test_connection(self) -> bool:
        try:
            self.login()
            self.list_sites()
            return True
        except Exception:
            return False
