"""
Blockchain Indexer Constants.

Contains token decimals and ERC20 ABI definitions.
"""

# Token decimals
USDT_DECIMALS = 18
PLEX_DECIMALS = 18

# Minimal ERC20 ABI for Transfer events
ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    }
]
