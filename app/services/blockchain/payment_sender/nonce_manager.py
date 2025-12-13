"""
Nonce Management for Payment Sender.

Handles nonce acquisition with stuck transaction detection and distributed locking
to prevent race conditions in multi-instance deployments.
"""

from typing import Any

from loguru import logger
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

from app.config.operational_constants import BLOCKING_TIMEOUT_LONG, LOCK_TIMEOUT_SHORT


class NonceManager:
    """
    Manages transaction nonces with safety features.

    Features:
    - Stuck transaction detection
    - Distributed locking for multi-instance protection
    - Race condition prevention
    """

    def __init__(self, web3: AsyncWeb3):
        """
        Initialize nonce manager.

        Args:
            web3: AsyncWeb3 instance
        """
        self.web3 = web3

    async def get_safe_nonce(self, address: str) -> int:
        """
        Get nonce with stuck transaction detection.

        Args:
            address: Wallet address

        Returns:
            Safe nonce to use

        Raises:
            ValueError: If address is invalid
            Web3Exception: If Web3 provider call fails
        """
        try:
            # Get pending nonce (includes pending transactions)
            pending_nonce = await self.web3.eth.get_transaction_count(address, 'pending')
        except ValueError as e:
            logger.error(f"Invalid address format for nonce lookup: {address}", exc_info=e)
            raise
        except Web3Exception as e:
            logger.error(f"Web3 error getting pending nonce for {address}: {e}", exc_info=e)
            raise

        try:
            # Get confirmed nonce (only confirmed transactions)
            confirmed_nonce = await self.web3.eth.get_transaction_count(address, 'latest')
        except ValueError as e:
            logger.error(f"Invalid address format for nonce lookup: {address}", exc_info=e)
            raise
        except Web3Exception as e:
            logger.error(f"Web3 error getting confirmed nonce for {address}: {e}", exc_info=e)
            raise

        # If there are too many stuck transactions (pending > confirmed + threshold)
        stuck_threshold = 5
        if pending_nonce > confirmed_nonce + stuck_threshold:
            logger.warning(
                f"Possible stuck transactions detected: "
                f"pending={pending_nonce}, confirmed={confirmed_nonce}, "
                f"stuck={pending_nonce - confirmed_nonce}"
            )

        return pending_nonce

    async def get_nonce_with_distributed_lock(
        self,
        address: str,
        session_factory: Any = None
    ) -> int:
        """
        Get nonce with distributed lock for multi-instance protection.

        Uses Redis-based distributed lock to prevent nonce conflicts
        when multiple bot instances are running.

        Args:
            address: Wallet address
            session_factory: Session factory for distributed lock (optional)

        Returns:
            Safe nonce to use

        Raises:
            ImportError: If distributed lock module cannot be imported
            ValueError: If address is invalid
            Web3Exception: If Web3 provider call fails
            TimeoutError: If lock acquisition times out
            RuntimeError: If lock operations fail
        """
        try:
            from app.utils.distributed_lock import get_distributed_lock
        except ImportError as e:
            logger.error(f"Failed to import distributed_lock module: {e}", exc_info=e)
            raise

        # Create lock key specific to this address
        lock_key = f"nonce_lock:{address}"

        # Try to get distributed lock with Redis/PostgreSQL
        if session_factory:
            try:
                async with session_factory() as session:
                    distributed_lock = get_distributed_lock(session=session)

                    # Acquire distributed lock with timeout
                    try:
                        async with distributed_lock.lock(
                            key=lock_key,
                            timeout=LOCK_TIMEOUT_SHORT,
                            blocking=True,
                            blocking_timeout=BLOCKING_TIMEOUT_LONG
                        ):
                            # Get nonce inside the distributed lock
                            return await self.get_safe_nonce(address)
                    except TimeoutError as e:
                        logger.error(
                            f"Timeout acquiring distributed lock for address {address}: {e}",
                            exc_info=e
                        )
                        raise
                    except RuntimeError as e:
                        logger.error(
                            f"Runtime error with distributed lock for address {address}: {e}",
                            exc_info=e
                        )
                        raise
            except (ValueError, Web3Exception):
                # Re-raise Web3/validation exceptions from get_safe_nonce
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in distributed lock session for address {address}: {e}",
                    exc_info=e
                )
                raise RuntimeError(f"Distributed lock session error: {e}") from e
        else:
            # Fallback to no distributed lock if no session factory
            logger.debug("No session factory available, using local lock only")
            return await self.get_safe_nonce(address)
