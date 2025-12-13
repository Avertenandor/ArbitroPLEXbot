"""
Blockchain Indexer Core Service.

Main service class that combines all indexer functionality.
Inherits from mixins to provide indexing, monitoring, and query methods.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.config.settings import settings
from app.repositories.blockchain_tx_cache_repository import (
    BlockchainTxCacheRepository,
)
from app.repositories.user_repository import UserRepository

from .indexing_mixin import IndexingMixin
from .monitoring_mixin import MonitoringMixin
from .queries_mixin import QueriesMixin


class BlockchainIndexerService(IndexingMixin, MonitoringMixin, QueriesMixin):
    """
    Complete blockchain indexer for transaction history.

    Maintains a full cache of all transactions involving:
    - System wallet (all incoming/outgoing)
    - Each user's wallet (relevant to system)

    After initial indexing, only monitors new blocks.

    Key features:
    - Initial full scan of system wallet history
    - Real-time monitoring of new blocks
    - Automatic indexing of user wallets on registration
    - Zero RPC calls for historical data queries
    """

    def __init__(self, session: AsyncSession, w3: Web3):
        """
        Initialize indexer.

        Args:
            session: Database session
            w3: Web3 instance
        """
        self.session = session
        self.w3 = w3
        self.cache_repo = BlockchainTxCacheRepository(session)
        self.user_repo = UserRepository(session)

        # Configuration
        sys_wallet = settings.system_wallet_address
        self.system_wallet = sys_wallet.lower() if sys_wallet else None

        usdt_addr = settings.usdt_contract_address
        self.usdt_address = usdt_addr.lower() if usdt_addr else None

        plex_addr = settings.auth_plex_token_address
        self.plex_address = plex_addr.lower() if plex_addr else None

        # Indexing settings
        self.chunk_size = 2000  # Blocks per chunk (safe for QuickNode)
        self.initial_scan_blocks = 500000  # ~17 days on BSC

    async def get_last_indexed_block(self, token_type: str) -> int:
        """
        Get the last block we have indexed for a token type.

        Args:
            token_type: Token type (USDT or PLEX)

        Returns:
            Last indexed block number
        """
        return await self.cache_repo.get_latest_block(token_type)
