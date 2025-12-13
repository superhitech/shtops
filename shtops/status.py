from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import CacheFile, load_cache_file


@dataclass(frozen=True)
class AttentionItem:
    system: str
    severity: str  # ok|warn|critical
    message: str


@dataclass(frozen=True)
class StatusReport:
    overall_status: str  # ok|warn|critical
    cache: Dict[str, CacheFile]
    attention: List[AttentionItem]


def _severity_rank(sev: str) -> int:
    return {"ok": 0, "warn": 1, "critical": 2}.get(sev, 1)


def _overall_from_items(items: List[AttentionItem]) -> str:
    if not items:
        return "ok"
    worst = max(items, key=lambda i: _severity_rank(i.severity))
    return worst.severity


def _fmt_age(age_seconds: Optional[int]) -> str:
    if age_seconds is None:
        return "unknown"
    if age_seconds < 60:
        return f"{age_seconds}s"
    minutes = age_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    minutes = minutes % 60
    if hours < 48:
        return f"{hours}h{minutes:02d}m"
    days = hours // 24
    hours = hours % 24
    return f"{days}d{hours:02d}h"


def collect_status(cache_dir: Path, ttl_seconds: int) -> StatusReport:
    cache = {
        "librenms": load_cache_file("librenms", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
        "proxmox": load_cache_file("proxmox", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
        "freepbx": load_cache_file("freepbx", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
    }

    attention: List[AttentionItem] = []

    # Cache freshness issues
    for system, cf in cache.items():
        if cf.error:
            attention.append(AttentionItem(system=system, severity="warn", message=f"cache read error: {cf.error}"))
            continue
        if not cf.exists:
            attention.append(AttentionItem(system=system, severity="warn", message=f"no cache file at {cf.path}"))
            continue
        if not cf.collected_at:
            attention.append(AttentionItem(system=system, severity="warn", message="cache missing collected_at timestamp"))
            continue
        if not cf.is_fresh:
            attention.append(
                AttentionItem(
                    system=system,
                    severity="warn",
                    message=f"cache is stale (age {_fmt_age(cf.age_seconds)}, ttl {ttl_seconds}s)",
                )
            )

    # LibreNMS: active alerts
    librenms = cache["librenms"].data or {}
    alerts = librenms.get("alerts", []) if isinstance(librenms.get("alerts", []), list) else []
    active_alerts = [a for a in alerts if str(a.get("state")) == "1" or a.get("state") == 1]
    if active_alerts:
        attention.append(
            AttentionItem(
                system="librenms",
                severity="critical",
                message=f"{len(active_alerts)} active LibreNMS alert(s)",
            )
        )

    # Proxmox: node/VM/container down
    proxmox = cache["proxmox"].data or {}
    nodes = proxmox.get("nodes", []) if isinstance(proxmox.get("nodes", []), list) else []

    # Collector stores nodes as objects with keys: node, info, status, ...
    down_nodes: List[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        node_name = n.get("node") or (n.get("info", {}) if isinstance(n.get("info", {}), dict) else {}).get("node")
        status = n.get("status", {}) if isinstance(n.get("status", {}), dict) else {}
        # Proxmox status payload often has 'status': 'online'|'offline'
        state = str(status.get("status", "")).lower()
        if state in {"offline", "unknown"}:
            if node_name:
                down_nodes.append(str(node_name))

    if down_nodes:
        attention.append(
            AttentionItem(
                system="proxmox",
                severity="critical",
                message=f"Proxmox node(s) offline: {', '.join(sorted(set(down_nodes)))}",
            )
        )

    vms = proxmox.get("vms", []) if isinstance(proxmox.get("vms", []), list) else []
    stopped_vms = [vm for vm in vms if isinstance(vm, dict) and str(vm.get("status", "")).lower() == "stopped"]
    if stopped_vms:
        attention.append(
            AttentionItem(
                system="proxmox",
                severity="warn",
                message=f"{len(stopped_vms)} VM(s) stopped",
            )
        )

    containers = proxmox.get("containers", []) if isinstance(proxmox.get("containers", []), list) else []
    stopped_cts = [ct for ct in containers if isinstance(ct, dict) and str(ct.get("status", "")).lower() == "stopped"]
    if stopped_cts:
        attention.append(
            AttentionItem(
                system="proxmox",
                severity="warn",
                message=f"{len(stopped_cts)} container(s) stopped",
            )
        )

    # FreePBX: trunk registration
    freepbx = cache["freepbx"].data or {}
    trunks = freepbx.get("trunks", []) if isinstance(freepbx.get("trunks", []), list) else []
    not_registered = []
    for t in trunks:
        if not isinstance(t, dict):
            continue
        state = str(t.get("state", ""))
        if "Registered" not in state:
            name = t.get("name") or t.get("trunk") or t.get("username") or "(unknown trunk)"
            not_registered.append(str(name))
    if not_registered:
        attention.append(
            AttentionItem(
                system="freepbx",
                severity="critical",
                message=f"FreePBX trunk(s) not registered: {', '.join(sorted(set(not_registered)))}",
            )
        )

    overall = _overall_from_items(attention)
    return StatusReport(overall_status=overall, cache=cache, attention=attention)
