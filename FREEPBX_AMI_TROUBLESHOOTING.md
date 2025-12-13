# FreePBX AMI Authentication Issue - Solution

## Problem
Authentication is failing even though the manager.conf configuration looks correct.

## Most Likely Cause
The manager.conf file was updated but **not reloaded** into Asterisk's running configuration.

Another very common cause in FreePBX is **a duplicate user section in** `manager_custom.conf`.
FreePBX includes files in this order:

- `manager.conf` (auto-generated)
- `manager_additional.conf`
- `manager_custom.conf`

If the same AMI username is defined again later (especially in `manager_custom.conf`), the later definition wins and can silently change/remove your `permit` ACLs. The result looks like a bad password, but the real issue is an IP restriction.

## Solution

### On the FreePBX Server (192.168.5.24 / pbx.super-ht.com)

SSH into the FreePBX server and run:

```bash
# Reload the AMI configuration
asterisk -rx 'manager reload'

# Verify the user exists
asterisk -rx 'manager show users'

# Show the effective ACLs for the user (this is the key check)
asterisk -rx 'manager show user 3pXw6N7PhSVI'
```

In the `manager show user` output, confirm the `deny/permit` list includes your SHTops host IP (on this repo it’s `10.10.0.24`).

### Expected Output

You should see something like:

```
username: 3pXw6N7PhSVI
       secret: <Set>
          ACL: yes
  read perm: system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
 write perm: system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
...
```

If you DON'T see the user `3pXw6N7PhSVI`, then:

1. **Verify the manager.conf file** is correct at `/etc/asterisk/manager.conf`
2. **Check for syntax errors** in the file
3. **Make sure there are no spaces in section headers** - should be `[3pXw6N7PhSVI]` not `[ 3pXw6N7PhSVI ]`
4. **Reload again** after fixing: `asterisk -rx 'manager reload'`

### Alternative: Use the Helper Script

Copy the helper script to the FreePBX server:

```bash
# From this machine (10.10.0.24)
scp /home/superht/shtops/freepbx_ami_helper.sh root@pbx.super-ht.com:/tmp/

# Then SSH and run it
ssh root@pbx.super-ht.com
cd /tmp
chmod +x freepbx_ami_helper.sh
./freepbx_ami_helper.sh
```

This will:
- Show the current configuration
- Show included override files and whether your user is duplicated
- Reload AMI
- Show connected users
- Verify the port is open

## After Reloading

Once you've reloaded the AMI configuration on the FreePBX server, test from this machine:

```bash
cd /home/superht/shtops
python3 debug_ami.py
```

If you see "✓ Authentication successful!", then run the full test:

```bash
python3 test_freepbx_ami.py
```

## Alternative Solutions

### Option 1: Create a New AMI User

If the current user doesn't work, create a new one in `/etc/asterisk/manager.conf`:

```ini
[shtops]
secret = SomeSecurePassword123
deny = 0.0.0.0/0.0.0.0
permit = 10.10.0.0/255.255.255.0
read = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
write = system,call,log,verbose,command,agent,user,config,dtmf,reporting,cdr,dialplan,originate,message
writetimeout = 5000
```

Then reload and update your `config/config.yaml`:

```yaml
freepbx:
  ami_username: "shtops"
  ami_password: "SomeSecurePassword123"
```

### Option 2: Use FreePBX GUI

1. Log into FreePBX web interface
2. Go to **Settings → Asterisk Manager Users**
3. Add a new user with:
   - Username: `shtops`
   - Secret: (strong password)
   - Permissions: Allow all
   - IP Restrictions: `10.10.0.0/255.255.255.0`

### Option 3: Check for FreePBX Module Conflicts

FreePBX sometimes has modules that override manager.conf. Check:

```bash
# Look for manager_custom.conf or manager_additional.conf
cat /etc/asterisk/manager_custom.conf
cat /etc/asterisk/manager_additional.conf

# These files are included by manager.conf
# If they exist and define the same AMI username again, the later definition wins
# and can override the permit/deny ACLs.
```

## Common Issues

### Issue 1: Special Characters in Password
If the password has special characters, try changing it to alphanumeric only.

### Issue 2: File Permissions
Make sure manager.conf is readable:
```bash
chmod 640 /etc/asterisk/manager.conf
chown asterisk:asterisk /etc/asterisk/manager.conf
```

### Issue 3: SELinux/AppArmor
If SELinux is enforcing, it might block AMI:
```bash
# Check SELinux status
getenforce

# If enforcing, temporarily disable to test
setenforce 0

# Test connection, then re-enable
setenforce 1
```

### Issue 4: Asterisk Not Reading manager.conf
Restart Asterisk completely:
```bash
systemctl restart asterisk
# or
asterisk -rx 'core restart now'
```

## Verification Commands

Run these on the FreePBX server to diagnose:

```bash
# 1. Check if AMI is listening
netstat -tlnp | grep 5038

# 2. Show AMI configuration
asterisk -rx 'manager show settings'

# 3. Show current users
asterisk -rx 'manager show users'

# 4. Check Asterisk logs for errors
tail -f /var/log/asterisk/full | grep -i manager

# 5. Test AMI locally on the FreePBX server
telnet localhost 5038
# You should see: Asterisk Call Manager/x.x.x
# Then Ctrl+] and type 'quit' to exit
```

## Quick Test Command

This one-liner tests AMI from the FreePBX server itself:

```bash
(echo "Action: Login"; echo "Username: 3pXw6N7PhSVI"; echo "Secret: Ep6CvZpiPpUr"; echo ""; sleep 1) | nc localhost 5038
```

Expected output should include `Response: Success`

## Summary

The most common fix is simply:

```bash
ssh root@pbx.super-ht.com
asterisk -rx 'manager reload'
```

After that, test from the shtops machine:

```bash
cd /home/superht/shtops && python3 debug_ami.py
```
