"""UniFi Collector

Collects device inventory and health information from UniFi Network and caches it locally.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml

# Add parent directory to path for imports (matches existing collectors)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clients.unifi_client import UniFiClient


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            "Copy config.example.yaml to config.yaml and fill in your credentials."
        )

    with open(config_path) as f:
        return yaml.safe_load(f) or {}


def ensure_cache_dir(cache_dir: str) -> Path:
    """Ensure cache directory exists."""
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> int:
    print("UniFi Collector")
    print("=" * 60)

    try:
        config = load_config()
        unifi_cfg = config.get("unifi", {}) or {}
        cache_cfg = config.get("cache", {}) or {}

        url = unifi_cfg.get("url")
        username = unifi_cfg.get("username")
        password = unifi_cfg.get("password")
        site = unifi_cfg.get("site", "default")
        verify_ssl = bool(unifi_cfg.get("verify_ssl", True))

        if not url or not username or not password:
            raise ValueError("unifi.url, unifi.username, unifi.password must be set in config.yaml")

        print(f"\nConnecting to UniFi at {url} (site={site}, verify_ssl={verify_ssl})...")
        client = UniFiClient(url=url, username=username, password=password, verify_ssl=verify_ssl)

        try:
            client.login()
        except Exception as e:
            hint = ""
            msg = str(e).lower()
            if verify_ssl and ("certificate" in msg or "ssl" in msg or "verify" in msg):
                hint = " (hint: set unifi.verify_ssl: false if using a self-signed cert)"
            raise ConnectionError(f"Failed to connect/authenticate to UniFi API: {e}{hint}")

        print("✓ Authenticated")
        sites = client.list_sites()
        devices = client.get_devices(site=site)
        health = client.get_health(site=site)

        data = {
            "collected_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "site": site,
            "sites": sites,
            "devices": devices,
            "health": health,
        }

        cache_dir = ensure_cache_dir(cache_cfg.get("directory", "./cache"))
        output_file = cache_dir / "unifi.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nCache saved to: {output_file}")
        print(f"Devices: {len(devices)} | Health entries: {len(health)}")
        print("\n✓ Collection complete")
        return 0

    except Exception as e:
        print(f"\n✗ Collection failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
