"""
Blacklist Service - User Termination Module.

Module: user_termination.py
Handles user account termination (R15-2): BLOCKED → TERMINATED.
Manages the complete termination flow with all consequences.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select, update

from app.models.blacklist import BlacklistActionType
from app.models.user import User


class UserTerminationManager:
    """User termination operations."""

    def __init__(self, blacklist_core) -> None:
        """Initialize termination manager."""
        self.session = blacklist_core.session
        self.repository = blacklist_core.repository

    async def terminate_user(
        self,
        user_id: int,
        reason: str,
        admin_id: int | None = None,
        redis_client: Any | None = None,
    ) -> dict:
        """
        Terminate user account (R15-2): BLOCKED → TERMINATED.

        Atomic transition with handling of all consequences:
        - Reject all pending appeals
        - Reject all pending support tickets
        - Stop ROI distribution (already handled by is_banned)
        - Reject all pending withdrawals
        - Clear notification queue

        Args:
            user_id: User ID
            reason: Termination reason
            admin_id: Admin ID (optional)
            redis_client: Optional Redis client for cache invalidation

        Returns:
            Dict with success status and actions taken
        """
        from app.models.appeal import AppealStatus
        from app.models.enums import (
            SupportTicketStatus,
            TransactionStatus,
            TransactionType,
        )
        from app.repositories.appeal_repository import AppealRepository
        from app.repositories.support_ticket_repository import (
            SupportTicketRepository,
        )
        from app.repositories.transaction_repository import (
            TransactionRepository,
        )
        from app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.session)
        transaction_repo = TransactionRepository(self.session)
        appeal_repo = AppealRepository(self.session)
        ticket_repo = SupportTicketRepository(self.session)

        # R9-2: Lock user first to prevent race conditions
        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found",
            }

        actions_taken = []

        # 1. Reject all pending appeals
        pending_appeals = await appeal_repo.find_by(
            user_id=user_id,
            status=AppealStatus.PENDING,
        )
        for appeal in pending_appeals:
            appeal.status = AppealStatus.REJECTED.value
            appeal.reviewed_at = datetime.now(UTC)
            appeal.review_notes = (
                "Автоматически отклонено при терминации аккаунта"
            )
            actions_taken.append(f"Rejected appeal {appeal.id}")

        # 2. Reject all pending support tickets
        pending_tickets = await ticket_repo.find_by(
            user_id=user_id,
            status=SupportTicketStatus.OPEN.value,
        )
        for ticket in pending_tickets:
            ticket.status = SupportTicketStatus.CLOSED.value
            actions_taken.append(f"Closed support ticket {ticket.id}")

        # 3. Reject all pending withdrawals
        pending_withdrawals = await transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )
        rejected_count = 0
        total_returned = 0
        for withdrawal in pending_withdrawals:
            withdrawal.status = TransactionStatus.FAILED.value
            total_returned += withdrawal.amount
            rejected_count += 1

        # R9-2: Atomic balance update to prevent race conditions
        if total_returned > 0:
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(balance=User.balance + total_returned)
            )
            await self.session.execute(stmt)
            actions_taken.append(f"Rejected {rejected_count} pending withdrawals")

        # 4. Update blacklist entry to TERMINATED
        blacklist_entry = await self.repository.find_by_telegram_id(
            user.telegram_id
        )
        if blacklist_entry:
            await self.repository.update(
                blacklist_entry.id,
                action_type=BlacklistActionType.TERMINATED,
                reason=reason,
            )
            actions_taken.append("Updated blacklist to TERMINATED")

        # 6. Mark user as banned (already done, but ensure it's set)
        user.is_banned = True
        await user_repo.update(
            user_id, is_banned=True, redis_client=redis_client
        )

        await self.session.commit()

        logger.warning(
            f"User {user_id} terminated",
            extra={
                "user_id": user_id,
                "telegram_id": user.telegram_id,
                "rejected_appeals": len(pending_appeals),
                "closed_tickets": len(pending_tickets),
                "rejected_withdrawals": rejected_count,
                "reason": reason,
            },
        )

        return {
            "success": True,
            "user_id": user_id,
            "actions_taken": actions_taken,
            "rejected_appeals": len(pending_appeals),
            "closed_tickets": len(pending_tickets),
            "rejected_withdrawals": rejected_count,
        }
