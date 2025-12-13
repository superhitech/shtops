"""FreePBX Collector

Collects PBX status, extensions, trunks, queues, active calls,
and system health from FreePBX using GraphQL API.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clients.freepbx_client import FreePBXClient


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


def collect_freepbx_data(client: FreePBXClient) -> Dict[str, Any]:
    """
    Collect all relevant data from FreePBX using GraphQL.
    
    Args:
        client: Initialized FreePBX client
        
    Returns:
        Dictionary with collected data
    """
    print("Collecting FreePBX data...")
    
    data = {
        'collected_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'system_info': {},
        'extensions': [],
        'trunks': [],
        'queues': [],
        'ivrs': [],
        'ring_groups': [],
        'active_calls': []
    }
    
    # Get system info
    print("  - Fetching system info...")
    try:
        system_info = client.get_asterisk_info()
        data['system_info'] = system_info
        if system_info.get('version'):
            print(f"    Asterisk version: {system_info['version']}")
        else:
            print(f"    System information collected")
    except Exception as e:
        print(f"    Warning: Could not fetch system info: {e}")
    
    # Get extensions
    print("  - Fetching extensions...")
    try:
        extensions = client.get_extensions()
        data['extensions'] = extensions
        print(f"    Found {len(extensions)} extensions")
    except Exception as e:
        print(f"    Warning: Could not fetch extensions: {e}")
    
    # Get trunks
    print("  - Fetching trunks...")
    try:
        trunks = client.get_trunks()
        data['trunks'] = trunks
        print(f"    Found {len(trunks)} trunks")
    except Exception as e:
        print(f"    Warning: Could not fetch trunks: {e}")
    
    # Get queues
    print("  - Fetching queues...")
    try:
        queues = client.get_queues()
        data['queues'] = queues
        print(f"    Found {len(queues)} queues")
    except Exception as e:
        print(f"    Warning: Could not fetch queues: {e}")
    
    # Get IVRs
    print("  - Fetching IVR menus...")
    try:
        ivrs = client.get_ivrs()
        data['ivrs'] = ivrs
        print(f"    Found {len(ivrs)} IVR menus")
    except Exception as e:
        print(f"    Warning: Could not fetch IVRs: {e}")
    
    # Get ring groups
    print("  - Fetching ring groups...")
    try:
        ring_groups = client.get_ring_groups()
        data['ring_groups'] = ring_groups
        print(f"    Found {len(ring_groups)} ring groups")
    except Exception as e:
        print(f"    Warning: Could not fetch ring groups: {e}")
    
    # Get active calls
    print("  - Fetching active calls...")
    try:
        active_calls = client.get_active_calls()
        data['active_calls'] = active_calls
        print(f"    Found {len(active_calls)} active calls")
    except Exception as e:
        print(f"    Warning: Could not fetch active calls: {e}")
    
    return data


def save_cache(data: Dict[str, Any], cache_path: Path) -> None:
    """Save collected data to cache file."""
    output_file = cache_path / 'freepbx.json'
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nCache saved to: {output_file}")
    print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")


def print_summary(data: Dict[str, Any]) -> None:
    """Print a summary of collected data."""
    print("\n" + "="*60)
    print("FreePBX Collection Summary")
    print("="*60)
    
    # System info
    system_info = data.get('system_info', {})
    if system_info and system_info.get('version'):
        print(f"\nAsterisk Version: {system_info['version']}")
    
    # Extensions
    extensions = data.get('extensions', [])
    print(f"\nExtensions: {len(extensions)}")
    
    # Trunks
    trunks = data.get('trunks', [])
    print(f"Trunks: {len(trunks)}")
    
    # Queues
    queues = data.get('queues', [])
    print(f"Queues: {len(queues)}")
    
    # IVRs
    ivrs = data.get('ivrs', [])
    print(f"IVR Menus: {len(ivrs)}")
    
    # Ring Groups
    ring_groups = data.get('ring_groups', [])
    print(f"Ring Groups: {len(ring_groups)}")
    
    # Active calls
    active_calls = data.get('active_calls', [])
    print(f"Active Calls: {len(active_calls)}")
    if active_calls:
        print("\n  Current Calls:")
        for call in active_calls[:3]:
            caller = call.get('caller', {})
            connected = call.get('connected', {})
            caller_num = caller.get('number', 'Unknown')
            connected_num = connected.get('number', 'Unknown')
            print(f"    - {caller_num} → {connected_num}")
        if len(active_calls) > 3:
            print(f"    ... and {len(active_calls) - 3} more")
    
    print("\n" + "="*60)


def main():
    """Main collector entry point."""
    print("FreePBX Collector (GraphQL API)")
    print("="*60)
    
    try:
        # Load configuration
        config = load_config()
        freepbx_config = config.get('freepbx', {})
        cache_config = config.get('cache', {})
        
        url = freepbx_config.get('url')
        client_id = freepbx_config.get('client_id')
        client_secret = freepbx_config.get('client_secret')
        
        if not all([url, client_id, client_secret]):
            raise ValueError(
                "FreePBX URL, client_id, and client_secret must be configured in config.yaml"
            )
        
        # Initialize client
        print(f"\nConnecting to FreePBX at {url}...")
        print("Using GraphQL API with OAuth2 authentication...")
        client = FreePBXClient(
            url=url,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=freepbx_config.get('verify_ssl', False)
        )
        
        # Test connection
        print("Testing connection...")
        try:
            if not client.test_connection():
                raise ConnectionError("Failed to connect to FreePBX GraphQL API")
        except Exception as e:
            print(f"Connection test failed: {e}")
            import traceback
            traceback.print_exc()
            raise ConnectionError(f"Failed to connect to FreePBX API: {e}")
        
        print("✓ Connection successful")
        
        # Collect data
        data = collect_freepbx_data(client)
        
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