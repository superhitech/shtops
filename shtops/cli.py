from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .config import load_app_config
from .status import collect_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _print_report(report, as_json: bool = False) -> int:
    if as_json:
        payload = {
            "overall_status": report.overall_status,
            "cache": {
                name: {
                    "path": str(cf.path),
                    "exists": cf.exists,
                    "collected_at": cf.collected_at.isoformat().replace("+00:00", "Z") if cf.collected_at else None,
                    "age_seconds": cf.age_seconds,
                    "is_fresh": cf.is_fresh,
                    "error": cf.error,
                }
                for name, cf in report.cache.items()
            },
            "attention": [
                {"system": a.system, "severity": a.severity, "message": a.message}
                for a in report.attention
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if report.overall_status == "ok" else 2

    print(f"Overall: {report.overall_status.upper()}")
    print("Cache:")
    for name, cf in report.cache.items():
        freshness = "fresh" if cf.is_fresh else "stale"
        if not cf.exists:
            freshness = "missing"
        if cf.error:
            freshness = "error"

        age = "?" if cf.age_seconds is None else str(cf.age_seconds)
        print(f"  - {name}: {freshness} (age={age}s) -> {cf.path}")

    if report.attention:
        print("Attention:")
        for item in report.attention:
            print(f"  - [{item.severity}] {item.system}: {item.message}")
    else:
        print("Attention: none")

    return 0 if report.overall_status == "ok" else 2


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: ./config/config.yaml)",
    )
    p.add_argument(
        "--cache-dir",
        default=None,
        help="Override cache directory (default: from config.cache.directory)",
    )
    p.add_argument(
        "--ttl",
        type=int,
        default=None,
        help="Override cache TTL seconds (default: from config.cache.default_ttl_seconds)",
    )
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(prog="shtops")
    sub = parser.add_subparsers(dest="cmd")

    p_status = sub.add_parser("status", help="Show unified status from cache")
    _add_common_args(p_status)

    p_attention = sub.add_parser("attention", help="Alias for status")
    _add_common_args(p_attention)

    p_collect = sub.add_parser("collect", help="Run collectors then show status")
    p_collect.add_argument(
        "--systems",
        nargs="+",
        choices=["librenms", "proxmox", "freepbx", "unifi"],
        default=["librenms", "proxmox", "freepbx", "unifi"],
        help="Which collectors to run (default: all)",
    )
    _add_common_args(p_collect)

    # Default command if none given
    args = parser.parse_args(argv)
    cmd = args.cmd or "status"

    config_path = Path(args.config) if args.config else (_repo_root() / "config" / "config.yaml")
    app_cfg = load_app_config(config_path=config_path)

    cache_dir = Path(args.cache_dir) if args.cache_dir else Path(app_cfg.cache.directory)
    ttl = int(args.ttl) if args.ttl is not None else int(app_cfg.cache.default_ttl_seconds)

    if cmd == "collect":
        repo_root = _repo_root()
        python_exe = sys.executable
        failures: list[str] = []

        for system in args.systems:
            module = f"collectors.{system}.collect"
            print(f"Running collector: {system} ({module})")
            result = subprocess.run(
                [python_exe, "-m", module],
                cwd=str(repo_root),
            )
            if result.returncode != 0:
                failures.append(system)

        if failures:
            print(f"One or more collectors failed: {', '.join(failures)}", file=sys.stderr)

        report = collect_status(cache_dir=cache_dir, ttl_seconds=ttl)
        exit_code = _print_report(report, as_json=bool(args.json))

        # Preserve collector failure as non-zero.
        if failures and exit_code == 0:
            return 1
        return exit_code

    report = collect_status(cache_dir=cache_dir, ttl_seconds=ttl)
    return _print_report(report, as_json=bool(args.json))


if __name__ == "__main__":
    raise SystemExit(main())
