# FreePBX Collector (AMI)

SHTops uses **AMI (Asterisk Manager Interface)** as the supported integration for FreePBX/Asterisk.

The older GraphQL/OAuth approach is retired because it is not consistently available across FreePBX builds and provides less operationally useful data.

## Configuration

Set AMI credentials in `config/config.yaml`:

```yaml
freepbx:
  ami_host: "192.168.5.24"
  ami_port: 5038
  ami_username: "your-ami-username"
  ami_password: "your-ami-password"
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
python3 test_freepbx_ami.py
python3 -m collectors.freepbx.collect
```

## Common Issues

### AMI Authentication Failed
- Confirm the user exists: `asterisk -rx 'manager show users'`
- Confirm effective ACLs: `asterisk -rx 'manager show user <username>'`
- Watch for duplicate user sections in `manager_custom.conf` overriding `permit` rules

### AMI Not Listening / IPv6 Only
- Verify binding: `ss -lntp | grep 5038`
- See `FIX_AMI_IPV6_ISSUE.md`
