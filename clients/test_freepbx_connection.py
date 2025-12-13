#!/usr/bin/env python3
"""DEPRECATED: FreePBX GraphQL/OAuth connection test.

SHTops uses AMI (Asterisk Manager Interface) as the supported integration.
This script is retained only for historical reference.

Use instead:
    - `python3 test_freepbx_ami.py`
    - `python3 -m collectors.freepbx.collect`
"""

import sys


if __name__ == '__main__':
    print("This script is deprecated (GraphQL/OAuth path).")
    print("Use AMI instead:")
    print("  python3 test_freepbx_ami.py")
    print("  python3 -m collectors.freepbx.collect")
    sys.exit(2)
