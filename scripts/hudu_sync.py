from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.hudu_client import HuduClient


def load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def load_cache(cache_dir: Path, system: str) -> Dict[str, Any]:
    p = cache_dir / f"{system}.json"
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f) or {}


def main() -> int:
    try:
        cfg = load_config()
        hudu_cfg = cfg.get("hudu", {}) or {}
        cache_cfg = cfg.get("cache", {}) or {}

        url = hudu_cfg.get("url")
        api_key = hudu_cfg.get("api_key")
        verify_ssl = bool(hudu_cfg.get("verify_ssl", True))

        company_id = hudu_cfg.get("company_id")
        asset_layout_id = hudu_cfg.get("asset_layout_id")
        asset_name = hudu_cfg.get("asset_name", "SHTops Inventory")
        inventory_field_name = hudu_cfg.get("inventory_field_name", "Inventory JSON")

        if not url or not api_key:
            raise ValueError("hudu.url and hudu.api_key must be set in config.yaml")
        if company_id is None or asset_layout_id is None:
            raise ValueError("hudu.company_id and hudu.asset_layout_id must be set to use this scaffold")

        cache_dir = Path(cache_cfg.get("directory", "./cache"))

        inventory = {
            "librenms": load_cache(cache_dir, "librenms"),
            "proxmox": load_cache(cache_dir, "proxmox"),
            "freepbx": load_cache(cache_dir, "freepbx"),
            "unifi": load_cache(cache_dir, "unifi"),
        }

        client = HuduClient(url=url, api_key=api_key, verify_ssl=verify_ssl)

        payload = {
            "company_id": int(company_id),
            "asset_layout_id": int(asset_layout_id),
            "name": str(asset_name),
            "custom_fields": {
                str(inventory_field_name): json.dumps(inventory, indent=2),
            },
        }

        print(f"Upserting Hudu asset '{asset_name}'...")
        client.upsert_asset(company_id=int(company_id), name=str(asset_name), payload=payload)
        print("✓ Hudu sync complete")
        return 0
    except Exception as e:
        print(f"✗ Hudu sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
