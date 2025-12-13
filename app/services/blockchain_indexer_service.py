"""
Blockchain Indexer Service.

DEPRECATED: This module is kept for backward compatibility.
Import from app.services.blockchain_indexer instead.

Full indexing of blockchain transactions for system and user wallets.
Provides real-time monitoring of new blocks and instant access to cached data.

Key features:
- Initial full scan of system wallet history
- Real-time monitoring of new blocks
- Automatic indexing of user wallets on registration
- Zero RPC calls for historical data queries
"""

# Re-export from new modular structure for backward compatibility
from app.services.blockchain_indexer import (
    BlockchainIndexerService,
    ERC20_ABI,
    PLEX_DECIMALS,
    USDT_DECIMALS,
)

__all__ = [
    "BlockchainIndexerService",
    "ERC20_ABI",
    "USDT_DECIMALS",
    "PLEX_DECIMALS",
]
