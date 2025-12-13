#!/bin/bash
# Fix for AMI IPv6-only binding issue
# Run this ON THE FREEPBX SERVER as root or with sudo

echo "============================================================"
echo "FreePBX AMI IPv4 Binding Fix"
echo "============================================================"
echo ""

# Check if running with sufficient privileges
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run with sudo:"
    echo "   sudo bash $0"
    exit 1
fi

echo "Current AMI listening status:"
netstat -tlnp | grep 5038
echo ""

echo "Issue: AMI is listening on IPv6 (:::5038) but not IPv4"
echo "Fix: Update manager.conf to explicitly bind to IPv4"
echo ""

MANAGER_CONF="/etc/asterisk/manager.conf"

if [ ! -f "$MANAGER_CONF" ]; then
    echo "✗ Error: $MANAGER_CONF not found!"
    exit 1
fi

echo "Creating backup..."
cp "$MANAGER_CONF" "${MANAGER_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup created"
echo ""

echo "Updating manager.conf..."
echo "Looking for bindaddr line..."

if grep -q "^bindaddr = 0.0.0.0" "$MANAGER_CONF"; then
    echo "bindaddr is already set to 0.0.0.0"
    echo "This might be an IPv6 preference issue."
    echo ""
    echo "Solution: Try binding to specific IPv4 address instead"
    
    # Get primary IPv4 address
    IPV4_ADDR=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -1)
    
    if [ -n "$IPV4_ADDR" ]; then
        echo "Detected IPv4 address: $IPV4_ADDR"
        echo ""
        echo "Option 1: Bind to specific IP"
        sed -i "s/^bindaddr = 0.0.0.0/bindaddr = $IPV4_ADDR/" "$MANAGER_CONF"
        echo "✓ Changed bindaddr to $IPV4_ADDR"
    else
        echo "Could not detect IPv4 address"
        echo "You may need to manually edit $MANAGER_CONF"
    fi
else
    echo "bindaddr not found or not set to 0.0.0.0"
    echo "Current bindaddr line:"
    grep "^bindaddr" "$MANAGER_CONF" || echo "(none found)"
fi

echo ""
echo "Restarting Asterisk..."
systemctl restart asterisk

echo "Waiting for Asterisk to start..."
sleep 3

echo ""
echo "New AMI listening status:"
netstat -tlnp | grep 5038

echo ""
echo "Checking for IPv4 binding..."
if netstat -tlnp | grep 5038 | grep -q "0.0.0.0"; then
    echo "✓ AMI is now listening on IPv4!"
elif netstat -tlnp | grep 5038 | grep -qv ":::"; then
    echo "✓ AMI is listening on specific IPv4 address!"
else
    echo "✗ Still only listening on IPv6"
    echo ""
    echo "Alternative solution needed:"
    echo "1. Check /etc/hosts - make sure hostname resolves to IPv4"
    echo "2. Or disable IPv6: sysctl -w net.ipv6.conf.all.disable_ipv6=1"
    echo "3. Or use IPv6 address in config: ami_host = \"::1\" or \"[::1]\""
fi

echo ""
echo "============================================================"
