"""
Blacklist Service - User Blocking Module.

Module: user_blocking.py
Handles user blocking with active operations (R15-1, R15-4).
Uses distributed locks to prevent race conditions.
"""

from typing import Any

from loguru import logger

from app.models.blacklist import BlacklistActionType


class UserBlockingManager:
    """User blocking operations."""

    def __init__(self, blacklist_core) -> None:
        """Initialize blocking manager."""
        self.session = blacklist_core.session
        self.repository = blacklist_core.repository

    async def block_user_with_active_operations(
        self,
        user_id: int,
        reason: str,
        admin_id: int | None = None,
        redis_client: Any | None = None,
    ) -> dict:
        """
        Block user and handle active operations (R15-1, R15-4).

        R15-4: Uses distributed lock to prevent race conditions.

        Policy:
        - Stop ROI distribution
        - Freeze pending withdrawals (mark as FROZEN)
        - Continue referral earnings (not blocked)

        Args:
            user_id: User ID
            reason: Block reason
            admin_id: Admin ID (optional)
            redis_client: Optional Redis client for distributed lock

        Returns:
            Dict with success status and actions taken
        """
        # R15-4: Use distributed lock to prevent race conditions
        from app.utils.distributed_lock import get_distributed_lock

        lock = get_distributed_lock(
            redis_client=redis_client, session=self.session
        )
        lock_key = f"user:{user_id}:block_operation"

        async with lock.lock(lock_key, timeout=30, blocking=True, blocking_timeout=5.0) as acquired:
            if not acquired:
                logger.warning(
                    f"Could not acquire lock for blocking user {user_id}, "
                    "operation may be in progress"
                )
                return {
                    "success": False,
                    "error": "Operation already in progress",
                    "actions_taken": [],
                }

            from app.models.enums import TransactionStatus, TransactionType
            from app.repositories.deposit_repository import DepositRepository
            from app.repositories.transaction_repository import (
                TransactionRepository,
            )
            from app.repositories.user_repository import UserRepository

            user_repo = UserRepository(self.session)
            transaction_repo = TransactionRepository(self.session)
            DepositRepository(self.session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                return {
                    "success": False,
                    "error": "User not found",
                }

            actions_taken = []

            # 1. Freeze pending withdrawals
            pending_withdrawals = await transaction_repo.get_by_user(
                user_id=user_id,
                type=TransactionType.WITHDRAWAL.value,
                status=TransactionStatus.PENDING.value,
            )

            frozen_count = 0
            for withdrawal in pending_withdrawals:
                withdrawal.status = TransactionStatus.FROZEN.value
                frozen_count += 1

            if frozen_count > 0:
                actions_taken.append(f"Frozen {frozen_count} pending withdrawals")

            # 2. Mark user as banned and block earnings (stop ROI distribution)
            user.is_banned = True
            await user_repo.update(
                user_id,
                is_banned=True,
                earnings_blocked=True,
                redis_client=redis_client,
            )

            # 3. Add to blacklist
            # Import the parent class to avoid circular imports
            from .core import BlacklistCore
            blacklist_core = BlacklistCore(self.session)
            await blacklist_core.add_to_blacklist(
                telegram_id=user.telegram_id,
                wallet_address=user.wallet_address,
                reason=reason,
                added_by_admin_id=admin_id,
                action_type=BlacklistActionType.BLOCKED,
            )

            await self.session.commit()

            logger.warning(
                f"User {user_id} blocked with active operations",
                extra={
                    "user_id": user_id,
                    "telegram_id": user.telegram_id,
                    "frozen_withdrawals": frozen_count,
                    "reason": reason,
                },
            )

            return {
                "success": True,
                "user_id": user_id,
                "actions_taken": actions_taken,
                "frozen_withdrawals": frozen_count,
            }
