# Automation

Guardrailed automation tasks.

**Status:** Future — build after read-only visibility is proven.

## systemd timer (collection)

Templates live in [automation/systemd](automation/systemd).

```bash
sudo mkdir -p /etc/shtops
sudo cp config/config.yaml /etc/shtops/config.yaml

sudo cp automation/systemd/shtops-collect.service /etc/systemd/system/
sudo cp automation/systemd/shtops-collect.timer /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now shtops-collect.timer
systemctl status shtops-collect.timer
```

## Principles

1. Pre-check before every action
2. Execute with logging
3. Validate the result
4. Rollback if possible
5. Log to Hudu

## Risk Tiers

| Risk | Requires |
|------|----------|
| Low | Scheduled, logged |
| Medium | Time windows, pre-checks, backoff |
| High | Manual confirmation |

See [VISION.md](../VISION.md) for examples of each tier.
