# FreePBX Collector

Pulls PBX status, extensions, trunks, queues, active calls, and system health from FreePBX.

## API Requirements

FreePBX uses REST API with basic authentication. The API is typically available at:
- `https://your-freepbx/admin/api/api/`

### Enabling API Access

1. **Log into FreePBX Admin Panel**
2. **Go to:** Settings → Advanced Settings
3. **Enable REST Apps**: Set to "Yes"
4. **Set API User**: Create or use admin credentials

Alternatively, use the **API Access** module if installed.

## Configuration

```yaml
freepbx:
  url: "https://pbx.example.com"
  username: "admin"
  password: "your-password-here"
  verify_ssl: false  # Set to true if using valid SSL cert
```

## Data Collected

- **System Info**: Asterisk version, uptime
- **System Status**: Overall PBX health
- **Extensions**: All configured extensions
- **Trunks**: Trunk configuration
- **Trunk Status**: Registration status for all trunks
- **Active Calls**: Currently active calls
- **Channels**: Active Asterisk channels
- **Queues**: Queue configuration
- **Queue Status**: Real-time queue statistics (waiting calls, agents)
- **Ring Groups**: Ring group configuration
- **IVR Menus**: IVR menu configuration
- **Inbound Routes (DIDs)**: DID routing configuration
- **Voicemail**: Voicemail box configuration
- **Conferences**: Conference room configuration
- **Parking Lots**: Call parking configuration

## Output

Writes to `cache/freepbx.json`:

```json
{
  "collected_at": "2024-01-15T10:30:00Z",
  "system_info": {...},
  "extensions": [...],
  "trunks": [...],
  "trunk_status": [...],
  "active_calls": [...],
  "queues": [...],
  ...
}
```

## Usage

```bash
python -m collectors.freepbx.collect
```

## Common Issues

### 403 Forbidden
- Ensure REST API is enabled in Advanced Settings
- Verify user has admin privileges

### Empty Results
- Some endpoints may return empty arrays if features aren't configured
- This is normal for unused features (queues, conferences, etc.)

### Connection Errors
- Verify FreePBX is accessible from your network
- Check firewall rules for HTTPS access
