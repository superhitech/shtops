#!/usr/bin/env python3
"""
FreePBX API Diagnostic Tool

Helps diagnose why your FreePBX GraphQL API has limited queries available
and explores alternative APIs.
"""

import sys
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from freepbx_client import FreePBXClient


def check_graphql_scopes(config):
    """Check what happens with different OAuth scopes."""
    
    print("="*60)
    print("Testing Different OAuth Scopes")
    print("="*60)
    print()
    
    scopes_to_test = [
        'gql:core',
        'gql:asterisk', 
        'gql:*',
        'read write',
        'rest',
    ]
    
    token_url = f"{config['url']}/admin/api/api/token"
    
    for scope in scopes_to_test:
        print(f"Testing scope: {scope}")
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'scope': scope
        }
        
        try:
            response = requests.post(token_url, data=data, verify=False)
            
            if response.status_code == 200:
                token_data = response.json()
                token = token_data.get('access_token', 'None')
                print(f"  ✓ Token obtained: {token[:30]}...")
                
                # Try a GraphQL introspection query with this token
                gql_url = f"{config['url']}/admin/api/api/gql"
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                introspection = {
                    'query': '''
                        query {
                            __schema {
                                queryType {
                                    fields {
                                        name
                                    }
                                }
                            }
                        }
                    '''
                }
                
                gql_response = requests.post(gql_url, json=introspection, headers=headers, verify=False)
                if gql_response.status_code == 200:
                    result = gql_response.json()
                    if 'data' in result:
                        fields = result['data']['__schema']['queryType']['fields']
                        print(f"  ✓ GraphQL queries available: {len(fields)}")
                        print(f"    Queries: {', '.join([f['name'] for f in fields[:5]])}")
                    elif 'errors' in result:
                        print(f"  ✗ GraphQL error: {result['errors'][0]['message']}")
                else:
                    print(f"  ✗ GraphQL request failed: {gql_response.status_code}")
            else:
                print(f"  ✗ Failed: {response.status_code} - {response.text[:100]}")
        
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print()


def check_asterisk_ari(config):
    """Check if Asterisk ARI (REST Interface) is available."""
    
    print("="*60)
    print("Checking Asterisk ARI (Asterisk REST Interface)")
    print("="*60)
    print()
    
    # ARI typically runs on port 8088
    ari_urls = [
        f"{config['url']}:8088/ari",
        f"{config['url'].replace(':443', '')}:8088/ari",
        f"{config['url'].replace('https://', 'http://')}:8088/ari",
    ]
    
    for ari_url in ari_urls:
        print(f"Trying: {ari_url}")
        try:
            # ARI uses basic auth, not OAuth
            # We'd need ARI credentials, but let's just check if it's responding
            response = requests.get(f"{ari_url}/api-docs/resources.json", verify=False, timeout=5)
            
            if response.status_code == 401:
                print(f"  ✓ ARI is available but requires authentication")
                print(f"    You would need to configure ARI credentials in /etc/asterisk/ari.conf")
                return True
            elif response.status_code == 200:
                print(f"  ✓ ARI is available!")
                return True
            else:
                print(f"  ✗ Status: {response.status_code}")
        
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout - ARI not responding")
        except Exception as e:
            print(f"  ✗ Not available: {str(e)[:50]}")
        
        print()
    
    return False


def check_ami_proxy(config):
    """Check if there's an AMI proxy available."""
    
    print("="*60)
    print("Checking AMI (Asterisk Manager Interface)")
    print("="*60)
    print()
    
    print("AMI typically runs on port 5038 and requires specific credentials.")
    print("It's not HTTP-based, so we can't easily test it here.")
    print("You would need to configure AMI in /etc/asterisk/manager.conf")
    print()


def check_rest_api(config):
    """Check what REST endpoints might be available."""
    
    print("="*60)
    print("Checking FreePBX REST API Endpoints")
    print("="*60)
    print()
    
    # Get a token with 'rest' scope
    token_url = f"{config['url']}/admin/api/api/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'scope': 'rest'
    }
    
    try:
        response = requests.post(token_url, data=data, verify=False)
        
        if response.status_code != 200:
            print(f"✗ Could not get token with 'rest' scope: {response.status_code}")
            return
        
        token = response.json().get('access_token')
        print(f"✓ Got token with 'rest' scope")
        
        # Try common REST endpoints
        rest_base = f"{config['url']}/admin/api/api/rest"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        endpoints_to_test = [
            '/framework/version',
            '/core/users',
            '/core/extensions',
            '/asterisk/info',
            '/trunks',
            '/extensions',
        ]
        
        print(f"\nTesting REST endpoints:")
        for endpoint in endpoints_to_test:
            try:
                url = f"{rest_base}{endpoint}"
                response = requests.get(url, headers=headers, verify=False, timeout=5)
                
                if response.status_code == 200:
                    print(f"  ✓ {endpoint} - Available")
                    result = response.json()
                    print(f"    Response: {json.dumps(result, indent=2)[:200]}...")
                elif response.status_code == 404:
                    print(f"  ✗ {endpoint} - Not Found")
                elif response.status_code == 401:
                    print(f"  ✗ {endpoint} - Unauthorized")
                else:
                    print(f"  ? {endpoint} - Status {response.status_code}")
            
            except Exception as e:
                print(f"  ✗ {endpoint} - Error: {str(e)[:50]}")
        
    except Exception as e:
        print(f"✗ Error testing REST API: {e}")
    
    print()


def check_freepbx_version(config):
    """Try to determine FreePBX version."""
    
    print("="*60)
    print("Checking FreePBX Version")
    print("="*60)
    print()
    
    # Try the REST framework/version endpoint
    try:
        token_url = f"{config['url']}/admin/api/api/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'scope': 'rest'
        }
        
        response = requests.post(token_url, data=data, verify=False)
        if response.status_code == 200:
            token = response.json().get('access_token')
            
            version_url = f"{config['url']}/admin/api/api/rest/framework/version"
            headers = {'Authorization': f'Bearer {token}'}
            
            version_response = requests.get(version_url, headers=headers, verify=False)
            if version_response.status_code == 200:
                version_data = version_response.json()
                print(f"FreePBX Version: {json.dumps(version_data, indent=2)}")
            else:
                print(f"Could not get version: {version_response.status_code}")
    
    except Exception as e:
        print(f"Error checking version: {e}")
    
    print()


def main():
    config = {
        'url': 'https://pbx.super-ht.com',
        'client_id': '21be855b92945b1d9e7f6d79af194140d958c6e15ca2a87c09baf2da965b94ff',
        'client_secret': '486dab98eb72a72ab83596ffb9e5ffcf',
    }
    
    print("\n" + "="*60)
    print("FreePBX API Diagnostic Tool")
    print("="*60)
    print()
    
    # Check FreePBX version
    check_freepbx_version(config)
    
    # Check different OAuth scopes
    check_graphql_scopes(config)
    
    # Check REST API
    check_rest_api(config)
    
    # Check Asterisk ARI
    check_asterisk_ari(config)
    
    # Check AMI
    check_ami_proxy(config)
    
    print("="*60)
    print("Diagnostic Complete")
    print("="*60)
    print()
    print("Summary:")
    print("- Your GraphQL API only has 2 queries (allCoreUsers, coreUser)")
    print("- This is much more limited than expected")
    print()
    print("Possible reasons:")
    print("1. FreePBX version doesn't expose extensions/trunks via GraphQL")
    print("2. Additional modules need to be installed")
    print("3. GraphQL API is still in development in this FreePBX version")
    print()
    print("Alternatives to investigate:")
    print("1. REST API endpoints (if 'rest' scope has more endpoints)")
    print("2. Asterisk ARI (port 8088) - more comprehensive real-time data")
    print("3. Direct database queries (if you have MySQL access)")
    print("4. Asterisk AMI (port 5038) - most complete but complex")
    print()
    print("Next steps:")
    print("1. Check FreePBX GUI → Module Admin → API module version")
    print("2. Check FreePBX GUI → Connectivity → API Applications → GraphQL Explorer")
    print("3. Consider using Asterisk ARI for call data if available")
    print()


if __name__ == '__main__':
    # Disable SSL warnings for this diagnostic
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    main()
