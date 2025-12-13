from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from clients.hudu_client import HuduClient


@dataclass(frozen=True)
class HuduSyncConfig:
    url: str
    api_key: str
    verify_ssl: bool = True

    default_company_id: Optional[int] = None
    default_asset_layout_id: Optional[int] = None

    asset_name: str = "SHTops Inventory"
    inventory_field_name: str = "Inventory JSON"

    # external_key/name -> company id
    company_map: Dict[str, int] | None = None


def resolve_company_id(cfg: HuduSyncConfig, company_key: Optional[str], company_id: Optional[int]) -> Optional[int]:
    if company_id is not None:
        return int(company_id)

    if company_key:
        m = cfg.company_map or {}
        if company_key in m:
            return int(m[company_key])

    if cfg.default_company_id is not None:
        return int(cfg.default_company_id)

    return None


def resolve_asset_layout_id(cfg: HuduSyncConfig, asset_layout_id: Optional[int]) -> Optional[int]:
    if asset_layout_id is not None:
        return int(asset_layout_id)
    if cfg.default_asset_layout_id is not None:
        return int(cfg.default_asset_layout_id)
    return None


def sync_inventory_to_hudu(
    *,
    hudu: HuduClient,
    company_id: int,
    asset_layout_id: int,
    asset_name: str,
    inventory_field_name: str,
    inventory: Dict[str, Any],
) -> Dict[str, Any]:
    payload = {
        "company_id": int(company_id),
        "asset_layout_id": int(asset_layout_id),
        "name": str(asset_name),
        "custom_fields": {
            str(inventory_field_name): json.dumps(inventory, indent=2),
        },
    }

    return hudu.upsert_asset(company_id=int(company_id), name=str(asset_name), payload=payload)
