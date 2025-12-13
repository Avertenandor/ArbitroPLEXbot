"""
Blockchain Indexer Queries Mixin.

Provides query methods to retrieve cached transaction data.
All methods query from database cache - zero RPC calls.
"""

from decimal import Decimal

from loguru import logger

from app.models.blockchain_tx_cache import BlockchainTxCache
from app.utils.security import mask_address


class QueriesMixin:
    """Mixin providing query methods for cached blockchain data."""

    async def get_user_total_deposits(
        self,
        wallet_address: str,
        token_type: str = "USDT",
    ) -> Decimal:
        """
        Get user's total deposits from cache.

        Zero RPC calls - pure database query.

        Args:
            wallet_address: User's wallet address
            token_type: Token type (USDT or PLEX)

        Returns:
            Total deposit amount
        """
        if not self.system_wallet:
            return Decimal("0")

        return await self.cache_repo.get_total_deposits(
            user_wallet=wallet_address.lower(),
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_user_deposit_transactions(
        self,
        wallet_address: str,
        token_type: str = "USDT",
    ) -> list[BlockchainTxCache]:
        """
        Get user's deposit transactions from cache.

        Zero RPC calls - pure database query.

        Args:
            wallet_address: User's wallet address
            token_type: Token type (USDT or PLEX)

        Returns:
            List of deposit transactions
        """
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_user_deposits(
            user_wallet=wallet_address.lower(),
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_system_incoming(
        self,
        token_type: str = "USDT",
        limit: int = 100,
    ) -> list[BlockchainTxCache]:
        """
        Get all incoming transactions to system wallet.

        Args:
            token_type: Token type (USDT or PLEX)
            limit: Maximum number of transactions (unused, kept for API)

        Returns:
            List of incoming transactions
        """
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_incoming_for_system(
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_system_outgoing(
        self,
        token_type: str = "USDT",
        limit: int = 100,
    ) -> list[BlockchainTxCache]:
        """
        Get all outgoing transactions from system wallet.

        Args:
            token_type: Token type (USDT or PLEX)
            limit: Maximum number of transactions (unused, kept for API)

        Returns:
            List of outgoing transactions
        """
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_outgoing_from_system(
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def is_tx_indexed(self, tx_hash: str) -> bool:
        """
        Check if a transaction is already indexed.

        Args:
            tx_hash: Transaction hash

        Returns:
            True if transaction is in cache
        """
        return await self.cache_repo.tx_exists(tx_hash)

    async def get_cache_stats(self) -> dict:
        """
        Get statistics about cached transactions.

        Returns:
            Dictionary with cache statistics
        """
        if not self.system_wallet:
            return {"error": "System wallet not configured"}

        usdt_in = await self.cache_repo.get_incoming_for_system(
            self.system_wallet, "USDT"
        )
        usdt_out = await self.cache_repo.get_outgoing_from_system(
            self.system_wallet, "USDT"
        )
        plex_in = await self.cache_repo.get_incoming_for_system(
            self.system_wallet, "PLEX"
        )
        plex_out = await self.cache_repo.get_outgoing_from_system(
            self.system_wallet, "PLEX"
        )

        last_usdt = await self.get_last_indexed_block("USDT")
        last_plex = await self.get_last_indexed_block("PLEX")
        latest = self.w3.eth.block_number

        return {
            "system_wallet": mask_address(self.system_wallet),
            "usdt": {
                "incoming_count": len(usdt_in),
                "outgoing_count": len(usdt_out),
                "incoming_total": sum(tx.amount for tx in usdt_in),
                "outgoing_total": sum(tx.amount for tx in usdt_out),
                "last_indexed_block": last_usdt,
            },
            "plex": {
                "incoming_count": len(plex_in),
                "outgoing_count": len(plex_out),
                "incoming_total": sum(tx.amount for tx in plex_in),
                "outgoing_total": sum(tx.amount for tx in plex_out),
                "last_indexed_block": last_plex,
            },
            "latest_block": latest,
            "blocks_behind_usdt": (
                latest - last_usdt if last_usdt else "Not indexed"
            ),
            "blocks_behind_plex": (
                latest - last_plex if last_plex else "Not indexed"
            ),
        }
