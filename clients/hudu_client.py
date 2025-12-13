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

    def list_company_assets_page(self, company_id: int, page: int = 1, per_page: int = 100) -> Any:
        return self._request(
            "GET",
            f"/api/v1/companies/{int(company_id)}/assets",
            params={"page": page, "per_page": per_page},
        )

    def find_asset_by_name(self, company_id: int, name: str) -> Optional[Dict[str, Any]]:
        target = name.strip()
        for page in range(1, 101):
            data = self.list_company_assets_page(company_id=company_id, page=page, per_page=100)
            assets = data.get("assets", []) if isinstance(data, dict) else []
            if not assets:
                return None

            for a in assets:
                if isinstance(a, dict) and str(a.get("name", "")).strip() == target:
                    return a

        return None

    def create_asset(self, company_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        # This Hudu instance supports create via company-scoped route.
        try:
            return self._request("POST", f"/api/v1/companies/{int(company_id)}/assets", json=payload)
        except Exception:
            return self._request("POST", f"/api/v1/companies/{int(company_id)}/assets", json={"asset": payload})

    def update_asset(self, company_id: int, asset_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._request(
                "PUT",
                f"/api/v1/companies/{int(company_id)}/assets/{int(asset_id)}",
                json=payload,
            )
        except Exception:
            return self._request(
                "PUT",
                f"/api/v1/companies/{int(company_id)}/assets/{int(asset_id)}",
                json={"asset": payload},
            )

    def upsert_asset(self, company_id: int, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.find_asset_by_name(company_id=company_id, name=name)
        if existing and existing.get("id"):
            return self.update_asset(company_id=int(company_id), asset_id=int(existing["id"]), payload=payload)
        return self.create_asset(company_id=int(company_id), payload=payload)

    def list_companies(self) -> Any:
        return self._request("GET", "/api/v1/companies")

    def list_companies_page(self, page: int = 1, per_page: int = 100) -> Any:
        return self._request("GET", "/api/v1/companies", params={"page": page, "per_page": per_page})

    def find_company(self, *, full_url: str | None = None, slug: str | None = None, name: str | None = None) -> Optional[Dict[str, Any]]:
        """Best-effort company lookup.

        Hudu company listings are paginated; this walks pages until it finds a match.
        """
        target_full_url = (full_url or "").strip()
        target_slug = (slug or "").strip()
        target_name = (name or "").strip().lower()

        for page in range(1, 101):
            data = self.list_companies_page(page=page, per_page=100)
            companies = data.get("companies", []) if isinstance(data, dict) else []
            if not companies:
                return None
            for c in companies:
                if not isinstance(c, dict):
                    continue
                if target_full_url and str(c.get("full_url", "")) == target_full_url:
                    return c
                if target_slug and str(c.get("slug", "")) == target_slug:
                    return c
                if target_name and str(c.get("name", "")).strip().lower() == target_name:
                    return c
        return None

    def list_asset_layouts(self) -> Any:
        return self._request("GET", "/api/v1/asset_layouts")
