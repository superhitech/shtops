from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.hudu_client import HuduClient
from shtops.hudu_sync import HuduSyncConfig, resolve_asset_layout_id, resolve_company_id, sync_inventory_to_hudu
from shtops.inventory import load_inventory


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f) or {}

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync SHTops inventory cache to Hudu")
    p.add_argument("--config", default=None, help="Path to config.yaml (default: ./config/config.yaml)")
    p.add_argument("--cache-dir", default=None, help="Cache directory (default: from config.cache.directory)")

    # Company targeting
    p.add_argument("--company-id", type=int, default=None, help="Hudu company id")
    p.add_argument(
        "--company",
        dest="company_key",
        default=None,
        help="Company key/name to resolve via hudu.company_map (falls back to hudu.default_company_id)",
    )

    # Asset targeting
    p.add_argument("--asset-layout-id", type=int, default=None, help="Hudu asset layout id")
    p.add_argument("--asset-name", default=None, help="Asset name (default: hudu.asset_name or 'SHTops Inventory')")
    p.add_argument(
        "--field-name",
        default=None,
        help="Custom field name to store inventory JSON (default: hudu.inventory_field_name or 'Inventory JSON')",
    )

    return p.parse_args(argv)


def main() -> int:
    try:
        args = _parse_args(sys.argv[1:])
        repo_root = _repo_root()
        config_path = Path(args.config) if args.config else (repo_root / "config" / "config.yaml")

        cfg = load_config(config_path=config_path)
        hudu_cfg = cfg.get("hudu", {}) or {}
        cache_cfg = cfg.get("cache", {}) or {}

        url = hudu_cfg.get("url")
        api_key = hudu_cfg.get("api_key")
        verify_ssl = bool(hudu_cfg.get("verify_ssl", True))

        sync_cfg = HuduSyncConfig(
            url=str(url or ""),
            api_key=str(api_key or ""),
            verify_ssl=verify_ssl,
            default_company_id=hudu_cfg.get("default_company_id"),
            default_asset_layout_id=hudu_cfg.get("default_asset_layout_id"),
            asset_name=str(hudu_cfg.get("asset_name", "SHTops Inventory")),
            inventory_field_name=str(hudu_cfg.get("inventory_field_name", "Inventory JSON")),
            company_map=dict(hudu_cfg.get("company_map", {}) or {}),
        )

        if not sync_cfg.url or not sync_cfg.api_key:
            raise ValueError("hudu.url and hudu.api_key must be set in config.yaml")

        client = HuduClient(url=sync_cfg.url, api_key=sync_cfg.api_key, verify_ssl=sync_cfg.verify_ssl)

        company_id = resolve_company_id(sync_cfg, args.company_key, args.company_id)
        asset_layout_id = resolve_asset_layout_id(sync_cfg, args.asset_layout_id)
        asset_name = args.asset_name or sync_cfg.asset_name
        inventory_field_name = args.field_name or sync_cfg.inventory_field_name

        if company_id is None or asset_layout_id is None:
            print("Missing required targeting: company_id and/or asset_layout_id", file=sys.stderr)
            print("Provide via flags or config:")
            print("- flags: --company-id / --company and --asset-layout-id")
            print("- config: hudu.default_company_id and hudu.default_asset_layout_id")
            print("- mapping: hudu.company_map")
            print("\nBest-effort listings to find IDs:")
            try:
                companies = client.list_companies()
                print("\nCompanies response (truncated):")
                print(str(companies)[:800])
            except Exception as e:
                print(f"\nCould not list companies: {e}", file=sys.stderr)
            try:
                layouts = client.list_asset_layouts()
                print("\nAsset layouts response (truncated):")
                print(str(layouts)[:800])
            except Exception as e:
                print(f"\nCould not list asset layouts: {e}", file=sys.stderr)
            return 1

        cache_dir = Path(args.cache_dir) if args.cache_dir else Path(cache_cfg.get("directory", "./cache"))
        inventory = load_inventory(cache_dir=cache_dir)

        print(f"Upserting Hudu asset '{asset_name}' (company_id={company_id}, asset_layout_id={asset_layout_id})...")
        sync_inventory_to_hudu(
            hudu=client,
            company_id=int(company_id),
            asset_layout_id=int(asset_layout_id),
            asset_name=str(asset_name),
            inventory_field_name=str(inventory_field_name),
            inventory=inventory,
        )
        print("✓ Hudu sync complete")
        return 0
    except Exception as e:
        print(f"✗ Hudu sync failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
