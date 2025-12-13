"""
Blockchain Indexer Service.

Full indexing of blockchain transactions for system and user wallets.
Provides real-time monitoring of new blocks and instant access to cached data.

Key features:
- Initial full scan of system wallet history
- Real-time monitoring of new blocks
- Automatic indexing of user wallets on registration
- Zero RPC calls for historical data queries
"""

from .constants import ERC20_ABI, PLEX_DECIMALS, USDT_DECIMALS
from .core import BlockchainIndexerService
from .indexing_mixin import IndexingMixin
from .monitoring_mixin import MonitoringMixin
from .queries_mixin import QueriesMixin

__all__ = [
    "BlockchainIndexerService",
    "IndexingMixin",
    "MonitoringMixin",
    "QueriesMixin",
    "ERC20_ABI",
    "USDT_DECIMALS",
    "PLEX_DECIMALS",
]
