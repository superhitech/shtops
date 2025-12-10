"""FreePBX/Asterisk API Client

Provides a clean Python interface to the FreePBX GraphQL API.
Requires the FreePBX API module to be installed and configured with OAuth2.
https://github.com/FreePBX/api
"""

import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class FreePBXClient:
    """Client for interacting with FreePBX GraphQL API."""
    
    def __init__(self, url: str, client_id: str, client_secret: str, verify_ssl: bool = False):
        """
        Initialize FreePBX client with OAuth2 client credentials.
        
        Args:
            url: Base URL of FreePBX instance (e.g., "https://pbx.example.com")
            client_id: OAuth2 Client ID from API Applications
            client_secret: OAuth2 Client Secret
            verify_ssl: Whether to verify SSL certificates (default: False)
        """
        self.url = url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.access_token = None
        self.graphql_url = urljoin(self.url, '/admin/api/api/gql')
        
        # Get access token
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Obtain OAuth2 access token using client credentials with required scopes."""
        token_url = urljoin(self.url, '/admin/api/api/token')
        
        # Request gql:core scope for GraphQL access
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'gql:core'  # CRITICAL: Must include scope for GraphQL
        }
        
        try:
            response = requests.post(
                token_url,
                data=data,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            if not self.access_token:
                raise ValueError(f"No access token in response: {token_data}")
            
            # Set authorization header
            self.session.headers.update({
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        except Exception as e:
            print(f"Authentication failed: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def _graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Query response data
        """
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        
        try:
            response = self.session.post(
                self.graphql_url,
                json=payload,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            
            result = response.json()
            
            if 'errors' in result:
                error_msgs = [e.get('message', str(e)) for e in result['errors']]
                raise Exception(f"GraphQL errors: {', '.join(error_msgs)}")
            
            return result.get('data', {})
            
        except Exception as e:
            print(f"GraphQL query failed: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def get_asterisk_info(self) -> Dict[str, Any]:
        """
        Get Asterisk system information using GraphQL.
        
        Returns:
            System info dictionary
        """
        query = """
        query {
            asterisk {
                info {
                    version
                    built_by
                    built_date
                    built_os
                    built_kernel
                }
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('asterisk', {}).get('info', {})
        except Exception:
            # Fallback to empty dict if query not available
            return {}
    
    def get_extensions(self) -> List[Dict[str, Any]]:
        """
        Get all extensions using GraphQL.
        
        Returns:
            List of extension dictionaries
        """
        query = """
        query {
            fetchAllExtensions {
                extension
                name
                tech
                dial
                deviceuser
                description
                emergency_cid
                hint
                noanswer
                recording_in_external
                recording_in_internal
                recording_out_external
                recording_out_internal
                ringtimer
                sipname
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('fetchAllExtensions', [])
        except Exception as e:
            print(f"Error fetching extensions: {e}")
            return []
    
    def get_extension(self, extension: str) -> Dict[str, Any]:
        """
        Get details for a specific extension using GraphQL.
        
        Args:
            extension: Extension number
            
        Returns:
            Extension details
        """
        query = """
        query($extension: String!) {
            fetchExtension(extension: $extension) {
                extension
                name
                tech
                dial
                deviceuser
                description
                emergency_cid
                hint
                noanswer
                recording_in_external
                recording_in_internal
                recording_out_external
                recording_out_internal
                ringtimer
                sipname
            }
        }
        """
        
        try:
            result = self._graphql_query(query, {'extension': extension})
            return result.get('fetchExtension', {})
        except Exception:
            return {}
    
    def get_trunks(self) -> List[Dict[str, Any]]:
        """
        Get all trunks using GraphQL.
        
        Returns:
            List of trunk dictionaries
        """
        query = """
        query {
            fetchAllTrunks {
                trunkid
                name
                tech
                outcid
                keepcid
                maxchans
                failscript
                dialoutprefix
                channelid
                usercontext
                provider
                disabled
                continue
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('fetchAllTrunks', [])
        except Exception as e:
            print(f"Error fetching trunks: {e}")
            return []
    
    def get_active_calls(self) -> List[Dict[str, Any]]:
        """
        Get currently active calls using GraphQL.
        
        Returns:
            List of active call dictionaries
        """
        query = """
        query {
            asterisk {
                channels {
                    id
                    name
                    state
                    caller {
                        name
                        number
                    }
                    connected {
                        name
                        number
                    }
                    accountcode
                    dialplan {
                        context
                        exten
                        priority
                    }
                    creationtime
                }
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('asterisk', {}).get('channels', [])
        except Exception as e:
            print(f"Error fetching active calls: {e}")
            return []
    
    def get_queues(self) -> List[Dict[str, Any]]:
        """
        Get all queues using GraphQL.
        
        Returns:
            List of queue dictionaries
        """
        query = """
        query {
            fetchAllQueues {
                extension
                descr
                grppre
                alertinfo
                ringing
                maxwait
                password
                ivr_id
                dest
                cwignore
                qregex
                queuewait
                use_queue_context
                togglehint
                qnoanswer
                callconfirm
                callconfirm_id
                monitor_type
                monitor_heard
                monitor_spoken
                callback_id
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('fetchAllQueues', [])
        except Exception as e:
            print(f"Error fetching queues: {e}")
            return []
    
    def get_ivrs(self) -> List[Dict[str, Any]]:
        """
        Get all IVR menus using GraphQL.
        
        Returns:
            List of IVR dictionaries
        """
        query = """
        query {
            fetchAllIVRs {
                id
                name
                description
                announcement
                directdial
                timeout
                invalid_loops
                invalid_retry_recording
                invalid_destination
                timeout_time
                timeout_recording
                timeout_destination
                retvm
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('fetchAllIVRs', [])
        except Exception as e:
            print(f"Error fetching IVRs: {e}")
            return []
    
    def get_ring_groups(self) -> List[Dict[str, Any]]:
        """
        Get all ring groups using GraphQL.
        
        Returns:
            List of ring group dictionaries
        """
        query = """
        query {
            fetchAllRinggroups {
                grpnum
                strategy
                grptime
                grppre
                grplist
                postdest
                description
                alertinfo
                remotealert_id
                needsconf
                toolate_id
                ringing
                cwignore
                cfignore
                cpickup
                recording
                changecid
                fixedcid
            }
        }
        """
        
        try:
            result = self._graphql_query(query)
            return result.get('fetchAllRinggroups', [])
        except Exception as e:
            print(f"Error fetching ring groups: {e}")
            return []
    
    def test_connection(self) -> bool:
        """
        Test the API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try a simple GraphQL query
            query = """
            query {
                asterisk {
                    info {
                        version
                    }
                }
            }
            """
            self._graphql_query(query)
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False