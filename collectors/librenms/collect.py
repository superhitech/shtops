"""LibreNMS Collector

Collects device status, alerts, and health metrics from LibreNMS
and caches them locally for querying.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from clients.librenms_client import LibreNMSClient


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


def collect_librenms_data(client: LibreNMSClient) -> Dict[str, Any]:
    """
    Collect all relevant data from LibreNMS.
    
    Args:
        client: Initialized LibreNMS client
        
    Returns:
        Dictionary with collected data
    """
    print("Collecting LibreNMS data...")
    
    data = {
        'collected_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'devices': [],
        'alerts': [],
        'device_groups': [],
        'alert_rules': []
    }
    
    # Get devices
    print("  - Fetching devices...")
    devices = client.get_devices()
    data['devices'] = devices
    print(f"    Found {len(devices)} devices")
    
    # Get alerts
    print("  - Fetching alerts...")
    alerts = client.get_alerts()
    data['alerts'] = alerts
    active_alerts = [a for a in alerts if a.get('state') == 1]  # state 1 = active
    print(f"    Found {len(alerts)} total alerts ({len(active_alerts)} active)")
    
    # Get device groups
    print("  - Fetching device groups...")
    try:
        groups = client.get_device_groups()
        data['device_groups'] = groups
        print(f"    Found {len(groups)} device groups")
    except Exception as e:
        print(f"    Warning: Could not fetch device groups: {e}")
    
    # Get alert rules
    print("  - Fetching alert rules...")
    try:
        rules = client.get_alert_rules()
        data['alert_rules'] = rules
        print(f"    Found {len(rules)} alert rules")
    except Exception as e:
        print(f"    Warning: Could not fetch alert rules: {e}")
    
    # Enhance devices with additional info
    print("  - Enriching device data...")
    for device in data['devices'][:10]:  # Limit to first 10 to avoid rate limiting
        device_id = device.get('device_id')
        if device_id:
            try:
                # Get health metrics
                health = client.get_device_health(device_id)
                device['health'] = health
            except Exception as e:
                print(f"    Warning: Could not fetch health for device {device_id}: {e}")
    
    return data


def save_cache(data: Dict[str, Any], cache_path: Path) -> None:
    """Save collected data to cache file."""
    output_file = cache_path / 'librenms.json'
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nCache saved to: {output_file}")
    print(f"Size: {output_file.stat().st_size / 1024:.1f} KB")


def print_summary(data: Dict[str, Any]) -> None:
    """Print a summary of collected data."""
    print("\n" + "="*60)
    print("LibreNMS Collection Summary")
    print("="*60)
    
    devices = data.get('devices', [])
    alerts = data.get('alerts', [])
    
    print(f"\nTotal Devices: {len(devices)}")
    
    # Device status breakdown
    status_counts = {}
    for device in devices:
        status = device.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    if status_counts:
        print("\nDevice Status:")
        for status, count in sorted(status_counts.items()):
            status_name = "Up" if status == 1 else "Down" if status == 0 else "Unknown"
            print(f"  {status_name}: {count}")
    
    # Alert breakdown
    print(f"\nTotal Alerts: {len(alerts)}")
    if alerts:
        active_count = sum(1 for a in alerts if a.get('state') == 1)
        ack_count = sum(1 for a in alerts if a.get('state') == 2)
        
        print(f"  Active: {active_count}")
        print(f"  Acknowledged: {ack_count}")
        
        if active_count > 0:
            print("\nActive Alerts:")
            for alert in alerts[:5]:  # Show first 5 active alerts
                if alert.get('state') == 1:
                    device_name = alert.get('hostname', 'Unknown')
                    rule_name = alert.get('rule_name', 'Unknown')
                    print(f"  - {device_name}: {rule_name}")
            
            if active_count > 5:
                print(f"  ... and {active_count - 5} more")
    
    print("\n" + "="*60)


def main():
    """Main collector entry point."""
    print("LibreNMS Collector")
    print("="*60)
    
    try:
        # Load configuration
        config = load_config()
        librenms_config = config.get('librenms', {})
        cache_config = config.get('cache', {})
        
        url = librenms_config.get('url')
        api_key = librenms_config.get('api_key')
        
        if not url or not api_key:
            raise ValueError(
                "LibreNMS URL and API key must be configured in config.yaml"
            )
        
        # Initialize client
        print(f"\nConnecting to LibreNMS at {url}...")
        client = LibreNMSClient(
            url=url,
            api_key=api_key,
            verify_ssl=librenms_config.get('verify_ssl', True)
        )
        
        # Test connection
        if not client.test_connection():
            raise ConnectionError("Failed to connect to LibreNMS API")
        
        print("✓ Connection successful")
        
        # Collect data
        data = collect_librenms_data(client)
        
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
