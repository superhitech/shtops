# SHTops

Operational independence platform for SuperHiTech.

See [VISION.md](./VISION.md) for the full strategy and principles.

## What This Is

A context aggregation layer that pulls data from all critical systems, makes it queryable (by humans and LLMs), and enables controlled automation—without creating new lock-in.

## Status

**Phase 1: Context Layer** — In progress

## Structure

```
shtops/
├── collectors/          # System-specific data collectors
│   └── librenms/
├── cache/               # JSON state cache (gitignored)
├── clients/             # Reusable API clients
├── dashboard/           # Flask/FastAPI web UI (future)
├── automation/          # Guardrailed automation tasks (future)
├── docs/                # Additional documentation
├── config/              # Configuration templates
└── scripts/             # Utility scripts
```

## Getting Started

```bash
# Clone
git clone <repo-url>
cd shtops

# Create config from template
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API keys and endpoints

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# (Recommended) Install the local package + console script
pip install -e .

# Run a collector
python -m collectors.librenms.collect

# Show unified status from cached collector outputs
shtops status
```

## Principles

1. Systems remain fully functional without SHTops
2. Read-only first, automation second
3. No destructive automation without human confirmation
4. Separate concerns: dashboard, automation, execution
5. Version control everything
6. Document as you go

## License

Internal use only — SuperHiTech
