"""
Failover Module.

Contains failover logic for the BlockchainService.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    from ..provider_manager import ProviderManager


class Failover:
    """
    Handles failover operations.

    Features:
    - Automatic provider failover
    - Maintenance mode management
    - Operation retry logic
    """

    def __init__(self, provider_manager: ProviderManager) -> None:
        """
        Initialize failover.

        Args:
            provider_manager: Provider manager instance
        """
        self.provider_manager = provider_manager

    async def execute_with_failover(
        self, operation: Callable, *args, **kwargs
    ) -> Any:
        """
        Execute blockchain operation with automatic failover (R7-5).

        Attempts operation with primary provider, falls back to HTTP if needed.

        Args:
            operation: Async function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result

        Raises:
            RuntimeError: If all providers fail and maintenance mode not set
        """
        from app.config.settings import settings

        # Check maintenance mode
        if settings.blockchain_maintenance_mode:
            raise RuntimeError(
                "Blockchain is in maintenance mode. "
                "Operations are temporarily unavailable."
            )

        try:
            # Try primary operation
            return await operation(*args, **kwargs)
        except Exception as e:
            logger.warning(
                f"Primary operation failed, attempting failover: {e}",
                extra={"operation": operation.__name__},
            )

            # Try to reconnect HTTP provider
            try:
                await self.provider_manager._connect_http()
                # Retry operation
                return await operation(*args, **kwargs)
            except Exception as failover_error:
                logger.error(
                    f"Failover also failed: {failover_error}",
                    extra={"operation": operation.__name__},
                )

                # If all providers fail, set maintenance mode
                settings.blockchain_maintenance_mode = True
                logger.critical(
                    "All blockchain providers failed. "
                    "Maintenance mode activated."
                )

                raise RuntimeError(
                    "Blockchain providers unavailable. "
                    "Maintenance mode activated."
                ) from failover_error
