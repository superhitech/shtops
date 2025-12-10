# Proxmox Collector

Pulls cluster status, node health, VM/container status, and storage information from Proxmox VE.

## API Authentication

Uses Proxmox API tokens for authentication (more secure than username/password).

### Creating an API Token

1. Log into Proxmox web UI
2. Go to: Datacenter → Permissions → API Tokens
3. Click "Add" and create a token:
   - User: `root@pam` (or your API user)
   - Token ID: `shtops`
   - Privilege Separation: Unchecked (or assign appropriate permissions)
4. Copy the token value (UUID format)

## Configuration

```yaml
proxmox:
  url: "https://proxmox.example.com:8006"
  user: "root@pam"
  token_name: "shtops"
  token_value: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  verify_ssl: false  # Set to true if using valid SSL cert
```

## Data Collected

- **Version**: Proxmox VE version
- **Cluster Status**: Nodes, quorum status
- **Cluster Resources**: Complete resource overview
- **Nodes**: Status, CPU, memory, uptime for each node
- **VMs (QEMU)**: All virtual machines and their status
- **Containers (LXC)**: All containers and their status
- **Storage**: Storage pools and usage
- **Resource Pools**: Defined resource pools
- **HA Resources**: High availability managed resources
- **Recent Tasks**: Last 50 tasks with status

## Output

Writes to `cache/proxmox.json`:

```json
{
  "collected_at": "2024-01-15T10:30:00Z",
  "version": {...},
  "cluster": {...},
  "nodes": [...],
  "vms": [...],
  "containers": [...],
  "storage": [...],
  "pools": [...],
  "ha_resources": [...],
  "recent_tasks": [...]
}
```

## Usage

```bash
python -m collectors.proxmox.collect
```

## Permissions

Minimum required permissions for the API token:
- VM.Audit (for VM/container status)
- Datastore.Audit (for storage information)
- Sys.Audit (for node and cluster status)
