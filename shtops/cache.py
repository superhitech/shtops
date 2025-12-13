from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from dateutil import parser as date_parser


@dataclass(frozen=True)
class CacheFile:
    system: str
    path: Path
    exists: bool
    collected_at: Optional[datetime]
    age_seconds: Optional[int]
    is_fresh: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def _parse_collected_at(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    try:
        dt = date_parser.isoparse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def load_cache_file(system: str, cache_dir: Path, ttl_seconds: int) -> CacheFile:
    path = cache_dir / f"{system}.json"

    if not path.exists():
        return CacheFile(
            system=system,
            path=path,
            exists=False,
            collected_at=None,
            age_seconds=None,
            is_fresh=False,
            data=None,
            error=None,
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("cache JSON must be an object")

        collected_at = _parse_collected_at(data.get("collected_at"))
        now = datetime.now(timezone.utc)

        age_seconds: Optional[int] = None
        is_fresh = False
        if collected_at is not None:
            age_seconds = max(0, int((now - collected_at).total_seconds()))
            is_fresh = age_seconds <= ttl_seconds

        return CacheFile(
            system=system,
            path=path,
            exists=True,
            collected_at=collected_at,
            age_seconds=age_seconds,
            is_fresh=is_fresh,
            data=data,
            error=None,
        )
    except Exception as e:
        return CacheFile(
            system=system,
            path=path,
            exists=True,
            collected_at=None,
            age_seconds=None,
            is_fresh=False,
            data=None,
            error=str(e),
        )
