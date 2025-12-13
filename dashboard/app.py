from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, render_template_string

from shtops.config import load_app_config, load_raw_config
from shtops.status import collect_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_path(repo_root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (repo_root / p)


app = Flask(__name__)


TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\"/>
    <title>SHTops Dashboard</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
      .tile { border: 1px solid #ddd; border-radius: 8px; padding: 12px; }
      .sev-ok { color: #0a7a20; }
      .sev-warn { color: #b36b00; }
      .sev-critical { color: #b00020; }
      .muted { color: #666; font-size: 0.9em; }
      a { color: inherit; }
    </style>
  </head>
  <body>
    <h1>SHTops</h1>
    <p class=\"muted\">Overall: <strong class=\"sev-{{ overall }}\">{{ overall.upper() }}</strong></p>

    <div class=\"grid\">
      {% for s in systems %}
        <div class=\"tile\">
          <h2>{{ s.name }}</h2>
          {% if s.url %}<p><a href=\"{{ s.url }}\" target=\"_blank\" rel=\"noreferrer\">Open native UI</a></p>{% endif %}
          <p class=\"muted\">Cache: {{ s.cache_state }}</p>
          <p>Attention: <span class=\"sev-critical\">{{ s.critical }}</span> critical, <span class=\"sev-warn\">{{ s.warn }}</span> warn</p>
        </div>
      {% endfor %}
    </div>

    <h2>Attention</h2>
    {% if attention %}
      <ul>
        {% for a in attention %}
          <li><strong class=\"sev-{{ a.severity }}\">{{ a.severity }}</strong> {{ a.system }} — {{ a.message }}</li>
        {% endfor %}
      </ul>
    {% else %}
      <p class=\"muted\">none</p>
    {% endif %}
  </body>
</html>
"""


@app.get("/")
def index():
    repo_root = _repo_root()
    config_path = Path(os.environ.get("SHTOPS_CONFIG") or (repo_root / "config" / "config.yaml"))

    raw = load_raw_config(config_path=config_path)
    app_cfg = load_app_config(config_path=config_path)

    cache_dir = _resolve_path(repo_root, str(app_cfg.cache.directory))
    ttl = int(app_cfg.cache.default_ttl_seconds)

    report = collect_status(cache_dir=cache_dir, ttl_seconds=ttl)

    def cache_state(system: str) -> str:
        cf = report.cache.get(system)
        if not cf:
            return "missing"
        if cf.error:
            return "error"
        if not cf.exists:
            return "missing"
        return "fresh" if cf.is_fresh else "stale"

    def counts(system: str) -> dict[str, int]:
        warn = sum(1 for a in report.attention if a.system == system and a.severity == "warn")
        crit = sum(1 for a in report.attention if a.system == system and a.severity == "critical")
        return {"warn": warn, "critical": crit}

    systems = [
        {"key": "librenms", "name": "LibreNMS", "url": (raw.get("librenms", {}) or {}).get("url")},
        {"key": "proxmox", "name": "Proxmox", "url": (raw.get("proxmox", {}) or {}).get("url")},
        {"key": "freepbx", "name": "FreePBX", "url": (raw.get("freepbx", {}) or {}).get("url")},
        {"key": "unifi", "name": "UniFi", "url": (raw.get("unifi", {}) or {}).get("url")},
    ]

    for s in systems:
        c = counts(s["key"])
        s["warn"] = c["warn"]
        s["critical"] = c["critical"]
        s["cache_state"] = cache_state(s["key"])

    return render_template_string(
        TEMPLATE,
        overall=report.overall_status,
        systems=systems,
        attention=report.attention,
    )


def main() -> int:
    app.run(host=os.environ.get("SHTOPS_HOST", "127.0.0.1"), port=int(os.environ.get("SHTOPS_PORT", "5000")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
