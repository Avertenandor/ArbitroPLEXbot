#!/usr/bin/env python3
"""Test RPC connection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web3 import Web3
from app.config.settings import settings

print(f"RPC URL: {settings.rpc_url}")

w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 30}))
print(f"Connected: {w3.is_connected()}")

if w3.is_connected():
    print(f"Block: {w3.eth.block_number}")
else:
    print("FAILED to connect!")
