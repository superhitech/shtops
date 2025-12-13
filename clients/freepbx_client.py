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
        self._action_id = 1
        
        # Connect and authenticate
        self._connect()
        self._authenticate()

    def _next_action_id(self) -> str:
        action_id = str(self._action_id)
        self._action_id += 1
        return action_id

    def _drain_pending(self, max_seconds: float = 0.25) -> None:
        """Drain any queued AMI events/responses already in the socket.

        Asterisk may emit asynchronous event frames (e.g. FullyBooted) that can
        arrive between actions. If we don't drain/ignore them, the next
        read-after-send can consume an event frame and misinterpret it as the
        action response.
        """
        if not self.socket:
            return

        original_timeout = self.socket.gettimeout()
        try:
            self.socket.settimeout(0.0)
            start = time.time()
            while time.time() - start < max_seconds:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                except (BlockingIOError, socket.error):
                    break
        finally:
            self.socket.settimeout(original_timeout)
    
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
        action_id = self._next_action_id()
        action = (
            f"Action: Login\r\n"
            f"ActionID: {action_id}\r\n"
            f"Username: {self.username}\r\n"
            f"Secret: {self.password}\r\n\r\n"
        )
        self.socket.send(action.encode('utf-8'))
        
        response = self._read_response()
        if 'Success' not in response:
            raise AuthenticationError(f"AMI authentication failed: {response}")
        
        self.authenticated = True
        # Drain any async events that may arrive right after login.
        self._drain_pending()
    
    def _read_response(self, terminator: bytes = b'\r\n\r\n') -> str:
        """Read a complete AMI response.

        Most AMI responses end with a blank line (double CRLF). Some actions
        (notably `Command`) can include a larger payload; in those cases a
        different terminator (e.g. `b'--END COMMAND--'`) is used.
        """
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

                if terminator in response:
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
        # Drain any queued async events before sending a new action.
        self._drain_pending()

        # Build action string
        action_id = self._next_action_id()
        action_str = f"Action: {action}\r\nActionID: {action_id}\r\n"
        for key, value in kwargs.items():
            action_str += f"{key}: {value}\r\n"
        action_str += "\r\n"
        
        # Send action
        self.socket.send(action_str.encode('utf-8'))
        
        # Read response: skip async event frames until we see a Response.
        start_time = time.time()
        while True:
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Timeout waiting for AMI response to action {action}")

            response = self._read_response()
            if not response.strip():
                continue

            # If this is an event-only frame, it won't include a Response header.
            if 'Response:' not in response:
                continue

            # If ActionID is present, make sure it matches.
            if f"ActionID: {action_id}" in response or 'ActionID:' not in response:
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
        # `Command` responses are typically `Response: Follows` and terminate with
        # `--END COMMAND--`. We also normalize output by stripping AMI headers and
        # the leading `Output: ` prefixes.
        self._drain_pending()
        action_id = self._next_action_id()
        action_str = f"Action: Command\r\nActionID: {action_id}\r\nCommand: {cmd}\r\n\r\n"
        self.socket.send(action_str.encode('utf-8'))

        raw = self._read_response(terminator=b'--END COMMAND--')

        # If we accidentally captured an async event first (rare), keep reading.
        if 'Response:' not in raw or (f"ActionID: {action_id}" not in raw and 'ActionID:' in raw):
            start_time = time.time()
            while time.time() - start_time <= self.timeout:
                more = self._read_response(terminator=b'--END COMMAND--')
                if not more.strip():
                    continue
                raw = more
                if 'Response:' in raw and (f"ActionID: {action_id}" in raw or 'ActionID:' not in raw):
                    break

        output_lines: List[str] = []
        for line in raw.split('\r\n'):
            if line == '--END COMMAND--':
                break
            if line.startswith('Output:'):
                output_lines.append(line.split(':', 1)[1].lstrip())

        return "\n".join(output_lines).rstrip("\n")
    
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
        
        # Get PJSIP endpoints.
        # On newer Asterisk versions, `pjsip show endpoints` often produces a
        # detailed multi-line listing. We only treat `Endpoint:` lines as the
        # actual endpoint identity.
        pjsip_output = self.ami.command('pjsip show endpoints')
        for line in pjsip_output.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('Endpoint:'):
                rest = line.split(':', 1)[1].strip()
                if not rest:
                    continue

                endpoint_id = rest.split()[0]  # e.g. 100/100
                # Skip header/table format lines like "<Endpoint...>"
                if endpoint_id.startswith('<'):
                    continue
                extension = endpoint_id.split('/')[0]
                status = rest[len(endpoint_id):].strip() or 'Unknown'

                if extension and not any(e.get('extension') == extension for e in extensions):
                    extensions.append({
                        'extension': extension,
                        'tech': 'PJSIP',
                        'status': status,
                        'type': 'endpoint'
                    })
        
        # Get SIP peers (legacy)
        try:
            sip_output = self.ami.command('sip show peers')
            if 'No such command' in sip_output or 'Command not found' in sip_output:
                return extensions
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
        
        # Get PJSIP registrations.
        # Output format varies by Asterisk version (table vs detailed). Prefer
        # parsing the first token as the registration id and infer state.
        pjsip_output = self.ami.command('pjsip show registrations')
        for line in pjsip_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            if line.startswith('=') or line.startswith('Objects found'):
                continue
            if line.startswith('Registration:') or line.startswith('Auth:') or line.startswith('Server URI:'):
                continue
            if '<Registration' in line or 'Aor:' in line or 'Transport:' in line:
                continue
            if line.lower().startswith('registration') and 'auth' in line.lower():
                continue

            parts = line.split()
            if not parts:
                continue

            reg_name = parts[0].strip()
            # Infer state from tokens when possible
            state = 'Unknown'
            for token in parts[1:]:
                if token in {'Registered', 'Rejected', 'Unregistered', 'AuthFailed', 'Failed'}:
                    state = token
                    break

            trunks.append({
                'name': reg_name,
                'tech': 'PJSIP',
                'state': state,
                'type': 'registration'
            })
        
        # Get SIP registry
        try:
            sip_output = self.ami.command('sip show registry')
            if 'No such command' in sip_output or 'Command not found' in sip_output:
                return trunks
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
