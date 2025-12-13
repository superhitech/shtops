"""FreePBX Collector

Collects PBX status, extensions, trunks, queues, active calls,
and system health from FreePBX using AMI (Asterisk Manager Interface).
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
    Collect all relevant data from FreePBX using AMI.
    
    Args:
        client: Initialized FreePBX client
        
    Returns:
        Dictionary with collected data
    """
    print("Collecting FreePBX data via AMI...")
    
    data = {
        'collected_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'system_info': {},
        'extensions': [],
        'trunks': [],
        'queues': [],
        'active_calls': []
    }
    
    # Get system info
    print("  - Fetching system info...")
    try:
        system_info = client.get_asterisk_info()
        data['system_info'] = system_info
        if system_info.get('version'):
            print(f"    ✓ {system_info['version'][:80]}")
        else:
            print(f"    ✓ System information collected")
    except Exception as e:
        print(f"    ✗ Warning: Could not fetch system info: {e}")
    
    # Get extensions
    print("  - Fetching extensions...")
    try:
        extensions = client.get_extensions()
        data['extensions'] = extensions
        print(f"    ✓ Found {len(extensions)} extensions")
        
        # Show sample
        if extensions:
            online = [e for e in extensions if 'Avail' in e.get('status', '')]
            print(f"      {len(online)} online, {len(extensions) - len(online)} offline/unavailable")
    except Exception as e:
        print(f"    ✗ Warning: Could not fetch extensions: {e}")
    
    # Get trunks
    print("  - Fetching trunks...")
    try:
        trunks = client.get_trunks()
        data['trunks'] = trunks
        print(f"    ✓ Found {len(trunks)} trunk registrations")
        
        # Show sample
        if trunks:
            registered = [t for t in trunks if 'Registered' in t.get('state', '')]
            print(f"      {len(registered)} registered, {len(trunks) - len(registered)} not registered")
    except Exception as e:
        print(f"    ✗ Warning: Could not fetch trunks: {e}")
    
    # Get queues
    print("  - Fetching queues...")
    try:
        queues = client.get_queues()
        data['queues'] = queues
        print(f"    ✓ Found {len(queues)} queues")
        
        # Show sample
        if queues:
            with_calls = [q for q in queues if int(q.get('calls', '0')) > 0]
            if with_calls:
                print(f"      {len(with_calls)} queues have waiting calls")
    except Exception as e:
        print(f"    ✗ Warning: Could not fetch queues: {e}")
    
    # Get active calls
    print("  - Fetching active calls...")
    try:
        active_calls = client.get_active_calls()
        data['active_calls'] = active_calls
        print(f"    ✓ Found {len(active_calls)} active calls")
        
        # Show sample
        if active_calls:
            for call in active_calls[:3]:
                channel = call.get('channel', 'Unknown')
                state = call.get('state', 'Unknown')
                print(f"      - {channel}: {state}")
            if len(active_calls) > 3:
                print(f"      ... and {len(active_calls) - 3} more")
    except Exception as e:
        print(f"    ✗ Warning: Could not fetch active calls: {e}")
    
    return data


def main():
    """Main collection function."""
    print("=" * 60)
    print("FreePBX Collector (AMI)")
    print("=" * 60)
    print()
    
    # Load configuration
    print("Loading configuration...")
    config = load_config()
    freepbx_config = config.get('freepbx', {})
    cache_config = config.get('cache', {})
    
    # Validate AMI configuration
    required_fields = ['ami_host', 'ami_port', 'ami_username', 'ami_password']
    missing = [f for f in required_fields if f not in freepbx_config]
    if missing:
        print(f"✗ Error: Missing required config fields: {', '.join(missing)}")
        print("  Please update config/config.yaml with AMI credentials")
        return 1
    
    ami_host = freepbx_config['ami_host']
    ami_port = freepbx_config['ami_port']
    ami_username = freepbx_config['ami_username']
    ami_password = freepbx_config['ami_password']
    
    print(f"  AMI: {ami_host}:{ami_port}")
    print(f"  Username: {ami_username}")
    print()
    
    # Initialize client
    print("Connecting to FreePBX AMI...")
    try:
        with FreePBXClient(ami_host, ami_port, ami_username, ami_password) as client:
            print("✓ Connected and authenticated!\n")
            
            # Test connection
            if not client.test_connection():
                print("✗ Connection test failed")
                return 1
            print("✓ Connection test passed\n")
            
            # Collect data
            data = collect_freepbx_data(client)
            
            # Save to cache
            cache_dir = ensure_cache_dir(cache_config.get('directory', './cache'))
            output_file = cache_dir / 'freepbx.json'
            
            print()
            print(f"Saving data to {output_file}...")
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✓ Data saved successfully!")
            print()
            print("=" * 60)
            print("Summary:")
            print(f"  Extensions: {len(data['extensions'])}")
            print(f"  Trunks: {len(data['trunks'])}")
            print(f"  Queues: {len(data['queues'])}")
            print(f"  Active Calls: {len(data['active_calls'])}")
            print("=" * 60)
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
