# LibreNMS Collector

Pulls alerts, device status, and health metrics from LibreNMS.

## API Endpoints Used

- `GET /api/v0/devices` — Device inventory
- `GET /api/v0/alerts` — Active alerts
- `GET /api/v0/health` — Health metrics (CPU, memory, disk, etc.)

## Output

Writes to `cache/librenms.json`:

```json
{
  "collected_at": "2024-01-15T10:30:00Z",
  "devices": [...],
  "alerts": [...],
  "health": [...]
}
```

## Usage

```bash
python -m collectors.librenms.collect
```
