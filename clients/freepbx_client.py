"""FreePBX/Asterisk API Client

Provides a clean Python interface to the FreePBX REST API module.
Requires the FreePBX API module to be installed.
https://github.com/FreePBX/api
"""

import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class FreePBXClient:
    """Client for interacting with FreePBX REST API module."""
    
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
        
        # Get access token
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Obtain OAuth2 access token using client credentials."""
        token_url = urljoin(self.url, '/admin/api/api/token')
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
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
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response data
            
        Raises:
            requests.exceptions.RequestException: On API errors
        """
        url = urljoin(self.url, endpoint)
        kwargs.setdefault('verify', self.verify_ssl)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        
        # Try to parse JSON, but handle text responses
        try:
            return response.json()
        except ValueError:
            return response.text
    
    def get_asterisk_info(self) -> Dict[str, Any]:
        """
        Get Asterisk system information.
        
        Returns:
            System info dictionary
        """
        return self._request('GET', '/admin/api/api/asterisk/sysinfo')
    
    def get_asterisk_variables(self) -> Dict[str, Any]:
        """
        Get Asterisk global variables.
        
        Returns:
            Variables dictionary
        """
        try:
            return self._request('GET', '/admin/api/api/asterisk/variable')
        except Exception:
            return {}
    
    def get_extensions(self) -> List[Dict[str, Any]]:
        """
        Get all extensions.
        
        Returns:
            List of extension dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/extensions')
            if isinstance(result, dict):
                return result.get('extensions', [])
            return []
        except Exception:
            return []
    
    def get_trunks(self) -> List[Dict[str, Any]]:
        """
        Get all trunks.
        
        Returns:
            List of trunk dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/trunks')
            if isinstance(result, dict):
                return result.get('trunks', [])
            return []
        except Exception:
            return []
    
    def get_active_calls(self) -> List[Dict[str, Any]]:
        """
        Get currently active calls.
        
        Returns:
            List of active call dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/asterisk/activecalls')
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get('calls', [])
            return []
        except Exception:
            return []
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """
        Get active channels.
        
        Returns:
            List of channel dictionaries
        """
        try:
            result = self._request('GET', '/ari/channels')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_endpoints(self) -> List[Dict[str, Any]]:
        """
        Get all endpoints (extensions/devices).
        
        Returns:
            List of endpoint dictionaries
        """
        try:
            result = self._request('GET', '/ari/endpoints')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_bridges(self) -> List[Dict[str, Any]]:
        """
        Get all bridges (calls in progress).
        
        Returns:
            List of bridge dictionaries
        """
        try:
            result = self._request('GET', '/ari/bridges')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_recordings(self) -> List[Dict[str, Any]]:
        """
        Get stored recordings.
        
        Returns:
            List of recording dictionaries
        """
        try:
            result = self._request('GET', '/ari/recordings/stored')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    # Legacy methods kept for compatibility but may not work without FreePBX API module
    def get_extensions(self) -> List[Dict[str, Any]]:
        """
        Get all extensions.
        
        Returns:
            List of extension dictionaries
        """
        result = self._request('GET', '/admin/api/api/extensions')
        if isinstance(result, dict):
            return result.get('extensions', [])
        return []
    
    def get_extension(self, extension: str) -> Dict[str, Any]:
        """
        Get details for a specific extension.
        
        Args:
            extension: Extension number
            
        Returns:
            Extension details
        """
        return self._request('GET', f'/admin/api/api/extensions/{extension}')
    
    def get_trunks(self) -> List[Dict[str, Any]]:
        """
        Get all trunks.
        
        Returns:
            List of trunk dictionaries
        """
        result = self._request('GET', '/admin/api/api/trunks')
        if isinstance(result, dict):
            return result.get('trunks', [])
        return []
    
    def get_trunk_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all trunks (registration status).
        
        Returns:
            List of trunk status dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/asterisk/registry')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_active_calls(self) -> List[Dict[str, Any]]:
        """
        Get currently active calls.
        
        Returns:
            List of active call dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/asterisk/activecalls')
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get('calls', [])
            return []
        except Exception:
            return []
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """
        Get active channels.
        
        Returns:
            List of channel dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/asterisk/channels')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_queues(self) -> List[Dict[str, Any]]:
        """
        Get all queues.
        
        Returns:
            List of queue dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/queues')
            if isinstance(result, dict):
                return result.get('queues', [])
            return []
        except Exception:
            return []
    
    def get_queue_status(self) -> List[Dict[str, Any]]:
        """
        Get real-time queue status.
        
        Returns:
            List of queue status dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/asterisk/queuestatus')
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []
    
    def get_parking_lots(self) -> List[Dict[str, Any]]:
        """
        Get parking lot configuration.
        
        Returns:
            List of parking lot dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/parking')
            if isinstance(result, dict):
                return result.get('parking', [])
            return []
        except Exception:
            return []
    
    def get_ring_groups(self) -> List[Dict[str, Any]]:
        """
        Get all ring groups.
        
        Returns:
            List of ring group dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/ringgroups')
            if isinstance(result, dict):
                return result.get('ringgroups', [])
            return []
        except Exception:
            return []
    
    def get_ivr(self) -> List[Dict[str, Any]]:
        """
        Get all IVR menus.
        
        Returns:
            List of IVR dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/ivr')
            if isinstance(result, dict):
                return result.get('ivr', [])
            return []
        except Exception:
            return []
    
    def get_did(self) -> List[Dict[str, Any]]:
        """
        Get all DIDs (inbound routes).
        
        Returns:
            List of DID dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/did')
            if isinstance(result, dict):
                return result.get('did', [])
            return []
        except Exception:
            return []
    
    def get_voicemail(self) -> List[Dict[str, Any]]:
        """
        Get all voicemail boxes.
        
        Returns:
            List of voicemail dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/voicemail')
            if isinstance(result, dict):
                return result.get('voicemail', [])
            return []
        except Exception:
            return []
    
    def get_conferences(self) -> List[Dict[str, Any]]:
        """
        Get all conference rooms.
        
        Returns:
            List of conference dictionaries
        """
        try:
            result = self._request('GET', '/admin/api/api/conferences')
            if isinstance(result, dict):
                return result.get('conferences', [])
            return []
        except Exception:
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status.
        
        Returns:
            System status dictionary
        """
        try:
            return self._request('GET', '/admin/api/api/asterisk/status')
        except Exception:
            return {}
    
    def reload_dialplan(self) -> bool:
        """
        Reload the dialplan (apply configuration changes).
        
        Returns:
            True if successful
        """
        try:
            self._request('POST', '/admin/api/api/asterisk/reload')
            return True
        except Exception:
            return False
    
    def test_connection(self) -> bool:
        """
        Test the API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.get_asterisk_info()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Connection test error details: {e}")
            return False
