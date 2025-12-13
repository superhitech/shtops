from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f) or {}
    if isinstance(data, dict):
        return data
    return {}


def load_inventory(cache_dir: Path) -> Dict[str, Any]:
    """Load current cached inventory for syncing.

    This is intentionally simple: it mirrors the cache JSON objects so other
    systems (Hudu/LLMs) can consume full-fidelity state.
    """
    return {
        "librenms": _load_json(cache_dir / "librenms.json"),
        "proxmox": _load_json(cache_dir / "proxmox.json"),
        "freepbx": _load_json(cache_dir / "freepbx.json"),
        "unifi": _load_json(cache_dir / "unifi.json"),
    }
