# FreePBX AMI Implementation

## Status: ✅ Implementation Complete - Authentication Issue

The AMI client has been successfully implemented and can connect to the FreePBX server at `192.168.5.24:5038`. However, we're getting an authentication error.

## What's Been Implemented

### 1. AMI Client (`clients/freepbx_client.py`)
- Complete socket-based AMI client
- Handles connection, authentication, and command execution
- Provides high-level methods for:
  - Extensions (SIP/PJSIP)
  - Active calls
  - Trunks
  - Queues
  - System information

### 2. AMI Collector (`collectors/freepbx/collect.py`)
- Collects all FreePBX data via AMI
- Saves to `cache/freepbx.json`
- Provides detailed status output

### 3. Test Script (`test_freepbx_ami.py`)
- Comprehensive connection testing
- Validates all data collection methods
- Helpful error messages

### 4. Configuration (`config/config.yaml`)
Updated with AMI credentials:
```yaml
freepbx:
  ami_host: "192.168.5.24"
  ami_port: 5038
  ami_username: "3pXw6N7PhSVI"
  ami_password: "Ep6CvZpiPpUr"
```

## Current Issue: Authentication Failed

The AMI client can connect to port 5038, but authentication is failing.

### Possible Causes:

1. **Credentials Mismatch**: The username/password in `config.yaml` might not match `/etc/asterisk/manager.conf` on the FreePBX server

2. **IP Restrictions**: The manager.conf might have `permit/deny` rules that don't allow connections from `10.10.0.24` (this machine)

3. **Incorrect Config Format**: The manager.conf might have changed

### How to Fix:

**Option 1: Verify Credentials on FreePBX Server**

SSH into the FreePBX server and check:
```bash
ssh root@pbx.super-ht.com
cat /etc/asterisk/manager.conf
```

Look for a section like:
```ini
[3pXw6N7PhSVI]
secret = Ep6CvZpiPpUr
deny = 0.0.0.0/0.0.0.0
permit = 192.168.5.0/255.255.255.0
permit = 10.10.0.0/255.255.255.0  # <-- Make sure this allows 10.10.0.24
read = system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan
write = system,call,log,verbose,command,agent,user,config,command,dtmf,reporting,cdr,dialplan
```

**Option 2: Update Permit Rules**

If the IP restriction is the issue, add to manager.conf:
```ini
permit = 10.10.0.24/255.255.255.255
```

Then reload AMI:
```bash
asterisk -rx "manager reload"
```

**Option 3: Create New AMI User**

If the credentials are wrong, create a new user in manager.conf:
```ini
[shtops]
secret = YourSecurePasswordHere
deny = 0.0.0.0/0.0.0.0
permit = 10.10.0.24/255.255.255.255
read = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan
write = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan
```

Then reload:
```bash
asterisk -rx "manager reload"
```

And update `config/config.yaml`:
```yaml
freepbx:
  ami_username: "shtops"
  ami_password: "YourSecurePasswordHere"
```

## Testing After Fix

Once you've updated the credentials or permissions:

```bash
cd /home/superht/shtops
python3 test_freepbx_ami.py
```

Expected output:
```
============================================================
FreePBX AMI Connection Test
============================================================

Loading configuration...

Connecting to AMI at 192.168.5.24:5038
Username: shtops

Step 1: Connecting to AMI...
✓ Connected and authenticated!

Step 2: Testing connection...
✓ Connection test passed!

Step 3: Getting Asterisk system info...
✓ System info retrieved
  Version: Asterisk 18.x.x

Step 4: Getting extensions...
✓ Found X extensions
  ...

✓ ALL TESTS PASSED!
```

## Running the Collector

Once authentication works:

```bash
# Manual collection
python3 -m collectors.freepbx.collect

# Schedule automatic collection (every 5 minutes)
crontab -e
# Add:
*/5 * * * * cd /home/superht/shtops && /usr/bin/python3 -m collectors.freepbx.collect >> /var/log/shtops-freepbx.log 2>&1
```

## What You'll Get

Once working, the collector will save to `cache/freepbx.json`:

```json
{
  "collected_at": "2025-12-09T12:34:56Z",
  "system_info": {
    "version": "Asterisk 18.x.x",
    "uptime": "..."
  },
  "extensions": [
    {
      "extension": "100",
      "tech": "PJSIP",
      "status": "Available"
    }
  ],
  "trunks": [
    {
      "name": "trunk1",
      "tech": "PJSIP",
      "state": "Registered"
    }
  ],
  "queues": [
    {
      "name": "sales",
      "calls": "2",
      "members": "5"
    }
  ],
  "active_calls": [
    {
      "channel": "PJSIP/100-00000001",
      "caller_id": "100",
      "state": "Up"
    }
  ]
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│          SHTops Context Layer           │
│         (10.10.0.24 - This host)        │
├─────────────────────────────────────────┤
│                                         │
│  FreePBX AMI Client                     │
│  ├─ Socket: 192.168.5.24:5038          │
│  ├─ Protocol: AMI (text-based)         │
│  └─ Authentication: username/password   │
│                                         │
│  Collected Data:                        │
│  ├─ Extensions (SIP + PJSIP)           │
│  ├─ Active calls & channels            │
│  ├─ Trunks & registration status       │
│  ├─ Queues & members                   │
│  └─ System info & uptime               │
│                                         │
└─────────────────────────────────────────┘
              │
              ↓ TCP Port 5038
┌─────────────────────────────────────────┐
│     FreePBX Server (192.168.5.24)       │
│         pbx.super-ht.com                │
├─────────────────────────────────────────┤
│  Asterisk Manager Interface (AMI)       │
│  - Port: 5038                           │
│  - Config: /etc/asterisk/manager.conf   │
└─────────────────────────────────────────┘
```

## Next Steps

1. ✅ AMI client implemented
2. ✅ Collector implemented  
3. ✅ Test script created
4. ✅ Config updated
5. ⏸️ **Fix authentication** (see above)
6. ⏸️ Run test to verify
7. ⏸️ Run collector
8. ⏸️ Set up cron job for automatic collection

## Benefits Over GraphQL API

| Feature | AMI | GraphQL |
|---------|-----|---------|
| Extensions | ✅ Full data | ❌ Not available |
| Trunks | ✅ Full data | ❌ Not available |
| Active Calls | ✅ Real-time | ❌ Not available |
| Queues | ✅ Full status | ❌ Not available |
| System Info | ✅ Complete | ❌ Limited |
| Real-time Events | ✅ Possible | ❌ No |
| CLI Commands | ✅ Any command | ❌ No |

AMI gives you **everything** you need for the SHTops vision!
