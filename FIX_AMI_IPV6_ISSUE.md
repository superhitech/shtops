# AMI IPv6 Binding Issue - SOLUTION

## The Problem

AMI is only listening on IPv6:
```
tcp6       0      0 :::5038                 :::*                    LISTEN
```

But we need it to listen on IPv4:
```
tcp        0      0 0.0.0.0:5038            0.0.0.0:*               LISTEN
```

## Root Cause

Even though `manager.conf` has `bindaddr = 0.0.0.0`, Asterisk on this system is preferring IPv6.

## Solution - Run on FreePBX Server

### Quick Fix (Bind to Specific IP)

**On the FreePBX server**, edit `/etc/asterisk/manager.conf`:

Change this line:
```ini
bindaddr = 0.0.0.0
```

To this (using the actual server IP):
```ini
bindaddr = 192.168.5.24
```

Then restart:
```bash
sudo systemctl restart asterisk
sudo netstat -tlnp | grep 5038
```

You should now see:
```
tcp        0      0 192.168.5.24:5038       0.0.0.0:*               LISTEN
```

### Complete Commands

Run these on **pbx.super-ht.com**:

```bash
# 1. Backup the config
sudo cp /etc/asterisk/manager.conf /etc/asterisk/manager.conf.backup

# 2. Edit the config
sudo nano /etc/asterisk/manager.conf
# Find the line: bindaddr = 0.0.0.0
# Change to:     bindaddr = 192.168.5.24

# 3. The [general] section should look like:
# [general]
# enabled = yes
# port = 5038
# bindaddr = 192.168.5.24

# 4. Save and exit (Ctrl+X, Y, Enter)

# 5. Restart Asterisk
sudo systemctl restart asterisk

# 6. Wait a moment, then verify
sleep 3
sudo netstat -tlnp | grep 5038

# 7. You should see IPv4 now, not tcp6
```

### Alternative: Use sed (one-liner)

```bash
sudo sed -i.bak 's/^bindaddr = 0.0.0.0/bindaddr = 192.168.5.24/' /etc/asterisk/manager.conf
sudo systemctl restart asterisk
sleep 3
sudo netstat -tlnp | grep 5038
```

## After the Fix

Test from the **shtops machine** (10.10.0.24):

```bash
cd /home/superht/shtops
python3 test_freepbx_ami.py
```

You should see:
```
✓ Connected and authenticated!
✓ Connection test passed!
✓ System info retrieved
✓ Found X extensions
...
✓ ALL TESTS PASSED!
```

## Why This Happens

When `bindaddr = 0.0.0.0` is used, some Linux systems with IPv6 enabled will bind to `:::5038` (IPv6 all interfaces) instead of `0.0.0.0:5038` (IPv4 all interfaces).

By specifying the exact IPv4 address (`192.168.5.24`), we force Asterisk to bind to IPv4.

## Alternative Solutions

### Option 1: Disable IPv6 (not recommended)
```bash
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo systemctl restart asterisk
```

### Option 2: Bind to both (if supported)
In some Asterisk versions, you can have multiple bindaddr lines:
```ini
bindaddr = 0.0.0.0
bindaddr = ::
```

### Option 3: Use localhost only
If shtops will run ON the FreePBX server:
```ini
bindaddr = 127.0.0.1
```

Then update shtops config to use `ami_host: "127.0.0.1"`

## Verification

After making changes, verify with:

```bash
# Should show IPv4 binding
netstat -tlnp | grep 5038

# Should allow connection
telnet 192.168.5.24 5038
# You should see: Asterisk Call Manager/x.x.x
# Type Ctrl+] then 'quit' to exit

# Test from remote machine
# On 10.10.0.24:
telnet 192.168.5.24 5038
```

## Security Note

Since you're binding to a specific IP (192.168.5.24), the service is already restricted to that interface. The permit/deny rules in manager.conf provide additional security by restricting which clients can authenticate.

Current permit rule allows entire subnet:
```ini
permit = 10.10.0.0/255.255.255.0
```

This is fine for internal networks. For production, consider restricting to specific IPs:
```ini
permit = 10.10.0.24/255.255.255.255  # Only shtops server
```
