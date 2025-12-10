#!/usr/bin/env python3
"""
Simple test script to verify FreePBX API connection.
This tests authentication and basic GraphQL queries.
"""

import sys
import json
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Update this import once you've copied the fixed client file
from freepbx_client import FreePBXClient


def test_connection():
    """Test FreePBX API connection and authentication."""
    
    print("="*60)
    print("FreePBX API Connection Test")
    print("="*60)
    
    # Configuration - UPDATE THESE VALUES
    config = {
        'url': 'https://pbx.super-ht.com',
        'client_id': '21be855b92945b1d9e7f6d79af194140d958c6e15ca2a87c09baf2da965b94ff',
        'client_secret': '486dab98eb72a72ab83596ffb9e5ffcf',
        'verify_ssl': False
    }
    
    print(f"\nConnecting to: {config['url']}")
    print(f"Client ID: {config['client_id'][:20]}...")
    print()
    
    try:
        # Step 1: Initialize client (this handles authentication)
        print("Step 1: Authenticating with OAuth2...")
        client = FreePBXClient(
            url=config['url'],
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            verify_ssl=config['verify_ssl']
        )
        print("✓ Authentication successful!")
        print(f"  Access token: {client.access_token[:30]}...")
        print()
        
        # Step 2: Test connection with simple query
        print("Step 2: Testing connection with simple query...")
        if client.test_connection():
            print("✓ Connection test passed!")
        else:
            print("✗ Connection test failed!")
            return False
        print()
        
        # Step 3: Fetch system info
        print("Step 3: Fetching Asterisk system info...")
        system_info = client.get_asterisk_info()
        if system_info:
            print("✓ System info retrieved:")
            print(json.dumps(system_info, indent=2))
        else:
            print("  Note: System info query returned empty (may not be available)")
        print()
        
        # Step 4: Fetch extensions
        print("Step 4: Fetching extensions...")
        extensions = client.get_extensions()
        print(f"✓ Found {len(extensions)} extensions")
        if extensions:
            print(f"  First 3 extensions:")
            for ext in extensions[:3]:
                ext_num = ext.get('extension', 'N/A')
                ext_name = ext.get('name', 'N/A')
                ext_tech = ext.get('tech', 'N/A')
                print(f"    - {ext_num}: {ext_name} ({ext_tech})")
        print()
        
        # Step 5: Fetch trunks
        print("Step 5: Fetching trunks...")
        trunks = client.get_trunks()
        print(f"✓ Found {len(trunks)} trunks")
        if trunks:
            print(f"  Trunks:")
            for trunk in trunks[:5]:
                trunk_id = trunk.get('trunkid', 'N/A')
                trunk_name = trunk.get('name', 'N/A')
                trunk_tech = trunk.get('tech', 'N/A')
                disabled = trunk.get('disabled', 'N/A')
                status = "DISABLED" if disabled == 'on' else "ENABLED"
                print(f"    - [{trunk_id}] {trunk_name} ({trunk_tech}) - {status}")
        print()
        
        # Step 6: Fetch active calls
        print("Step 6: Fetching active calls...")
        active_calls = client.get_active_calls()
        print(f"✓ Found {len(active_calls)} active calls")
        if active_calls:
            print(f"  Active calls:")
            for call in active_calls:
                call_id = call.get('id', 'N/A')
                caller = call.get('caller', {})
                connected = call.get('connected', {})
                caller_num = caller.get('number', 'N/A')
                connected_num = connected.get('number', 'N/A')
                state = call.get('state', 'N/A')
                print(f"    - [{call_id}] {caller_num} → {connected_num} ({state})")
        else:
            print("  No active calls at this time")
        print()
        
        # Success summary
        print("="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nYour FreePBX API integration is working correctly!")
        print("You can now use the full collector to gather all data.")
        print("\nNext steps:")
        print("1. Copy freepbx_client_fixed.py to clients/freepbx_client.py")
        print("2. Copy freepbx_collect_fixed.py to collectors/freepbx/collect.py")
        print("3. Run: python -m collectors.freepbx.collect")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        print("\nError details:")
        import traceback
        traceback.print_exc()
        print("\nTroubleshooting:")
        print("1. Check that your client_id and client_secret are correct")
        print("2. Verify the OAuth2 application has 'gql:core' scope")
        print("3. Make sure the FreePBX API module is installed and enabled")
        print("4. Check that FreePBX is accessible at the configured URL")
        return False


def test_graphql_query():
    """Test a raw GraphQL query to help debug."""
    import requests
    
    print("\n" + "="*60)
    print("Raw GraphQL Query Test (for debugging)")
    print("="*60)
    
    config = {
        'url': 'https://pbx.super-ht.com',
        'client_id': '21be855b92945b1d9e7f6d79af194140d958c6e15ca2a87c09baf2da965b94ff',
        'client_secret': '486dab98eb72a72ab83596ffb9e5ffcf',
    }
    
    # Step 1: Get token
    print("\nGetting OAuth2 token...")
    token_url = f"{config['url']}/admin/api/api/token"
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'scope': 'gql:core'
    }
    
    try:
        response = requests.post(token_url, data=token_data, verify=False)
        response.raise_for_status()
        token_response = response.json()
        access_token = token_response.get('access_token')
        print(f"✓ Token: {access_token[:30]}...")
        
        # Step 2: Make GraphQL query
        print("\nMaking GraphQL query...")
        gql_url = f"{config['url']}/admin/api/api/gql"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        query = {
            'query': '''
                query {
                    fetchAllExtensions {
                        extension
                        name
                    }
                }
            '''
        }
        
        response = requests.post(gql_url, json=query, headers=headers, verify=False)
        response.raise_for_status()
        result = response.json()
        
        print("✓ Query successful!")
        print(f"Response: {json.dumps(result, indent=2)[:500]}...")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response: {e.response.text[:500]}")


if __name__ == '__main__':
    success = test_connection()
    
    if not success:
        print("\nWould you like to try a raw GraphQL query test? (y/n): ", end='')
        if input().lower().strip() == 'y':
            test_graphql_query()
    
    sys.exit(0 if success else 1)
