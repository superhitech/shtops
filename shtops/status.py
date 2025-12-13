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


PROXMOX_CPU_WARN_PCT = 80.0
PROXMOX_CPU_CRIT_PCT = 95.0
PROXMOX_MEM_WARN_PCT = 85.0
PROXMOX_MEM_CRIT_PCT = 95.0
PROXMOX_DISK_WARN_PCT = 85.0
PROXMOX_DISK_CRIT_PCT = 95.0
PROXMOX_RECENT_REBOOT_WARN_SECONDS = 15 * 60


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _pct(used: Any, total: Any) -> Optional[float]:
    u = _safe_float(used)
    t = _safe_float(total)
    if u is None or t is None or t <= 0:
        return None
    return (u / t) * 100.0


def _cpu_pct(cpu_value: Any) -> Optional[float]:
    c = _safe_float(cpu_value)
    if c is None:
        return None
    # Proxmox commonly reports CPU as a fraction (0..1).
    if c <= 1.5:
        return c * 100.0
    return c


def _severity_from_threshold(pct: Optional[float], warn_pct: float, crit_pct: float) -> Optional[str]:
    if pct is None:
        return None
    if pct >= crit_pct:
        return "critical"
    if pct >= warn_pct:
        return "warn"
    return None


def _name_with_id(obj: Dict[str, Any], id_key: str = "vmid") -> str:
    name = obj.get("name") or obj.get("hostname") or obj.get("node") or "(unknown)"
    ident = obj.get(id_key)
    if ident is None:
        return str(name)
    return f"{name} ({id_key}={ident})"


def collect_status(cache_dir: Path, ttl_seconds: int) -> StatusReport:
    cache = {
        "librenms": load_cache_file("librenms", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
        "proxmox": load_cache_file("proxmox", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
        "freepbx": load_cache_file("freepbx", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
        "unifi": load_cache_file("unifi", cache_dir=cache_dir, ttl_seconds=ttl_seconds),
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

    # Proxmox: thresholds (nodes/VMs/CTs) and recent reboot detection
    for n in nodes:
        if not isinstance(n, dict):
            continue
        node_name = str(n.get("node") or "(unknown)")
        status = n.get("status", {}) if isinstance(n.get("status", {}), dict) else {}

        cpu_pct = _cpu_pct(status.get("cpu"))
        sev = _severity_from_threshold(cpu_pct, PROXMOX_CPU_WARN_PCT, PROXMOX_CPU_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"Node {node_name} CPU high: {cpu_pct:.1f}%")
            )

        mem = status.get("memory", {}) if isinstance(status.get("memory", {}), dict) else {}
        mem_pct = _pct(mem.get("used"), mem.get("total"))
        sev = _severity_from_threshold(mem_pct, PROXMOX_MEM_WARN_PCT, PROXMOX_MEM_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"Node {node_name} RAM high: {mem_pct:.1f}%")
            )

        rootfs = status.get("rootfs", {}) if isinstance(status.get("rootfs", {}), dict) else {}
        rootfs_pct = _pct(rootfs.get("used"), rootfs.get("total"))
        sev = _severity_from_threshold(rootfs_pct, PROXMOX_DISK_WARN_PCT, PROXMOX_DISK_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"Node {node_name} rootfs high: {rootfs_pct:.1f}%")
            )

        uptime_s = _safe_int(status.get("uptime"))
        state = str(status.get("status", "")).lower()
        if state == "online" and uptime_s is not None and uptime_s > 0 and uptime_s < PROXMOX_RECENT_REBOOT_WARN_SECONDS:
            attention.append(
                AttentionItem(
                    system="proxmox",
                    severity="warn",
                    message=f"Node {node_name} recently rebooted (uptime {uptime_s}s)",
                )
            )

    for vm in vms:
        if not isinstance(vm, dict):
            continue
        if str(vm.get("status", "")).lower() != "running":
            continue
        label = _name_with_id(vm, id_key="vmid")

        cpu_pct = _cpu_pct(vm.get("cpu"))
        sev = _severity_from_threshold(cpu_pct, PROXMOX_CPU_WARN_PCT, PROXMOX_CPU_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"VM CPU high: {label} {cpu_pct:.1f}%")
            )

        mem_pct = _pct(vm.get("mem"), vm.get("maxmem"))
        sev = _severity_from_threshold(mem_pct, PROXMOX_MEM_WARN_PCT, PROXMOX_MEM_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"VM RAM high: {label} {mem_pct:.1f}%")
            )

        disk_pct = _pct(vm.get("disk"), vm.get("maxdisk"))
        sev = _severity_from_threshold(disk_pct, PROXMOX_DISK_WARN_PCT, PROXMOX_DISK_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"VM disk high: {label} {disk_pct:.1f}%")
            )

        uptime_s = _safe_int(vm.get("uptime"))
        if uptime_s is not None and uptime_s > 0 and uptime_s < PROXMOX_RECENT_REBOOT_WARN_SECONDS:
            attention.append(
                AttentionItem(
                    system="proxmox",
                    severity="warn",
                    message=f"VM recently rebooted: {label} (uptime {uptime_s}s)",
                )
            )

    for ct in containers:
        if not isinstance(ct, dict):
            continue
        if str(ct.get("status", "")).lower() != "running":
            continue
        label = _name_with_id(ct, id_key="vmid")

        cpu_pct = _cpu_pct(ct.get("cpu"))
        sev = _severity_from_threshold(cpu_pct, PROXMOX_CPU_WARN_PCT, PROXMOX_CPU_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"CT CPU high: {label} {cpu_pct:.1f}%")
            )

        mem_pct = _pct(ct.get("mem"), ct.get("maxmem"))
        sev = _severity_from_threshold(mem_pct, PROXMOX_MEM_WARN_PCT, PROXMOX_MEM_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"CT RAM high: {label} {mem_pct:.1f}%")
            )

        disk_pct = _pct(ct.get("disk"), ct.get("maxdisk"))
        sev = _severity_from_threshold(disk_pct, PROXMOX_DISK_WARN_PCT, PROXMOX_DISK_CRIT_PCT)
        if sev:
            attention.append(
                AttentionItem(system="proxmox", severity=sev, message=f"CT disk high: {label} {disk_pct:.1f}%")
            )

        uptime_s = _safe_int(ct.get("uptime"))
        if uptime_s is not None and uptime_s > 0 and uptime_s < PROXMOX_RECENT_REBOOT_WARN_SECONDS:
            attention.append(
                AttentionItem(
                    system="proxmox",
                    severity="warn",
                    message=f"CT recently rebooted: {label} (uptime {uptime_s}s)",
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

    # UniFi: offline devices
    unifi = cache["unifi"].data or {}
    devices = unifi.get("devices", []) if isinstance(unifi.get("devices", []), list) else []
    offline = []
    for d in devices:
        if not isinstance(d, dict):
            continue
        try:
            state = int(d.get("state", 0) or 0)
        except Exception:
            state = 0
        if state != 1:
            offline.append(d.get("name") or d.get("mac") or "(unknown)")
    if offline:
        attention.append(
            AttentionItem(
                system="unifi",
                severity="warn",
                message=f"{len(offline)} UniFi device(s) offline",
            )
        )

    overall = _overall_from_items(attention)
    return StatusReport(overall_status=overall, cache=cache, attention=attention)
