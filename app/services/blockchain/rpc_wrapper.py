"""
RPC Wrapper with Timeout and Retry Logic.

Provides centralized timeout and retry functionality for all blockchain RPC calls.
"""

import asyncio
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from loguru import logger

from app.config.constants import BLOCKCHAIN_TIMEOUT

T = TypeVar("T")


class BlockchainTimeoutError(Exception):
    """Raised when blockchain RPC call times out."""
    pass


class BlockchainError(Exception):
    """Base exception for blockchain errors."""
    pass


async def with_timeout(
    coro: Any,
    timeout: float = BLOCKCHAIN_TIMEOUT,
    operation_name: str = "RPC call",
) -> Any:
    """
    Execute async coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds (default: BLOCKCHAIN_TIMEOUT)
        operation_name: Operation name for logging

    Returns:
        Result of the coroutine

    Raises:
        BlockchainTimeoutError: If operation times out
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError as e:
        error_msg = f"{operation_name} timed out after {timeout}s"
        logger.error(error_msg)
        raise BlockchainTimeoutError(error_msg) from e


async def rpc_call_with_retry(
    coro_factory: Callable[[], Any],
    max_retries: int = 3,
    timeout: float = BLOCKCHAIN_TIMEOUT,
    operation_name: str = "RPC call",
    exponential_backoff: bool = True,
) -> Any:
    """
    Execute RPC call with retry logic and timeout.

    Args:
        coro_factory: Factory function that returns a coroutine
        max_retries: Maximum number of retry attempts
        timeout: Timeout per attempt in seconds
        operation_name: Operation name for logging
        exponential_backoff: Use exponential backoff between retries

    Returns:
        Result of the RPC call

    Raises:
        BlockchainTimeoutError: If all attempts time out
        BlockchainError: If all attempts fail with errors
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            coro = coro_factory()
            result = await with_timeout(
                coro,
                timeout=timeout,
                operation_name=f"{operation_name} (attempt {attempt + 1}/{max_retries})",
            )

            # Success!
            if attempt > 0:
                logger.success(
                    f"{operation_name} succeeded on attempt {attempt + 1}"
                )

            return result

        except (BlockchainTimeoutError, Exception) as e:
            last_error = e

            if attempt < max_retries - 1:
                # Calculate delay with exponential backoff
                if exponential_backoff:
                    delay = 2 ** attempt  # 1s, 2s, 4s, 8s...
                else:
                    delay = 2  # Fixed 2s delay

                logger.warning(
                    f"{operation_name} failed on attempt {attempt + 1}/{max_retries}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries} attempts: {e}"
                )

    # All attempts failed
    if isinstance(last_error, BlockchainTimeoutError):
        raise last_error
    else:
        raise BlockchainError(
            f"{operation_name} failed after {max_retries} attempts: {last_error}"
        ) from last_error


def timeout_decorator(
    timeout: float = BLOCKCHAIN_TIMEOUT,
    operation_name: str | None = None,
):
    """
    Decorator to add timeout to async functions.

    Usage:
        @timeout_decorator(timeout=30.0, operation_name="get_balance")
        async def get_balance(self, address: str):
            return await self.web3.eth.get_balance(address)

    Args:
        timeout: Timeout in seconds
        operation_name: Operation name for logging (uses function name if None)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            return await with_timeout(
                func(*args, **kwargs),
                timeout=timeout,
                operation_name=op_name,
            )
        return wrapper
    return decorator
