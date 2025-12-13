"""
Session-based reward calculation module.

Handles the calculation of rewards for deposits within a specific reward session,
including ROI cap enforcement, user status validation, and statistical aggregation.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.deposit_reward import DepositReward
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from app.repositories.deposit_reward_repository import DepositRewardRepository
from app.repositories.reward_session_repository import RewardSessionRepository
from app.services.reward.reward_calculator import RewardCalculator


if TYPE_CHECKING:
    from app.services.reward.reward_balance_handler import RewardBalanceHandler


class SessionRewardProcessor:
    """Processes rewards for deposit sessions."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize session reward processor.

        Args:
            session: Database session
        """
        self.session = session
        self.session_repo = RewardSessionRepository(session)
        self.reward_repo = DepositRewardRepository(session)
        self.deposit_repo = DepositRepository(session)
        self.calculator = RewardCalculator(session)

    async def calculate_rewards_for_session(  # noqa: C901
        self,
        session_id: int,
        balance_creditor: "RewardBalanceHandler",
    ) -> tuple[bool, int, Decimal, str | None]:
        """
        Calculate rewards for session.

        CRITICAL: Respects ROI cap (500% for level 1).
        Skips deposits with earnings_blocked flag.

        Args:
            session_id: Session ID
            balance_creditor: Balance handler for crediting rewards

        Returns:
            Tuple of (success, rewards_calculated, total_amount, error)
        """
        # R17-3: Emergency stop for ROI accruals
        if settings.emergency_stop_roi:
            logger.warning(
                "Reward calculation blocked by emergency stop ROI",
                extra={"session_id": session_id},
            )
            return (
                False,
                0,
                Decimal("0"),
                "⚠️ Начисление доходности временно приостановлено администратором.",
            )

        session_obj = await self.session_repo.get_by_id(session_id)

        if not session_obj:
            return False, 0, Decimal("0"), "Сессия не найдена"

        if not session_obj.is_active:
            return False, 0, Decimal("0"), "Сессия неактивна"

        # R9-2: Find deposits in session period with pessimistic lock
        # This prevents race conditions with withdrawal operations
        # Eager load users to avoid N+1 queries
        stmt = (
            select(Deposit)
            .options(selectinload(Deposit.user))
            .where(
                Deposit.status == TransactionStatus.CONFIRMED.value,
                Deposit.confirmed_at >= session_obj.start_date,
                Deposit.confirmed_at <= session_obj.end_date,
            )
            .with_for_update()  # Lock deposits to prevent concurrent modifications
        )

        result = await self.session.execute(stmt)
        deposits = list(result.scalars().all())

        logger.info(
            "Calculating rewards for session",
            extra={
                "session_id": session_id,
                "deposits_found": len(deposits),
            },
        )

        rewards_calculated = 0
        total_reward_amount = Decimal("0")

        for deposit in deposits:
            # User is already loaded via eager loading (selectinload)
            user = deposit.user

            # CRITICAL: Skip if earnings blocked (finpass recovery)
            if user and user.earnings_blocked:
                logger.warning(
                    "Skipped deposit reward - earnings blocked",
                    extra={
                        "user_id": deposit.user_id,
                        "deposit_id": deposit.id,
                        "reason": "finpass_recovery_in_progress",
                    },
                )
                continue

            # R15-1: Skip if user is banned (stop ROI distribution)
            if user and user.is_banned:
                logger.warning(
                    "Skipped deposit reward - user banned",
                    extra={
                        "user_id": deposit.user_id,
                        "deposit_id": deposit.id,
                        "reason": "user_blocked",
                    },
                )
                continue

            # Check if reward already calculated
            existing = await self.reward_repo.find_by(
                deposit_id=deposit.id, reward_session_id=session_id
            )

            if existing:
                continue

            # R12-1: Check ROI cap for all levels (not just Level 1)
            if deposit.is_roi_completed:
                logger.info(
                    "Skipped reward - ROI cap reached",
                    extra={
                        "deposit_id": deposit.id,
                        "level": deposit.level,
                        "roi_cap": str(deposit.roi_cap_amount),
                        "roi_paid": str(deposit.roi_paid_amount),
                    },
                )
                continue

            # R17-1: Get reward rate using RewardCalculator
            reward_rate = await self.calculator.get_rate_for_level(
                deposit.level, session_id=session_id
            )

            # If RewardSession rate is 0 or deposit has version, use version's roi_percent
            has_version_roi = deposit.deposit_version and deposit.deposit_version.roi_percent
            if reward_rate == Decimal("0") or has_version_roi:
                # R17-1: Use deposit version's roi_percent as fallback/base rate
                if deposit.deposit_version:
                    # Convert roi_percent to daily rate (assuming roi_percent is annual)
                    # For now, use roi_percent directly if it's already daily
                    version_rate = deposit.deposit_version.roi_percent
                    # If RewardSession rate is 0, use version rate
                    if reward_rate == Decimal("0"):
                        reward_rate = version_rate
                    # Otherwise, RewardSession overrides (temporary promotion)
                elif reward_rate == Decimal("0"):
                    # No version and no session rate - skip
                    logger.warning(
                        f"No reward rate available for deposit {deposit.id}",
                        extra={"deposit_id": deposit.id, "level": deposit.level},
                    )
                    continue

            # Calculate reward using RewardCalculator
            reward_amount = self.calculator.calculate_reward_amount(
                deposit.amount, reward_rate, days=1
            )

            # R12-1: For all levels, cap to remaining ROI space using RewardCalculator
            if deposit.roi_cap_amount:
                reward_amount = self.calculator.cap_reward_to_remaining_roi(reward_amount, deposit)

                if reward_amount <= 0:
                    continue

            # Create reward record
            await self.reward_repo.create(
                user_id=deposit.user_id,
                deposit_id=deposit.id,
                reward_session_id=session_id,
                deposit_level=deposit.level,
                deposit_amount=deposit.amount,
                reward_rate=reward_rate,
                reward_amount=reward_amount,
                paid=False,
            )

            # R12-1: Update deposit roi_paid_amount and check for completion
            new_roi_paid = (deposit.roi_paid_amount or Decimal("0")) + reward_amount

            # Update roi_paid_amount
            await self.deposit_repo.update(
                deposit.id,
                roi_paid_amount=new_roi_paid,
            )

            # Notify user about ROI accrual
            try:
                from app.services.notification_service import (
                    NotificationService,
                )

                if user and user.telegram_id:
                    notification_service = NotificationService(self.session)
                    # Calculate ROI progress as percentage (0-100)
                    # ROI cap = 500% = deposit.amount * 5
                    roi_cap_amount = deposit.roi_cap_amount or (deposit.amount * 5)
                    roi_progress = (
                        (new_roi_paid / roi_cap_amount * 100)
                        if roi_cap_amount > 0
                        else Decimal("0")
                    )

                    # Note: Convert to float only at display layer for Telegram API
                    # Financial calculations above remain in Decimal
                    await notification_service.notify_roi_accrual(
                        telegram_id=user.telegram_id,
                        amount=float(reward_amount),
                        deposit_level=deposit.level,
                        roi_progress_percent=float(min(roi_progress, Decimal("100.0"))),
                    )
            except Exception as e:
                logger.warning(f"Failed to send ROI notification: {e}")

            # R12-1: Check if ROI cap reached for all levels using RewardCalculator
            if self.calculator.is_roi_cap_reached(deposit, total_earned=new_roi_paid):
                # Mark deposit as ROI completed with timestamp
                await self.deposit_repo.update(
                    deposit.id,
                    is_roi_completed=True,
                    completed_at=datetime.now(UTC),
                )
                logger.info(
                    "Deposit ROI completed (cap reached)",
                    extra={
                        "deposit_id": deposit.id,
                        "user_id": deposit.user_id,
                        "level": deposit.level,
                        "roi_paid": str(new_roi_paid),
                        "roi_cap": str(deposit.roi_cap_amount),
                    },
                )

            # Credit ROI to user's internal balance and create accounting transaction
            await balance_creditor.credit_roi_to_balance(
                user_id=deposit.user_id,
                reward_amount=reward_amount,
                deposit_id=deposit.id,
            )

            rewards_calculated += 1
            total_reward_amount += reward_amount

        await self.session.commit()

        logger.info(
            "Rewards calculation completed",
            extra={
                "session_id": session_id,
                "rewards_calculated": rewards_calculated,
                "total_amount": str(total_reward_amount),
            },
        )

        return True, rewards_calculated, total_reward_amount, None

    async def get_session_statistics(self, session_id: int) -> dict:
        """
        Get session statistics.

        Uses SQL aggregation to avoid OOM on large datasets.

        Args:
            session_id: Session ID

        Returns:
            Dict with comprehensive session stats
        """
        # Aggregate reward stats using SQL
        stats_stmt = select(
            func.count(DepositReward.id).label("total_rewards"),
            func.sum(
                case(
                    (DepositReward.paid == True, 1),  # noqa: E712
                    else_=0,
                )
            ).label("paid_rewards"),
            func.sum(DepositReward.reward_amount).label("total_amount"),
            func.sum(
                case(
                    (DepositReward.paid == True, DepositReward.reward_amount),  # noqa: E712
                    else_=0,
                )
            ).label("paid_amount"),
        ).where(DepositReward.reward_session_id == session_id)

        result = await self.session.execute(stats_stmt)
        stats = result.one()

        total_rewards = stats.total_rewards or 0
        paid_rewards = stats.paid_rewards or 0
        pending_rewards = total_rewards - paid_rewards

        total_amount = stats.total_amount or Decimal("0")
        paid_amount = stats.paid_amount or Decimal("0")
        pending_amount = total_amount - paid_amount

        return {
            "total_rewards": total_rewards,
            "total_amount": total_amount,
            "paid_rewards": paid_rewards,
            "paid_amount": paid_amount,
            "pending_rewards": pending_rewards,
            "pending_amount": pending_amount,
        }
