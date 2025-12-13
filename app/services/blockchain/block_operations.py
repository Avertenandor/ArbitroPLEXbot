"""
Block operations module.

Provides utilities for working with blockchain blocks.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from app.config.constants import BLOCKCHAIN_EXECUTOR_TIMEOUT


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
        # Update settings from DB first (async operation)
        await self.provider_manager._update_settings_from_db()

        # Get active Web3 instance
        w3 = self.provider_manager.get_active_web3()

        loop = asyncio.get_running_loop()
        async with self.rpc_limiter:
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        lambda: w3.eth.block_number  # Synchronous call in thread pool
                    ),
                    timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                )
            except TimeoutError:
                # Try failover if enabled
                if self.provider_manager.is_auto_switch_enabled:
                    backup_name = next(
                        (n for n in self.provider_manager.providers
                         if n != self.provider_manager.active_provider_name),
                        None
                    )
                    if backup_name:
                        w3_backup = self.provider_manager.providers[backup_name]
                        return await asyncio.wait_for(
                            loop.run_in_executor(
                                self._executor,
                                lambda: w3_backup.eth.block_number
                            ),
                            timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                        )
                raise
