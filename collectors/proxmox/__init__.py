"""Proxmox Collector

Collects cluster status, node health, VM/container status, and storage
information from Proxmox VE and caches locally.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clients.proxmox_client import ProxmoxClient


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            "Copy config.example.yaml to config.yaml and fill in your credentials."
        )
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def ensure_cache_dir(cache_dir: str) -> Path:
    """Ensure cache directory exists."""
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def collect_proxmox_data(client: ProxmoxClient) -> Dict[str, Any]:
    """
    Collect all relevant data from Proxmox.
    
    Args:
        client: Initialized Proxmox client
        
    Returns:
        Dictionary with collected data
    """
    print("Collecting Proxmox data...")
    
    data = {
        'collected_at': datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
        'version': {},
        'cluster': {
            'status': [],
            'resources': []
        },
        'nodes': [],
        'vms': [],
        'containers': [],
        'storage': [],
        'pools': [],
        'ha_resources': [],
        'recent_tasks': []
    }
    
    # Get version
    print("  - Fetching version...")
    try:
        data['version'] = client.get_version()
        version_str = data['version'].get('version', 'unknown')
        print(f"    Proxmox VE {version_str}")
    except Exception as e:
        print(f"    Warning: Could not fetch version: {e}")
    
    # Get cluster status
    print("  - Fetching cluster status...")
    try:
        data['cluster']['status'] = client.get_cluster_status()
        print(f"    Found {len(data['cluster']['status'])} cluster members")
    except Exception as e:
        print(f"    Warning: Could not fetch cluster status: {e}")
    
    # Get cluster resources (comprehensive view)
    print("  - Fetching cluster resources...")
    try:
        data['cluster']['resources'] = client.get_cluster_resources()
        print(f"    Found {len(data['cluster']['resources'])} resources")
    except Exception as e:
        print(f"    Warning: Could not fetch cluster resources: {e}")
    
    # Get nodes
    print("  - Fetching nodes...")
    try:
        nodes = client.get_nodes()
        print(f"    Found {len(nodes)} nodes")
        
        for node_info in nodes:
            node_name = node_info.get('node')
            if not node_name:
                continue
            
            print(f"    - Processing node: {node_name}")
            
            # Get detailed node status
            try:
                node_status = client.get_node_status(node_name)
                node_data = {
                    'node': node_name,
                    'info': node_info,
                    'status': node_status,
                    'vms': [],
                    'containers': [],
                    'storage': []
                }
                
                # Get VMs on this node
                try:
                    vms = client.get_node_vms(node_name)
                    node_data['vms'] = vms
                    data['vms'].extend([{**vm, 'node': node_name} for vm in vms])
                except Exception as e:
                    print(f"      Warning: Could not fetch VMs: {e}")
                
                # Get containers on this node
                try:
                    containers = client.get_node_containers(node_name)
                    node_data['containers'] = containers
                    data['containers'].extend([{**ct, 'node': node_name} for ct in containers])
                except Exception as e:
                    print(f"      Warning: Could not fetch containers: {e}")
                
                # Get storage on this node
                try:
                    storage = client.get_storage(node_name)
                    node_data['storage'] = storage
                except Exception as e:
                    print(f"      Warning: Could not fetch storage: {e}")
                
                data['nodes'].append(node_data)
                
            except Exception as e:
                print(f"      Warning: Could not fetch node status: {e}")
        
    except Exception as e:
        print(f"    Warning: Could not fetch nodes: {e}")
    
    # Get storage summary
    print("  - Fetching storage...")
    try:
        storage = client.get_storage()
        data['storage'] = storage
        print(f"    Found {len(storage)} storage locations")
    except Exception as e:
        print(f"    Warning: Could not fetch storage: {e}")
    
    # Get pools
    print("  - Fetching resource pools...")
    try:
        pools = client.get_pools()
        data['pools'] = pools
        print(f"    Found {len(pools)} pools")
    except Exception as e:
        print(f"    Warning: Could not fetch pools: {e}")
    
    # Get HA resources
    print("  - Fetching HA resources...")
    try:
        ha_resources = client.get_ha_resources()
        data['ha_resources'] = ha_resources
        if ha_resources:
            print(f"    Found {len(ha_resources)} HA-managed resources")
        else:
            print(f"    HA not configured or no managed resources")
    except Exception as e:
        print(f"    Warning: Could not fetch HA resources: {e}")
    
    # Get recent tasks
    print("  - Fetching recent tasks...")
    try:
        tasks = client.get_tasks(limit=50)
        data['recent_tasks'] = tasks
        print(f"    Found {len(tasks)} recent tasks")
    except Exception as e:
        print(f"    Warning: Could not fetch tasks: {e}")
    
    return data


def save_cache(data: Dict[str, Any], cache_path: Path) -> None:
    """Save collected data to cache file."""
    output_file = cache_path / 'proxmox.json'
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nCache saved to: {output_file}")
    print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")


def print_summary(data: Dict[str, Any]) -> None:
    """Print a summary of collected data."""
    print("\n" + "="*60)
    print("Proxmox Collection Summary")
    print("="*60)
    
    version = data.get('version', {}).get('version', 'Unknown')
    print(f"\nProxmox VE Version: {version}")
    
    # Nodes summary
    nodes = data.get('nodes', [])
    print(f"\nNodes: {len(nodes)}")
    for node in nodes:
        node_name = node.get('node', 'Unknown')
        status = node.get('status', {})
        uptime = status.get('uptime', 0)
        cpu = status.get('cpu', 0) * 100
        memory_used = status.get('memory', {}).get('used', 0) / (1024**3) if isinstance(status.get('memory'), dict) else 0
        memory_total = status.get('memory', {}).get('total', 0) / (1024**3) if isinstance(status.get('memory'), dict) else 0
        
        print(f"  - {node_name}: CPU {cpu:.1f}%, RAM {memory_used:.1f}/{memory_total:.1f} GB")
    
    # VMs summary
    vms = data.get('vms', [])
    print(f"\nVirtual Machines: {len(vms)}")
    vm_status_counts = {}
    for vm in vms:
        status = vm.get('status', 'unknown')
        vm_status_counts[status] = vm_status_counts.get(status, 0) + 1
    
    for status, count in sorted(vm_status_counts.items()):
        print(f"  {status}: {count}")
    
    # Containers summary
    containers = data.get('containers', [])
    print(f"\nContainers (LXC): {len(containers)}")
    ct_status_counts = {}
    for ct in containers:
        status = ct.get('status', 'unknown')
        ct_status_counts[status] = ct_status_counts.get(status, 0) + 1
    
    for status, count in sorted(ct_status_counts.items()):
        print(f"  {status}: {count}")
    
    # Storage summary
    storage = data.get('storage', [])
    print(f"\nStorage: {len(storage)}")
    for stor in storage[:5]:  # Show first 5
        name = stor.get('storage', 'Unknown')
        type_ = stor.get('type', 'Unknown')
        print(f"  - {name} ({type_})")
    
    if len(storage) > 5:
        print(f"  ... and {len(storage) - 5} more")
    
    # HA resources
    ha_resources = data.get('ha_resources', [])
    if ha_resources:
        print(f"\nHA Resources: {len(ha_resources)}")
    
    # Recent tasks with errors
    tasks = data.get('recent_tasks', [])
    error_tasks = [t for t in tasks if t.get('status') == 'ERROR']
    if error_tasks:
        print(f"\n⚠ Recent Failed Tasks: {len(error_tasks)}")
        for task in error_tasks[:3]:
            node = task.get('node', 'Unknown')
            task_type = task.get('type', 'Unknown')
            print(f"  - {node}: {task_type}")
        
        if len(error_tasks) > 3:
            print(f"  ... and {len(error_tasks) - 3} more")
    
    print("\n" + "="*60)


def main():
    """Main collector entry point."""
    print("Proxmox Collector")
    print("="*60)
    
    try:
        # Load configuration
        config = load_config()
        proxmox_config = config.get('proxmox', {})
        cache_config = config.get('cache', {})
        
        url = proxmox_config.get('url')
        user = proxmox_config.get('user')
        token_name = proxmox_config.get('token_name')
        token_value = proxmox_config.get('token_value')
        
        if not all([url, user, token_name, token_value]):
            raise ValueError(
                "Proxmox URL, user, token_name, and token_value must be configured in config.yaml"
            )
        
        # Initialize client
        print(f"\nConnecting to Proxmox at {url}...")
        client = ProxmoxClient(
            url=url,
            user=user,
            token_name=token_name,
            token_value=token_value,
            verify_ssl=proxmox_config.get('verify_ssl', False)
        )
        
        # Test connection
        if not client.test_connection():
            raise ConnectionError("Failed to connect to Proxmox API")
        
        print("✓ Connection successful")
        
        # Collect data
        data = collect_proxmox_data(client)
        
        # Save to cache
        cache_dir = ensure_cache_dir(cache_config.get('directory', './cache'))
        save_cache(data, cache_dir)
        
        # Print summary
        print_summary(data)
        
        print("\n✓ Collection complete")
        return 0
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n✗ Collection failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
