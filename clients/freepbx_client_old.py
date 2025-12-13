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