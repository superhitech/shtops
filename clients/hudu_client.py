"""Hudu API client (minimal scaffold)

Hudu API payload shapes can vary by version; this client is intended as a
starting point for MVP sync.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class HuduClient:
    def __init__(self, url: str, api_key: str, verify_ssl: bool = True):
        self.url = url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-API-Key": api_key,
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> Any:
        kwargs.setdefault("verify", self.verify_ssl)
        resp = self.session.request(method, f"{self.url}{path}", **kwargs)
        if resp.status_code >= 400:
            raise RuntimeError(f"Hudu API {method} {path} failed: {resp.status_code} {resp.text[:400]}")
        if resp.content:
            return resp.json()
        return {}

    def find_asset_by_name(self, company_id: int, name: str) -> Optional[Dict[str, Any]]:
        data = self._request("GET", "/api/v1/assets", params={"company_id": company_id, "name": name})

        assets = []
        if isinstance(data, dict):
            assets = data.get("assets") or data.get("data") or []

        if isinstance(assets, list):
            for a in assets:
                if isinstance(a, dict) and str(a.get("name", "")).strip() == name.strip():
                    return a

        return None

    def create_asset(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Try unwrapped then wrapped.
        try:
            return self._request("POST", "/api/v1/assets", json=payload)
        except Exception:
            return self._request("POST", "/api/v1/assets", json={"asset": payload})

    def update_asset(self, asset_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._request("PUT", f"/api/v1/assets/{asset_id}", json=payload)
        except Exception:
            return self._request("PUT", f"/api/v1/assets/{asset_id}", json={"asset": payload})

    def upsert_asset(self, company_id: int, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.find_asset_by_name(company_id=company_id, name=name)
        if existing and existing.get("id"):
            return self.update_asset(int(existing["id"]), payload)
        return self.create_asset(payload)
