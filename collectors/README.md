# Collectors

Each subdirectory contains a collector for a specific system.

## Pattern

Every collector should:

1. Read config from `config/config.yaml`
2. Pull data from the system's API
3. Write state to `cache/<system>.json` with a timestamp
4. Be runnable standalone: `python -m collectors.<system>.collect`

## Collectors

| System | Status | Notes |
|--------|--------|-------|
| LibreNMS | Planned | Alerts, devices, health metrics |
| Proxmox | Planned | VMs, nodes, cluster status |
| FreePBX | Planned | Trunks, call metrics, module status |
| UniFi | Planned | Devices, firmware, clients |
