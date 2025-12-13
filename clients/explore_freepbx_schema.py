#!/usr/bin/env python3
"""DEPRECATED: FreePBX GraphQL schema explorer.

SHTops uses AMI (Asterisk Manager Interface) as the supported integration.
GraphQL/OAuth scripts are retained only for historical reference.
"""

import sys

if __name__ == '__main__':
    print("This script is deprecated (GraphQL/OAuth path).")
    print("Use AMI instead:")
    print("  python3 test_freepbx_ami.py")
    print("  python3 -m collectors.freepbx.collect")
    sys.exit(2)


def explore_schema(client):
    """Introspect the GraphQL schema to see available queries."""
    
    print("="*60)
    print("FreePBX GraphQL Schema Explorer")
    print("="*60)
    print()
    
    # GraphQL introspection query
    introspection_query = """
    query {
      __schema {
        queryType {
          name
          fields {
            name
            description
            type {
              name
              kind
              ofType {
                name
                kind
              }
            }
            args {
              name
              type {
                name
                kind
                ofType {
                  name
                  kind
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        result = client._graphql_query(introspection_query)
        schema = result.get('__schema', {})
        query_type = schema.get('queryType', {})
        fields = query_type.get('fields', [])
        
        print(f"Found {len(fields)} available queries:")
        print()
        
        # Group queries by category
        categories = {}
        for field in fields:
            name = field.get('name', 'unknown')
            # Try to categorize
            if 'extension' in name.lower():
                category = 'Extensions'
            elif 'trunk' in name.lower():
                category = 'Trunks'
            elif 'queue' in name.lower():
                category = 'Queues'
            elif 'ivr' in name.lower():
                category = 'IVR'
            elif 'ring' in name.lower():
                category = 'Ring Groups'
            elif 'did' in name.lower() or 'route' in name.lower():
                category = 'DIDs/Routes'
            elif 'voicemail' in name.lower():
                category = 'Voicemail'
            elif 'conference' in name.lower():
                category = 'Conferences'
            elif 'user' in name.lower():
                category = 'Users'
            elif 'call' in name.lower() or 'channel' in name.lower():
                category = 'Calls/Channels'
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = []
            categories[category].append(field)
        
        # Print by category
        for category, fields in sorted(categories.items()):
            print(f"\n{category}:")
            print("-" * 60)
            for field in sorted(fields, key=lambda x: x.get('name', '')):
                name = field.get('name')
                desc = field.get('description', '')
                field_type = field.get('type', {})
                type_name = field_type.get('name') or field_type.get('ofType', {}).get('name', 'unknown')
                
                # Get arguments
                args = field.get('args', [])
                arg_str = ''
                if args:
                    arg_names = [f"{arg['name']}: {arg.get('type', {}).get('name', 'unknown')}" for arg in args]
                    arg_str = f"({', '.join(arg_names)})"
                
                print(f"  • {name}{arg_str} → {type_name}")
                if desc:
                    print(f"    {desc}")
        
        return fields
        
    except Exception as e:
        print(f"Error exploring schema: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_sample_queries(client, fields):
    """Try some sample queries based on available fields."""
    
    print("\n\n" + "="*60)
    print("Testing Sample Queries")
    print("="*60)
    print()
    
    # Look for extension queries
    extension_fields = [f for f in fields if 'extension' in f.get('name', '').lower()]
    if extension_fields:
        print("Testing extension query...")
        # Try to get a single extension query
        for field in extension_fields:
            name = field.get('name')
            if 'all' not in name.lower() and 'extension' in name.lower():
                # This might be a single extension query
                args = field.get('args', [])
                if args:
                    print(f"  Query: {name}")
                    query = f"""
                    query {{
                        {name}(extension: "100") {{
                            extension
                            name
                        }}
                    }}
                    """
                    try:
                        result = client._graphql_query(query)
                        print(f"  ✓ Result: {json.dumps(result, indent=2)[:200]}...")
                        break
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
    
    # Try a list query
    print("\nTesting list query...")
    for field in fields:
        name = field.get('name')
        # Look for queries that might return lists
        if any(keyword in name.lower() for keyword in ['all', 'list', 'fetch']):
            print(f"  Trying: {name}")
            
            # Get the return type to understand structure
            field_type = field.get('type', {})
            type_name = field_type.get('name') or field_type.get('ofType', {}).get('name', '')
            
            # Try different query structures
            # First try: simple fields
            query = f"""
            query {{
                {name} {{
                    __typename
                }}
            }}
            """
            try:
                result = client._graphql_query(query)
                print(f"  ✓ Query works! Type: {result}")
                
                # Now try to get actual data by exploring the type
                type_query = f"""
                query {{
                    __type(name: "{type_name}") {{
                        fields {{
                            name
                            type {{
                                name
                                kind
                            }}
                        }}
                    }}
                }}
                """
                type_result = client._graphql_query(type_query)
                type_fields = type_result.get('__type', {}).get('fields', [])
                if type_fields:
                    print(f"  Available fields in {type_name}:")
                    for tf in type_fields[:5]:
                        print(f"    - {tf['name']}")
                
                break
            except Exception as e:
                print(f"  ✗ Failed: {str(e)[:100]}")
                continue


def save_schema_to_file(fields):
    """Save the schema information to a file."""
    
    schema_info = {
        'queries': []
    }
    
    for field in fields:
        query_info = {
            'name': field.get('name'),
            'description': field.get('description'),
            'return_type': field.get('type', {}).get('name') or field.get('type', {}).get('ofType', {}).get('name'),
            'arguments': []
        }
        
        for arg in field.get('args', []):
            query_info['arguments'].append({
                'name': arg.get('name'),
                'type': arg.get('type', {}).get('name') or arg.get('type', {}).get('ofType', {}).get('name')
            })
        
        schema_info['queries'].append(query_info)
    
    with open('/home/superht/freepbx_schema.json', 'w') as f:
        json.dump(schema_info, f, indent=2)
    
    print(f"\n✓ Schema saved to freepbx_schema.json")


def main():
    config = {
        'url': 'https://pbx.super-ht.com',
        'client_id': '21be855b92945b1d9e7f6d79af194140d958c6e15ca2a87c09baf2da965b94ff',
        'client_secret': '486dab98eb72a72ab83596ffb9e5ffcf',
        'verify_ssl': False
    }
    
    print("Initializing client...")
    client = FreePBXClient(
        url=config['url'],
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        verify_ssl=config['verify_ssl']
    )
    print("✓ Connected\n")
    
    # Explore the schema
    fields = explore_schema(client)
    
    # Save to file
    if fields:
        save_schema_to_file(fields)
    
    # Test some queries
    if fields:
        test_sample_queries(client, fields)
    
    print("\n" + "="*60)
    print("Exploration complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Review freepbx_schema.json to see all available queries")
    print("2. Look for queries related to extensions, trunks, etc.")
    print("3. Use the FreePBX GUI GraphQL Explorer to test queries")
    print("   (Connectivity → API Applications → GraphQL Explorer)")
    print()


if __name__ == '__main__':
    main()
