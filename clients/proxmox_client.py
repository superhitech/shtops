"""Proxmox VE API Client

Provides a clean Python interface to the Proxmox Virtual Environment API.
Documentation: https://pve.proxmox.com/wiki/Proxmox_VE_API
"""

import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import warnings

# Suppress only the single InsecureRequestWarning from urllib3
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class ProxmoxClient:
    """Client for interacting with Proxmox VE API."""
    
    def __init__(self, url: str, user: str, token_name: str, token_value: str, 
                 verify_ssl: bool = False):
        """
        Initialize Proxmox client using API tokens.
        
        Args:
            url: Base URL of Proxmox instance (e.g., "https://proxmox.example.com:8006")
            user: Username (e.g., "api@pam")
            token_name: API token name
            token_value: API token value (UUID format)
            verify_ssl: Whether to verify SSL certificates (default: False)
        """
        self.url = url.rstrip('/')
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        # API token authentication
        self.session.headers.update({
            'Authorization': f'PVEAPIToken={user}!{token_name}={token_value}'
        })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api2/json/nodes")
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response data (usually a dict or list)
            
        Raises:
            requests.exceptions.RequestException: On API errors
        """
        url = urljoin(self.url, endpoint)
        kwargs.setdefault('verify', self.verify_ssl)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        
        data = response.json()
        return data.get('data', data)
    
    def get_version(self) -> Dict[str, Any]:
        """
        Get Proxmox version information.
        
        Returns:
            Version info dictionary
        """
        return self._request('GET', '/api2/json/version')
    
    def get_cluster_status(self) -> List[Dict[str, Any]]:
        """
        Get cluster status.
        
        Returns:
            List of cluster nodes and their status
        """
        return self._request('GET', '/api2/json/cluster/status')
    
    def get_cluster_resources(self, type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get cluster resources (VMs, containers, storage, nodes).
        
        Args:
            type: Filter by type ('vm', 'storage', 'node'). None for all.
            
        Returns:
            List of resource dictionaries
        """
        params = {}
        if type:
            params['type'] = type
        
        return self._request('GET', '/api2/json/cluster/resources', params=params)
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes in the cluster.
        
        Returns:
            List of node dictionaries
        """
        return self._request('GET', '/api2/json/nodes')
    
    def get_node_status(self, node: str) -> Dict[str, Any]:
        """
        Get detailed status for a specific node.
        
        Args:
            node: Node name
            
        Returns:
            Node status dictionary
        """
        return self._request('GET', f'/api2/json/nodes/{node}/status')
    
    def get_node_vms(self, node: str) -> List[Dict[str, Any]]:
        """
        Get all VMs (qemu) on a node.
        
        Args:
            node: Node name
            
        Returns:
            List of VM dictionaries
        """
        return self._request('GET', f'/api2/json/nodes/{node}/qemu')
    
    def get_node_containers(self, node: str) -> List[Dict[str, Any]]:
        """
        Get all containers (LXC) on a node.
        
        Args:
            node: Node name
            
        Returns:
            List of container dictionaries
        """
        return self._request('GET', f'/api2/json/nodes/{node}/lxc')
    
    def get_vm_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get status for a specific VM.
        
        Args:
            node: Node name
            vmid: VM ID
            
        Returns:
            VM status dictionary
        """
        return self._request('GET', f'/api2/json/nodes/{node}/qemu/{vmid}/status/current')
    
    def get_container_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get status for a specific container.
        
        Args:
            node: Node name
            vmid: Container ID
            
        Returns:
            Container status dictionary
        """
        return self._request('GET', f'/api2/json/nodes/{node}/lxc/{vmid}/status/current')
    
    def get_storage(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get storage information.
        
        Args:
            node: Optional node name to filter by
            
        Returns:
            List of storage dictionaries
        """
        if node:
            return self._request('GET', f'/api2/json/nodes/{node}/storage')
        else:
            return self._request('GET', '/api2/json/storage')
    
    def get_node_storage_content(self, node: str, storage: str) -> List[Dict[str, Any]]:
        """
        Get content of a storage on a node.
        
        Args:
            node: Node name
            storage: Storage name
            
        Returns:
            List of storage content items
        """
        return self._request('GET', f'/api2/json/nodes/{node}/storage/{storage}/content')
    
    def get_tasks(self, node: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent tasks.
        
        Args:
            node: Optional node name to filter by
            limit: Maximum number of tasks to return
            
        Returns:
            List of task dictionaries
        """
        params = {'limit': limit}
        
        if node:
            return self._request('GET', f'/api2/json/nodes/{node}/tasks', params=params)
        else:
            return self._request('GET', '/api2/json/cluster/tasks', params=params)
    
    def get_cluster_backup_schedule(self) -> List[Dict[str, Any]]:
        """
        Get cluster backup schedule.
        
        Returns:
            List of backup job dictionaries
        """
        try:
            return self._request('GET', '/api2/json/cluster/backup')
        except requests.exceptions.HTTPError:
            # Older Proxmox versions might not have this endpoint
            return []
    
    def get_pools(self) -> List[Dict[str, Any]]:
        """
        Get resource pools.
        
        Returns:
            List of pool dictionaries
        """
        return self._request('GET', '/api2/json/pools')
    
    def get_ha_resources(self) -> List[Dict[str, Any]]:
        """
        Get HA (High Availability) managed resources.
        
        Returns:
            List of HA resource dictionaries
        """
        try:
            return self._request('GET', '/api2/json/cluster/ha/resources')
        except requests.exceptions.HTTPError:
            # HA might not be configured
            return []
    
    def get_ha_status(self) -> Dict[str, Any]:
        """
        Get HA status.
        
        Returns:
            HA status dictionary
        """
        try:
            return self._request('GET', '/api2/json/cluster/ha/status/current')
        except requests.exceptions.HTTPError:
            return {}
    
    def test_connection(self) -> bool:
        """
        Test the API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.get_version()
            return True
        except requests.exceptions.RequestException:
            return False
