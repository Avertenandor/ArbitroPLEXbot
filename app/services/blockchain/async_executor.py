"""
Async executor for blockchain operations with failover support.

Provides async execution of synchronous Web3 operations with automatic
failover between multiple RPC providers.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from loguru import logger

from app.config.constants import BLOCKCHAIN_EXECUTOR_TIMEOUT


class AsyncBlockchainExecutor:
    """
    Async executor for blockchain operations.

    Handles:
    - Thread pool execution of sync Web3 calls
    - Automatic failover between providers
    - RPC rate limiting
    - Timeout handling
    """

    def __init__(
        self,
        provider_manager: Any,
        rpc_limiter: Any,
        max_workers: int = 4,
    ) -> None:
        """
        Initialize async executor.

        Args:
            provider_manager: SyncProviderManager instance
            rpc_limiter: RPCRateLimiter instance
            max_workers: Maximum thread pool workers
        """
        self.provider_manager = provider_manager
        self.rpc_limiter = rpc_limiter
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="web3"
        )

    async def run_with_failover(self, sync_func: Callable[[Any], Any]) -> Any:
        """
        Run a synchronous Web3 function with failover logic.

        Args:
            sync_func: Synchronous function that takes Web3 instance as argument

        Returns:
            Result from the function

        Raises:
            Exception: If all providers fail
        """
        try:
            await self.provider_manager._update_settings_from_db()
            loop = asyncio.get_running_loop()

            current_name = self.provider_manager.active_provider_name

            # Try primary provider
            try:
                # Check primary provider exists
                if current_name not in self.provider_manager.providers and self.provider_manager.providers:
                    current_name = next(iter(self.provider_manager.providers))

                if current_name not in self.provider_manager.providers:
                    raise ConnectionError("No providers available")

                w3 = self.provider_manager.providers[current_name]

                async with self.rpc_limiter:
                    try:
                        return await asyncio.wait_for(
                            loop.run_in_executor(
                                self._executor,
                                lambda: sync_func(w3)
                            ),
                            timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                        )
                    except TimeoutError:
                        logger.error(f"Timeout in blockchain operation on provider '{current_name}'")
                        raise TimeoutError(f"Blockchain operation timeout on {current_name}")
            except Exception as e:
                if not self.provider_manager.is_auto_switch_enabled:
                    raise e

                logger.warning(f"Primary provider '{current_name}' failed: {e}. Trying failover...")

                # Find backup provider
                backup_name = next(
                    (n for n in self.provider_manager.providers if n != current_name), None
                )
                if not backup_name:
                    raise e

                # Try backup provider
                try:
                    logger.info(f"Switching to backup: {backup_name}")
                    w3_backup = self.provider_manager.providers[backup_name]

                    async with self.rpc_limiter:
                        try:
                            result = await asyncio.wait_for(
                                loop.run_in_executor(
                                    self._executor,
                                    lambda: sync_func(w3_backup)
                                ),
                                timeout=BLOCKCHAIN_EXECUTOR_TIMEOUT,
                            )
                        except TimeoutError:
                            logger.error(
                                f"Timeout in blockchain operation on backup provider '{backup_name}'"
                            )
                            raise TimeoutError(f"Blockchain operation timeout on backup {backup_name}")

                    # If success, switch permanent
                    self.provider_manager.active_provider_name = backup_name
                    if self.provider_manager.session_factory:
                        asyncio.create_task(
                            self.provider_manager._safe_persist_provider_switch(backup_name)
                        )

                    return result
                except Exception as e2:
                    logger.error(f"Backup provider failed: {e2}")
                    raise e
        except asyncio.CancelledError:
            logger.warning("Blockchain operation cancelled, performing cleanup")
            raise  # Always re-raise CancelledError

    def cleanup(self) -> None:
        """Clean up thread pool executor."""
        if self._executor:
            self._executor.shutdown(wait=True)
