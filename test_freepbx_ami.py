#!/usr/bin/env python3
"""Test script for FreePBX AMI connection.

This script tests the connection to FreePBX AMI and validates that all
data collection methods are working properly.
"""

import sys
from pathlib import Path

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from clients.freepbx_client import FreePBXClient


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}\n"
            "Copy config.example.yaml to config.yaml and fill in your credentials."
        )
    
    with open(config_path) as f:
        return yaml.safe_load(f)


def print_header(title):
    """Print a section header."""
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main():
    """Run AMI connection tests."""
    print_header("FreePBX AMI Connection Test")
    
    # Load config
    print("\nLoading configuration...")
    config = load_config()
    freepbx_config = config.get('freepbx', {})
    
    # Check for required fields
    required_fields = ['ami_host', 'ami_port', 'ami_username', 'ami_password']
    missing = [f for f in required_fields if f not in freepbx_config]
    if missing:
        print(f"✗ Error: Missing required config fields: {', '.join(missing)}")
        print("\nPlease update config/config.yaml with:")
        print("  freepbx:")
        print("    ami_host: \"0.0.0.0\" or \"127.0.0.1\"")
        print("    ami_port: 5038")
        print("    ami_username: \"your-ami-username\"")
        print("    ami_password: \"your-ami-password\"")
        return 1
    
    ami_host = freepbx_config['ami_host']
    ami_port = freepbx_config['ami_port']
    ami_username = freepbx_config['ami_username']
    ami_password = freepbx_config['ami_password']
    
    print(f"\nConnecting to AMI at {ami_host}:{ami_port}")
    print(f"Username: {ami_username}")
    
    try:
        # Step 1: Connect
        print("\nStep 1: Connecting to AMI...")
        with FreePBXClient(ami_host, ami_port, ami_username, ami_password) as client:
            print("✓ Connected and authenticated!")
            
            # Step 2: Test connection
            print("\nStep 2: Testing connection...")
            if client.test_connection():
                print("✓ Connection test passed!")
            else:
                print("✗ Connection test failed!")
                return 1
            
            # Step 3: Get system info
            print("\nStep 3: Getting Asterisk system info...")
            system_info = client.get_asterisk_info()
            print("✓ System info retrieved")
            if system_info.get('version'):
                print(f"  Version: {system_info['version'][:80]}")
            
            # Step 4: Get extensions
            print("\nStep 4: Getting extensions...")
            extensions = client.get_extensions()
            print(f"✓ Found {len(extensions)} extensions")
            if extensions:
                print(f"  First {min(5, len(extensions))} extensions:")
                for ext in extensions[:5]:
                    ext_num = ext.get('extension', 'Unknown')
                    tech = ext.get('tech', 'Unknown')
                    status = ext.get('status', 'Unknown')
                    print(f"    - {ext_num} ({tech}): {status}")
            
            # Step 5: Get trunks
            print("\nStep 5: Getting trunks...")
            trunks = client.get_trunks()
            print(f"✓ Found {len(trunks)} trunk registrations")
            if trunks:
                print("  Trunks:")
                for trunk in trunks[:5]:
                    name = trunk.get('name', trunk.get('host', 'Unknown'))
                    state = trunk.get('state', 'Unknown')
                    tech = trunk.get('tech', 'Unknown')
                    print(f"    - {name} ({tech}): {state}")
            
            # Step 6: Get queues
            print("\nStep 6: Getting queues...")
            queues = client.get_queues()
            print(f"✓ Found {len(queues)} queues")
            if queues:
                print("  Queues:")
                for queue in queues[:5]:
                    name = queue.get('name', 'Unknown')
                    calls = queue.get('calls', '0')
                    members = queue.get('members', '0')
                    print(f"    - {name}: {calls} calls, {members} members")
            
            # Step 7: Get active calls
            print("\nStep 7: Getting active calls...")
            active_calls = client.get_active_calls()
            print(f"✓ Found {len(active_calls)} active calls")
            if active_calls:
                print("  Active calls:")
                for call in active_calls[:5]:
                    channel = call.get('channel', 'Unknown')
                    caller = call.get('caller_id', 'Unknown')
                    state = call.get('state', 'Unknown')
                    print(f"    - {channel}: {caller} ({state})")
            
            print_header("✓ ALL TESTS PASSED!")
            print("\nYour FreePBX AMI connection is working correctly!")
            print("\nYou can now run the collector:")
            print("  python -m collectors.freepbx.collect")
            print("\nOr set up a cron job to collect data automatically:")
            print("  */5 * * * * cd /path/to/shtops && venv/bin/python -m collectors.freepbx.collect")
            
    except ConnectionError as e:
        print(f"\n✗ Connection Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure AMI is enabled in /etc/asterisk/manager.conf")
        print("  2. Verify the host and port are correct")
        print("  3. If ami_host is 127.0.0.1, you must run this on the FreePBX server")
        print("  4. If ami_host is 0.0.0.0, make sure your firewall allows port 5038")
        return 1
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
