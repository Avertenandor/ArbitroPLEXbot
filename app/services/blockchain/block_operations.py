"""
Block operations module.

Provides utilities for working with blockchain blocks.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from web3 import Web3

if TYPE_CHECKING:
    from app.services.blockchain.rpc_rate_limiter import RPCRateLimiter
    from app.services.blockchain.sync_provider_manager import SyncProviderManager


class BlockOperations:
    """Block-related operations."""

    def __init__(
        self,
        provider_manager: "SyncProviderManager",
        rpc_limiter: "RPCRateLimiter",
        executor: ThreadPoolExecutor,
    ) -> None:
        """
        Initialize block operations.

        Args:
            provider_manager: SyncProviderManager instance
            rpc_limiter: RPCRateLimiter instance
            executor: Thread pool executor
        """
        self.provider_manager = provider_manager
        self.rpc_limiter = rpc_limiter
        self._executor = executor

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Current block number
        """
        loop = asyncio.get_event_loop()
        async with self.rpc_limiter:
            return await loop.run_in_executor(
                self._executor,
                lambda: asyncio.run(
                    self.provider_manager._execute_with_failover(
                        lambda w3: w3.eth.block_number
                    )
                )
            )
