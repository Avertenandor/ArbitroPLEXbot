"""
Failover Executor - Unified Provider Failover Logic.

Eliminates duplicate sync/async failover implementations across blockchain services.
Provides a single, reusable component for automatic provider switching on failure.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

from loguru import logger as default_logger

T = TypeVar("T")


class FailoverExecutor:
    """
    Execute operations with automatic provider failover.

    Features:
    - Manages multiple blockchain providers (QuickNode, NodeReal, etc.)
    - Automatic failover on provider failure
    - Configurable retry strategy
    - Support for both sync and async operations
    - Thread pool executor for sync Web3 calls

    Usage:
        providers = [web3_quicknode, web3_nodereal]
        executor = FailoverExecutor(providers, logger)

        # Execute with automatic failover
        result = await executor.execute(
            operation=lambda provider: provider.eth.block_number,
            operation_name="get_block_number"
        )
    """

    def __init__(
        self,
        providers: list[Any],
        logger: Any = None,
        max_workers: int = 4,
    ) -> None:
        """
        Initialize failover executor.

        Args:
            providers: List of Web3 provider instances
            logger: Logger instance (defaults to loguru logger)
            max_workers: Thread pool size for sync operations
        """
        if not providers:
            raise ValueError("At least one provider must be specified")

        self.providers = providers
        self.current_provider_index = 0
        self.logger = logger or default_logger

        # Thread pool for sync Web3 operations
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="failover"
        )

        # Track failover statistics
        self._failover_count = 0
        self._success_count = 0
        self._failure_count = 0

        self.logger.info(
            f"FailoverExecutor initialized with {len(providers)} providers"
        )

    async def execute(
        self,
        operation: Callable[[Any], T],
        operation_name: str,
        max_retries: int = 3,
        is_sync: bool = True,
    ) -> T:
        """
        Execute operation with automatic provider failover.

        Tries current provider first, then fails over to next provider on error.
        Continues retrying across all providers up to max_retries times.

        Args:
            operation: Function that takes provider and returns result
                      For sync: lambda provider: provider.eth.block_number
                      For async: async lambda provider: await some_async_call(provider)
            operation_name: Human-readable operation name for logging
            max_retries: Maximum retry attempts across all providers (default: 3)
            is_sync: Whether operation is synchronous (default: True)
                    Set False for async operations

        Returns:
            Operation result

        Raises:
            RuntimeError: If all providers fail after max_retries
        """
        last_error: Exception | None = None
        attempts = 0
        providers_tried = set()

        self.logger.debug(
            f"[{operation_name}] Starting execution with "
            f"{len(self.providers)} providers available"
        )

        while attempts < max_retries:
            attempts += 1
            provider = self.get_current_provider()
            provider_name = self._get_provider_name(self.current_provider_index)

            # Avoid retrying same provider consecutively if other options exist
            if (
                len(self.providers) > 1
                and self.current_provider_index in providers_tried
                and len(providers_tried) < len(self.providers)
            ):
                if not self._switch_provider():
                    break
                continue

            providers_tried.add(self.current_provider_index)

            self.logger.debug(
                f"[{operation_name}] Attempt {attempts}/{max_retries} "
                f"using provider {provider_name}"
            )

            # Try executing operation on current provider
            success, result, error = await self._try_provider(
                provider, operation, operation_name, is_sync
            )

            if success:
                self._success_count += 1
                self.logger.debug(
                    f"[{operation_name}] Success on provider {provider_name}"
                )
                return result

            # Operation failed, log and try failover
            last_error = error
            self._failure_count += 1

            self.logger.warning(
                f"[{operation_name}] Failed on provider {provider_name}: {error}"
            )

            # Try switching to next provider
            if not self._switch_provider():
                self.logger.error(
                    f"[{operation_name}] No more providers available for failover"
                )
                break

            self._failover_count += 1
            self.logger.info(
                f"[{operation_name}] Switched to provider "
                f"{self._get_provider_name(self.current_provider_index)}"
            )

        # All retries exhausted
        error_msg = (
            f"Operation '{operation_name}' failed after {attempts} attempts "
            f"across {len(providers_tried)} providers. "
            f"Last error: {last_error}"
        )
        self.logger.error(error_msg)

        raise RuntimeError(error_msg) from last_error

    async def _try_provider(
        self,
        provider: Any,
        operation: Callable[[Any], T],
        operation_name: str,
        is_sync: bool,
    ) -> tuple[bool, T | None, Exception | None]:
        """
        Try executing operation on specific provider.

        Args:
            provider: Web3 provider instance
            operation: Operation callable
            operation_name: Operation name for logging
            is_sync: Whether operation is synchronous

        Returns:
            Tuple of (success, result, error)
        """
        try:
            if is_sync:
                # Execute sync operation in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: operation(provider)
                )
            else:
                # Execute async operation directly
                result = await operation(provider)

            return (True, result, None)

        except Exception as e:
            self.logger.debug(
                f"[{operation_name}] Provider operation failed: {type(e).__name__}: {e}"
            )
            return (False, None, e)

    def _switch_provider(self) -> bool:
        """
        Switch to next available provider.

        Returns:
            True if switched to new provider, False if no more providers available
        """
        if len(self.providers) <= 1:
            return False

        old_index = self.current_provider_index
        self.current_provider_index = (old_index + 1) % len(self.providers)

        # If we've cycled back to start, no more unique providers
        if self.current_provider_index == 0 and old_index != 0:
            return False

        return True

    def get_current_provider(self) -> Any:
        """
        Get currently active provider.

        Returns:
            Current Web3 provider instance

        Raises:
            RuntimeError: If no providers available
        """
        if not self.providers:
            raise RuntimeError("No providers available")

        if self.current_provider_index >= len(self.providers):
            self.current_provider_index = 0

        return self.providers[self.current_provider_index]

    def reset_providers(self) -> None:
        """
        Reset to primary (first) provider.

        Use after successful operation to prefer primary provider.
        """
        old_index = self.current_provider_index
        self.current_provider_index = 0

        if old_index != 0:
            self.logger.info(
                f"Reset to primary provider: "
                f"{self._get_provider_name(0)}"
            )

    def get_stats(self) -> dict[str, Any]:
        """
        Get failover execution statistics.

        Returns:
            Dict with success_count, failure_count, failover_count
        """
        return {
            "providers_count": len(self.providers),
            "current_provider": self._get_provider_name(self.current_provider_index),
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "failover_count": self._failover_count,
        }

    def _get_provider_name(self, index: int) -> str:
        """
        Get human-readable provider name.

        Args:
            index: Provider index

        Returns:
            Provider name (e.g., "provider_0", "QuickNode", etc.)
        """
        provider = self.providers[index]

        # Try to get provider name from common attributes
        if hasattr(provider, "provider"):
            endpoint = getattr(provider.provider, "endpoint_uri", None)
            if endpoint:
                if "quicknode" in endpoint.lower():
                    return "QuickNode"
                elif "nodereal" in endpoint.lower():
                    return "NodeReal"

        return f"provider_{index}"

    def close(self) -> None:
        """
        Shutdown thread pool executor.

        Call this when done with the failover executor.
        """
        if hasattr(self, "_executor") and self._executor:
            self._executor.shutdown(wait=True)
            self.logger.debug("FailoverExecutor thread pool shut down")
