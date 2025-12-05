"""
Nonce Management for Payment Sender.

Handles nonce acquisition with stuck transaction detection and distributed locking
to prevent race conditions in multi-instance deployments.
"""

from typing import Any

from loguru import logger
from web3 import AsyncWeb3


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
        """
        # Get pending nonce (includes pending transactions)
        pending_nonce = await self.web3.eth.get_transaction_count(address, 'pending')
        # Get confirmed nonce (only confirmed transactions)
        confirmed_nonce = await self.web3.eth.get_transaction_count(address, 'latest')

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
        """
        from app.utils.distributed_lock import get_distributed_lock

        # Create lock key specific to this address
        lock_key = f"nonce_lock:{address}"

        # Try to get distributed lock with Redis/PostgreSQL
        if session_factory:
            async with session_factory() as session:
                distributed_lock = get_distributed_lock(session=session)

                # Acquire distributed lock with timeout
                async with distributed_lock.lock(
                    key=lock_key,
                    timeout=30,  # Lock expires after 30 seconds
                    blocking=True,
                    blocking_timeout=10.0  # Wait max 10 seconds for lock
                ):
                    # Get nonce inside the distributed lock
                    return await self.get_safe_nonce(address)
        else:
            # Fallback to no distributed lock if no session factory
            logger.debug("No session factory available, using local lock only")
            return await self.get_safe_nonce(address)
