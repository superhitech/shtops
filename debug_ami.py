#!/usr/bin/env python3
"""Debug AMI connection - shows exact data sent/received."""

import socket
import time

def read_response(sock, timeout=10):
    """Read a complete AMI response."""
    response = b''
    start_time = time.time()
    
    while True:
        if time.time() - start_time > timeout:
            print(f"Timeout after {timeout} seconds")
            break
        
        try:
            chunk = sock.recv(4096)
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

def main():
    host = "192.168.5.24"
    port = 5038
    username = "3pXw6N7PhSVI"
    password = "Ep6CvZpiPpUr"
    
    print("=" * 60)
    print("AMI Connection Debug")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print()
    
    # Connect
    print("Step 1: Connecting...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((host, port))
        print("✓ Connected!")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return 1
    
    # Read welcome
    print("\nStep 2: Reading welcome message...")
    welcome = read_response(sock)
    print("Received:")
    print("-" * 60)
    print(repr(welcome))
    print("-" * 60)
    print(welcome)
    
    # Send login
    print("\nStep 3: Sending login...")
    login = f"Action: Login\r\nUsername: {username}\r\nSecret: {password}\r\n\r\n"
    print("Sending:")
    print("-" * 60)
    print(repr(login))
    print("-" * 60)
    print(login)
    
    sock.send(login.encode('utf-8'))
    
    # Read response
    print("\nStep 4: Reading authentication response...")
    response = read_response(sock)
    print("Received:")
    print("-" * 60)
    print(repr(response))
    print("-" * 60)
    print(response)
    
    if 'Success' in response:
        print("\n✓ Authentication successful!")
    else:
        print("\n✗ Authentication failed!")
        print("Check the credentials in /etc/asterisk/manager.conf")
    
    # Close
    sock.close()
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
