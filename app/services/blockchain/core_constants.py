"""
Core blockchain constants and configurations.

This module contains all blockchain-related constants including:
- USDT contract ABI
- Gas price settings
- Token decimals
- Type definitions
"""

from decimal import Decimal
from typing import TypeVar

# USDT contract ABI (ERC-20 standard functions)
USDT_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
]

# PLEX ABI (ERC-20 compatible)
# PLEX token follows standard ERC-20 interface with 9 decimals
PLEX_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "_owner", "type": "address"}],
        "outputs": [{"name": "balance", "type": "uint256"}],
        "constant": True,
    },
    {
        "name": "Transfer",
        "type": "event",
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "anonymous": False,
    },
]

# USDT decimals (BEP-20 USDT uses 18 decimals)
USDT_DECIMALS = 18

# PLEX Token Configuration
PLEX_CONTRACT_ADDRESS = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"
PLEX_DECIMALS = 9
PLEX_PER_DOLLAR_DAILY = 10

# Gas settings for BSC
# 0.1 Gwei = 100_000_000 Wei (1 Gwei = 10^9 Wei)
# User requirement: Max 0.1 Gwei, try lower if possible
MIN_GAS_PRICE_GWEI = Decimal("0.01")
MAX_GAS_PRICE_GWEI = Decimal("0.1")
MIN_GAS_PRICE_WEI = int(MIN_GAS_PRICE_GWEI * 10**9)
MAX_GAS_PRICE_WEI = int(MAX_GAS_PRICE_GWEI * 10**9)

# Gas limits
DEFAULT_USDT_GAS_LIMIT = 100000  # Standard USDT transfer
DEFAULT_NATIVE_GAS_LIMIT = 21000  # Standard native BNB transfer
GAS_LIMIT_MULTIPLIER = 1.2  # Safety buffer for gas estimation

# Nonce management
NONCE_STUCK_THRESHOLD = 5  # Max pending transactions before warning

# Type variable for generic operations
T = TypeVar("T")
