#!/bin/bash
# FreePBX AMI Setup Helper
# Run this script ON THE FREEPBX SERVER to verify and reload AMI configuration

echo "============================================================"
echo "FreePBX AMI Configuration Helper"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root (or with sudo)"
    exit 1
fi

echo "Step 1: Checking manager.conf..."
if [ -f /etc/asterisk/manager.conf ]; then
    echo "✓ manager.conf exists"
    echo ""
    echo "Current configuration:"
    echo "------------------------------------------------------------"
    cat /etc/asterisk/manager.conf
    echo "------------------------------------------------------------"
else
    echo "✗ manager.conf not found!"
    exit 1
fi

echo ""
echo "Step 2: Checking if Asterisk is running..."
if pgrep -x "asterisk" > /dev/null; then
    echo "✓ Asterisk is running"
else
    echo "✗ Asterisk is not running!"
    echo "  Start it with: systemctl start asterisk"
    exit 1
fi

echo ""
echo "Step 3: Reloading AMI configuration..."
asterisk -rx 'manager reload'
sleep 2

echo ""
echo "Step 4: Showing AMI status..."
echo "------------------------------------------------------------"
asterisk -rx 'manager show connected'
echo "------------------------------------------------------------"

echo ""
echo "Step 5: Showing AMI users..."
echo "------------------------------------------------------------"
asterisk -rx 'manager show users'
echo "------------------------------------------------------------"

echo ""
echo "Step 6: Testing from this server..."
echo "Attempting connection to 0.0.0.0:5038..."
if timeout 3 bash -c 'cat < /dev/null > /dev/tcp/0.0.0.0/5038'; then
    echo "✓ AMI port 5038 is accessible locally"
else
    echo "✗ Cannot connect to AMI port 5038 locally"
fi

echo ""
echo "Step 7: Checking firewall (if applicable)..."
if command -v firewall-cmd &> /dev/null; then
    echo "Firewall zones:"
    firewall-cmd --list-all-zones | grep -A 10 "public"
fi

echo ""
echo "============================================================"
echo "Summary"
echo "============================================================"
echo "If you see the user '3pXw6N7PhSVI' in the output above,"
echo "the configuration should be correct."
echo ""
echo "Next steps:"
echo "1. Verify the user exists in 'manager show users'"
echo "2. Test from the remote machine: 10.10.0.24"
echo "   cd /home/superht/shtops && python3 debug_ami.py"
echo "============================================================"
