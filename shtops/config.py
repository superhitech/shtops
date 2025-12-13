from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass(frozen=True)
class CacheConfig:
    directory: str = "./cache"
    default_ttl_seconds: int = 300


@dataclass(frozen=True)
class AppConfig:
    cache: CacheConfig


def _repo_root() -> Path:
    # This file lives at <repo>/shtops/config.py
    return Path(__file__).resolve().parent.parent


def load_raw_config(config_path: Path | None = None) -> Dict[str, Any]:
    if config_path is None:
        config_path = _repo_root() / "config" / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. "
            "Copy config/config.example.yaml to config/config.yaml and fill in your credentials."
        )

    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config at {config_path} must be a YAML mapping")

    return data


def load_app_config(config_path: Path | None = None) -> AppConfig:
    raw = load_raw_config(config_path=config_path)
    cache_raw = raw.get("cache", {}) if isinstance(raw.get("cache", {}), dict) else {}

    cache = CacheConfig(
        directory=str(cache_raw.get("directory", "./cache")),
        default_ttl_seconds=int(cache_raw.get("default_ttl_seconds", 300)),
    )

    return AppConfig(cache=cache)
