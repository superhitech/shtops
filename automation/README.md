# Automation

Guardrailed automation tasks.

**Status:** Future — build after read-only visibility is proven.

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
