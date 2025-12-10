"""LibreNMS API Client

Provides a clean Python interface to the LibreNMS API.
Documentation: https://docs.librenms.org/API/
"""

import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class LibreNMSClient:
    """Client for interacting with LibreNMS API."""
    
    def __init__(self, url: str, api_key: str, verify_ssl: bool = True):
        """
        Initialize LibreNMS client.
        
        Args:
            url: Base URL of LibreNMS instance (e.g., "https://librenms.example.com")
            api_key: API key for authentication
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            'X-Auth-Token': api_key,
            'Accept': 'application/json'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v0/devices")
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.exceptions.RequestException: On API errors
        """
        url = f"{self.url}{endpoint}"
        kwargs.setdefault('verify', self.verify_ssl)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        
        return response.json()
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Get all devices.
        
        Returns:
            List of device dictionaries
        """
        response = self._request('GET', '/api/v0/devices')
        return response.get('devices', [])
    
    def get_device(self, device_id: int) -> Dict[str, Any]:
        """
        Get a specific device by ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device dictionary
        """
        response = self._request('GET', f'/api/v0/devices/{device_id}')
        return response.get('devices', [{}])[0]
    
    def get_alerts(self, state: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get alerts.
        
        Args:
            state: Filter by state ('active', 'acknowledged', 'ok'). None for all.
            
        Returns:
            List of alert dictionaries
        """
        params = {}
        if state:
            params['state'] = state
            
        response = self._request('GET', '/api/v0/alerts', params=params)
        return response.get('alerts', [])
    
    def get_device_health(self, device_id: int) -> Dict[str, Any]:
        """
        Get health metrics for a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Dictionary with health metrics (cpu, memory, storage, etc.)
        """
        response = self._request('GET', f'/api/v0/devices/{device_id}/health')
        return response.get('health', {})
    
    def get_device_ports(self, device_id: int) -> List[Dict[str, Any]]:
        """
        Get ports for a device.
        
        Args:
            device_id: Device ID
            
        Returns:
            List of port dictionaries
        """
        response = self._request('GET', f'/api/v0/devices/{device_id}/ports')
        return response.get('ports', [])
    
    def get_alert_rules(self) -> List[Dict[str, Any]]:
        """
        Get all alert rules.
        
        Returns:
            List of alert rule dictionaries
        """
        response = self._request('GET', '/api/v0/rules')
        return response.get('rules', [])
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            True if successful
        """
        try:
            self._request('PUT', f'/api/v0/alerts/{alert_id}', 
                         json={'state': 'acknowledged'})
            return True
        except requests.exceptions.RequestException:
            return False
    
    def get_device_groups(self) -> List[Dict[str, Any]]:
        """
        Get all device groups.
        
        Returns:
            List of device group dictionaries
        """
        response = self._request('GET', '/api/v0/devicegroups')
        return response.get('groups', [])
    
    def get_inventory(self, device_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get inventory items.
        
        Args:
            device_id: Optional device ID to filter by
            
        Returns:
            List of inventory dictionaries
        """
        if device_id:
            response = self._request('GET', f'/api/v0/inventory/{device_id}')
        else:
            response = self._request('GET', '/api/v0/inventory')
        return response.get('inventory', [])
    
    def test_connection(self) -> bool:
        """
        Test the API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._request('GET', '/api/v0/devices?limit=1')
            return True
        except requests.exceptions.RequestException:
            return False
