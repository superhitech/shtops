"""FreePBX/Asterisk AMI Client

Provides a clean Python interface to the Asterisk Manager Interface (AMI).
AMI provides comprehensive access to all FreePBX/Asterisk data and real-time events.
"""

import socket
import time
from typing import Dict, List, Any, Optional


class AMIClient:
    """Client for Asterisk Manager Interface (AMI)."""
    
    def __init__(self, host: str, port: int, username: str, password: str, timeout: int = 10):
        """
        Initialize AMI client.
        
        Args:
            host: AMI host (usually 127.0.0.1 or 0.0.0.0)
            port: AMI port (default: 5038)
            username: AMI username
            password: AMI password
            timeout: Socket timeout in seconds
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.socket = None
        self.authenticated = False
        
        # Connect and authenticate
        self._connect()
        self._authenticate()
    
    def _connect(self) -> None:
        """Establish socket connection to AMI."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # Read welcome message
            welcome = self._read_response()
            if 'Asterisk Call Manager' not in welcome:
                raise ConnectionError(f"Unexpected AMI response: {welcome}")
                
        except Exception as e:
            raise ConnectionError(f"Failed to connect to AMI at {self.host}:{self.port}: {e}")
    
    def _authenticate(self) -> None:
        """Authenticate with AMI."""
        action = f"Action: Login\r\nUsername: {self.username}\r\nSecret: {self.password}\r\n\r\n"
        self.socket.send(action.encode('utf-8'))
        
        response = self._read_response()
        if 'Success' not in response:
            raise AuthenticationError(f"AMI authentication failed: {response}")
        
        self.authenticated = True
    
    def _read_response(self) -> str:
        """Read a complete AMI response."""
        response = b''
        start_time = time.time()
        
        while True:
            if time.time() - start_time > self.timeout:
                raise TimeoutError("Timeout reading AMI response")
            
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                
                # AMI responses end with double CRLF
                if b'\r\n\r\n' in response:
                    break
            except socket.timeout:
                if response:
                    break
                raise
        
        return response.decode('utf-8', errors='ignore')
    
    def _send_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Send an AMI action and parse the response.
        
        Args:
            action: AMI action name
            **kwargs: Additional action parameters
            
        Returns:
            Parsed response dictionary
        """
        # Build action string
        action_str = f"Action: {action}\r\n"
        for key, value in kwargs.items():
            action_str += f"{key}: {value}\r\n"
        action_str += "\r\n"
        
        # Send action
        self.socket.send(action_str.encode('utf-8'))
        
        # Read response
        response = self._read_response()
        
        # Parse response
        return self._parse_response(response)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse AMI response into structured data."""
        result = {
            'success': False,
            'message': '',
            'events': [],
            'data': {}
        }
        
        current_event = {}
        
        for line in response.split('\r\n'):
            if not line.strip():
                if current_event:
                    result['events'].append(current_event)
                    current_event = {}
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'Response':
                    result['success'] = value == 'Success'
                    result['message'] = value
                elif key == 'Message':
                    result['message'] = value
                else:
                    current_event[key] = value
                    result['data'][key] = value
        
        # Add last event if exists
        if current_event:
            result['events'].append(current_event)
        
        return result
    
    def command(self, cmd: str) -> str:
        """
        Execute an Asterisk CLI command.
        
        Args:
            cmd: Asterisk CLI command
            
        Returns:
            Command output
        """
        response = self._send_action('Command', Command=cmd)
        
        # Command output is in the raw response
        # Re-read to get full output
        action_str = f"Action: Command\r\nCommand: {cmd}\r\n\r\n"
        self.socket.send(action_str.encode('utf-8'))
        output = self._read_response()
        
        return output
    
    def ping(self) -> bool:
        """Test connection to AMI."""
        response = self._send_action('Ping')
        return response['success']
    
    def close(self) -> None:
        """Close AMI connection."""
        if self.socket:
            try:
                self._send_action('Logoff')
            except:
                pass
            finally:
                self.socket.close()
                self.socket = None
                self.authenticated = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AuthenticationError(Exception):
    """AMI authentication failed."""
    pass


class FreePBXClient:
    """High-level FreePBX client using AMI."""
    
    def __init__(self, ami_host: str, ami_port: int, ami_username: str, ami_password: str):
        """
        Initialize FreePBX client with AMI credentials.
        
        Args:
            ami_host: AMI host address
            ami_port: AMI port (default: 5038)
            ami_username: AMI username
            ami_password: AMI password
        """
        self.ami = AMIClient(ami_host, ami_port, ami_username, ami_password)
    
    def test_connection(self) -> bool:
        """Test the AMI connection."""
        return self.ami.ping()
    
    def get_asterisk_info(self) -> Dict[str, Any]:
        """
        Get Asterisk system information.
        
        Returns:
            System info dictionary with version, uptime, etc.
        """
        output = self.ami.command('core show version')
        
        info = {
            'raw_version': output,
            'version': '',
            'uptime': ''
        }
        
        # Parse version from output
        for line in output.split('\n'):
            if 'Asterisk' in line and 'built' in line:
                info['version'] = line.strip()
                break
        
        # Get uptime
        uptime_output = self.ami.command('core show uptime')
        info['uptime'] = uptime_output.strip()
        
        return info
    
    def get_extensions(self) -> List[Dict[str, Any]]:
        """
        Get all SIP/PJSIP extensions.
        
        Returns:
            List of extension dictionaries
        """
        extensions = []
        
        # Get PJSIP endpoints
        pjsip_output = self.ami.command('pjsip show endpoints')
        for line in pjsip_output.split('\n'):
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('Endpoint') or line.startswith('Object'):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                endpoint = parts[0].strip()
                # Skip non-extension entries
                if '/' in endpoint or endpoint == 'Endpoint:':
                    continue
                    
                status = parts[1] if len(parts) > 1 else 'Unknown'
                
                extensions.append({
                    'extension': endpoint,
                    'tech': 'PJSIP',
                    'status': status,
                    'type': 'endpoint'
                })
        
        # Get SIP peers (legacy)
        try:
            sip_output = self.ami.command('sip show peers')
            for line in sip_output.split('\n'):
                line = line.strip()
                if not line or line.startswith('=') or line.startswith('Name/username') or 'sip peers' in line.lower():
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    peer = parts[0].strip().split('/')[0]
                    # Skip if already in PJSIP list
                    if not any(e['extension'] == peer for e in extensions):
                        status = parts[-1] if len(parts) > 1 else 'Unknown'
                        extensions.append({
                            'extension': peer,
                            'tech': 'SIP',
                            'status': status,
                            'type': 'peer'
                        })
        except:
            pass  # SIP might not be configured
        
        return extensions
    
    def get_active_calls(self) -> List[Dict[str, Any]]:
        """
        Get currently active calls.
        
        Returns:
            List of active call dictionaries
        """
        calls = []
        
        output = self.ami.command('core show channels verbose')
        
        current_call = {}
        for line in output.split('\n'):
            line = line.strip()
            
            if line.startswith('Channel:'):
                if current_call:
                    calls.append(current_call)
                current_call = {'channel': line.split(':', 1)[1].strip()}
            elif line.startswith('CallerIDNum:') and current_call:
                current_call['caller_id'] = line.split(':', 1)[1].strip()
            elif line.startswith('CallerIDName:') and current_call:
                current_call['caller_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('State:') and current_call:
                current_call['state'] = line.split(':', 1)[1].strip()
            elif line.startswith('Duration:') and current_call:
                current_call['duration'] = line.split(':', 1)[1].strip()
            elif line.startswith('ConnectedLineNum:') and current_call:
                current_call['connected_num'] = line.split(':', 1)[1].strip()
        
        if current_call:
            calls.append(current_call)
        
        return calls
    
    def get_trunks(self) -> List[Dict[str, Any]]:
        """
        Get trunk registration status.
        
        Returns:
            List of trunk dictionaries
        """
        trunks = []
        
        # Get PJSIP registrations
        pjsip_output = self.ami.command('pjsip show registrations')
        for line in pjsip_output.split('\n'):
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('Objects found'):
                continue
            if 'Registration' in line or '<Registration' in line:
                continue
                
            parts = line.split()
            if len(parts) >= 2:
                reg_name = parts[0].strip()
                state = parts[1].strip() if len(parts) > 1 else 'Unknown'
                
                trunks.append({
                    'name': reg_name,
                    'tech': 'PJSIP',
                    'state': state,
                    'type': 'registration'
                })
        
        # Get SIP registry
        try:
            sip_output = self.ami.command('sip show registry')
            for line in sip_output.split('\n'):
                line = line.strip()
                if not line or line.startswith('=') or 'sip registrations' in line.lower():
                    continue
                if 'Host' in line and 'Username' in line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 3:
                    host = parts[0].strip()
                    state = parts[2].strip() if len(parts) > 2 else 'Unknown'
                    
                    trunks.append({
                        'host': host,
                        'tech': 'SIP',
                        'state': state,
                        'type': 'registration'
                    })
        except:
            pass  # SIP might not be configured
        
        return trunks
    
    def get_queues(self) -> List[Dict[str, Any]]:
        """
        Get queue status.
        
        Returns:
            List of queue dictionaries
        """
        queues = []
        
        output = self.ami.command('queue show')
        
        current_queue = {}
        for line in output.split('\n'):
            line = line.strip()
            
            if not line:
                if current_queue:
                    queues.append(current_queue)
                    current_queue = {}
                continue
            
            if line.endswith('has 0 calls') or 'has' in line and 'calls' in line:
                parts = line.split()
                if len(parts) >= 1:
                    current_queue = {
                        'name': parts[0],
                        'calls': '0',
                        'members': '0',
                        'holdtime': '0'
                    }
                    # Extract call count
                    for i, part in enumerate(parts):
                        if part == 'has' and i + 1 < len(parts):
                            current_queue['calls'] = parts[i + 1]
                            break
            elif 'Members:' in line and current_queue:
                current_queue['members'] = line.split(':')[1].strip()
            elif 'Longest Hold Time:' in line and current_queue:
                current_queue['holdtime'] = line.split(':')[1].strip()
        
        if current_queue:
            queues.append(current_queue)
        
        return queues
    
    def close(self) -> None:
        """Close the AMI connection."""
        self.ami.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
