#!/usr/bin/env python3
"""Test Composio YouTube integration."""
import os
import json
import sys

# Read COMPOSIO_API_KEY
env_path = os.path.expanduser("~/.hermes/.env")
composio_key = None
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if line.startswith('COMPOSIO_API_KEY=***            composio_key = line.split('=', 1)[1]
            break

print(f"Composio key found: {bool(composio_key)} (len={len(composio_key) if composio_key else 0})")
os.environ['COMPOSIO_API_KEY'] = composio_key

from composio import Composio
client = Composio(api_key=composio_key)

# List connected accounts
print("\n=== Connected Accounts ===")
try:
    accounts = client.connected_accounts.get()
    print(json.dumps(accounts, indent=2, default=str)[:3000])
except Exception as e:
    print(f"Error: {e}")

# Try to list available tools/actions
print("\n=== Available Tools ===")
try:
    tools = client.tools.list()
    print(json.dumps(tools, indent=2, default=str)[:3000])
except Exception as e:
    print(f"Error: {e}")
