"""
Bonus Service.

Manages admin-granted bonus credits that participate in ROI calculations.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.bonus_credit import BonusCredit
from app.repositories.bonus_credit_repository import BonusCreditRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.repositories.user_repository import UserRepository
from app.services.base_service import BaseService


class BonusService(BaseService):
    """
    Service for managing bonus credits.

    Bonus credits are admin-granted amounts that:
    - Act as virtual deposits for ROI calculations
    - Have their own ROI cap (typically 500% like regular deposits)
    - Participate in the same reward accrual system as deposits
    - Are tracked separately from regular deposits
    """

    # Default accrual period (hours)
    DEFAULT_ACCRUAL_PERIOD_HOURS = 1

    def __init__(self, session: AsyncSession) -> None:
        """Initialize bonus service."""
        super().__init__(session)
        self.bonus_repo = BonusCreditRepository(session)
        self.user_repo = UserRepository(session)

    async def grant_bonus(
        self,
        user_id: int,
        amount: Decimal,
        reason: str,
        admin_id: int,
        roi_cap_multiplier: Decimal | None = None,
    ) -> tuple[BonusCredit | None, str | None]:
        """
        Grant a bonus credit to a user.

        Args:
            user_id: User receiving the bonus
            amount: Bonus amount in USDT equivalent
            reason: Admin's reason for granting
            admin_id: Admin granting the bonus
            roi_cap_multiplier: Custom ROI cap (default 5.0 = 500%)

        Returns:
            Tuple of (BonusCredit, error_message)
        """
        # Validate amount
        if amount <= 0:
            return None, "Сумма бонуса должна быть положительной"

        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None, "Пользователь не найден"

        # Calculate ROI cap
        cap_multiplier = roi_cap_multiplier or Decimal(str(settings.roi_cap_multiplier))
        roi_cap_amount = amount * cap_multiplier

        # Set first accrual time
        now = datetime.now(UTC)
        next_accrual = now + timedelta(hours=self.DEFAULT_ACCRUAL_PERIOD_HOURS)

        # Create bonus credit
        bonus = BonusCredit(
            user_id=user_id,
            admin_id=admin_id,
            amount=amount,
            roi_cap_multiplier=cap_multiplier,
            roi_cap_amount=roi_cap_amount,
            roi_paid_amount=Decimal("0"),
            next_accrual_at=next_accrual,
            is_active=True,
            is_roi_completed=False,
            reason=reason,
            created_at=now,
        )

        self.session.add(bonus)

        # Update user's bonus_balance
        new_bonus_balance = (user.bonus_balance or Decimal("0")) + amount
        user.bonus_balance = new_bonus_balance

        await self.session.flush()

        msg = (
            f"Granted bonus to user {user_id}: {amount} USDT "
            f"(ROI cap: {roi_cap_amount} USDT, admin: {admin_id})"
        )
        logger.info(msg)

        return bonus, None

    async def cancel_bonus(
        self,
        bonus_id: int,
        admin_id: int,
        reason: str,
    ) -> tuple[bool, str | None]:
        """
        Cancel an active bonus credit.

        Args:
            bonus_id: Bonus credit ID to cancel
            admin_id: Admin performing cancellation
            reason: Reason for cancellation

        Returns:
            Tuple of (success, error_message)
        """
        bonus = await self.bonus_repo.get_with_user(bonus_id)
        if not bonus:
            return False, "Бонус не найден"

        if not bonus.is_active:
            return False, "Бонус уже неактивен"

        now = datetime.now(UTC)

        # Cancel the bonus
        cancelled = await self.bonus_repo.cancel(
            bonus_id=bonus_id,
            cancelled_by=admin_id,
            cancel_reason=reason,
            cancelled_at=now,
        )

        if not cancelled:
            return False, "Не удалось отменить бонус"

        # Update user's bonus_balance
        if bonus.user:
            current_balance = bonus.user.bonus_balance or Decimal("0")
            # Only subtract the original amount, not ROI
            new_balance = max(Decimal("0"), current_balance - bonus.amount)
            bonus.user.bonus_balance = new_balance

        await self.session.flush()

        msg = (
            f"Cancelled bonus {bonus_id} for user {bonus.user_id} "
            f"(admin: {admin_id}, reason: {reason})"
        )
        logger.info(msg)

        return True, None

    async def get_user_bonuses(
        self,
        user_id: int,
        active_only: bool = False,
    ) -> list[BonusCredit]:
        """
        Get bonus credits for a user.

        Args:
            user_id: User ID
            active_only: Only return active bonuses

        Returns:
            List of bonus credits
        """
        if active_only:
            return await self.bonus_repo.get_active_by_user(user_id)
        return await self.bonus_repo.get_all_by_user(user_id)

    async def get_user_bonus_stats(self, user_id: int) -> dict[str, Any]:
        """
        Get bonus statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with bonus statistics
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {
                "total_bonus_balance": Decimal("0"),
                "total_bonus_roi_earned": Decimal("0"),
                "active_bonuses_count": 0,
                "total_bonuses_count": 0,
            }

        all_bonuses = await self.bonus_repo.get_all_by_user(user_id)
        active_bonuses = [b for b in all_bonuses if b.is_active]

        total_roi_earned = sum(b.roi_paid_amount for b in all_bonuses)

        return {
            "total_bonus_balance": user.bonus_balance or Decimal("0"),
            "total_bonus_roi_earned": total_roi_earned,
            "active_bonuses_count": len(active_bonuses),
            "total_bonuses_count": len(all_bonuses),
            "active_bonuses": active_bonuses,
            "all_bonuses": all_bonuses,
        }

    async def get_total_active_bonus(self, user_id: int) -> Decimal:
        """
        Get total active bonus amount for a user.

        Args:
            user_id: User ID

        Returns:
            Total active bonus amount
        """
        return await self.bonus_repo.get_total_active_bonus(user_id)

    async def process_bonus_rewards(self) -> dict[str, Any]:
        """
        Process ROI rewards for all due bonus credits.

        This is called by the reward accrual task to process
        bonus credits alongside regular deposits.

        Returns:
            Dict with processing statistics
        """
        from app.services.reward.reward_calculator import RewardCalculator
        from app.services.roi_corridor_service import RoiCorridorService

        now = datetime.now(UTC)
        stats = {
            "processed": 0,
            "total_rewards": Decimal("0"),
            "completed": 0,
            "errors": 0,
        }

        corridor_service = RoiCorridorService(self.session)
        calculator = RewardCalculator(self.session)

        settings_repo = GlobalSettingsRepository(self.session)
        project_start_at = await settings_repo.get_project_start_at()
        if now < project_start_at:
            return stats

        period_hours = await corridor_service.get_accrual_period_hours()
        normalized_next_accrual = project_start_at + timedelta(hours=period_hours)
        await self.session.execute(
            update(BonusCredit)
            .where(
                BonusCredit.is_active.is_(True),
                BonusCredit.is_roi_completed.is_(False),
                (BonusCredit.next_accrual_at.is_(None))
                | (BonusCredit.next_accrual_at < project_start_at),
            )
            .values(next_accrual_at=normalized_next_accrual)
        )

        # Get due bonus credits
        due_bonuses = await self.bonus_repo.get_due_for_accrual(now)

        if not due_bonuses:
            return stats

        # Get corridor config (use level 1 settings for bonuses)
        config = await corridor_service.get_corridor_config(1)

        for bonus in due_bonuses:
            try:
                # Determine rate
                if config["mode"] == "custom":
                    rate = corridor_service.generate_rate_from_corridor(
                        config["roi_min"], config["roi_max"]
                    )
                else:
                    rate = config["roi_fixed"]

                # Calculate reward
                reward_amount = calculator.calculate_reward_amount(
                    bonus.amount, rate, days=1
                )

                # Cap to remaining ROI
                remaining_roi = bonus.roi_cap_amount - bonus.roi_paid_amount
                if reward_amount > remaining_roi:
                    reward_amount = remaining_roi

                if reward_amount <= 0:
                    continue

                # Update bonus ROI tracking
                new_roi_paid = bonus.roi_paid_amount + reward_amount
                is_completed = new_roi_paid >= bonus.roi_cap_amount

                # Get accrual period
                next_accrual = now + timedelta(hours=period_hours)

                await self.bonus_repo.update_roi(
                    bonus_id=bonus.id,
                    roi_paid_amount=new_roi_paid,
                    next_accrual_at=next_accrual if not is_completed else None,
                    is_completed=is_completed,
                    completed_at=now if is_completed else None,
                )

                # Credit reward to user balance
                user = await self.user_repo.get_by_id(bonus.user_id)
                if user:
                    user.balance = (user.balance or Decimal("0")) + reward_amount
                    user.total_earned = (
                        (user.total_earned or Decimal("0")) + reward_amount
                    )
                    user.bonus_roi_earned = (
                        (user.bonus_roi_earned or Decimal("0")) + reward_amount
                    )

                stats["processed"] += 1
                stats["total_rewards"] += reward_amount

                if is_completed:
                    stats["completed"] += 1
                    msg = (
                        f"Bonus {bonus.id} ROI completed for user "
                        f"{bonus.user_id}: total paid {new_roi_paid} USDT"
                    )
                    logger.info(msg)

            except Exception as e:
                logger.error(f"Error processing bonus {bonus.id}: {e}")
                stats["errors"] += 1

        await self.session.commit()

        msg = (
            f"Bonus rewards processed: {stats['processed']} bonuses, "
            f"{stats['total_rewards']} USDT total"
        )
        logger.info(msg)

        return stats

    async def get_global_bonus_stats(self) -> dict[str, Any]:
        """
        Get global bonus statistics for admin panel.

        Returns:
            Dict with total_granted, active_count, last_24h
        """
        now = datetime.now(UTC)
        day_ago = now - timedelta(hours=24)

        all_bonuses = await self.bonus_repo.get_all()
        active = [b for b in all_bonuses if b.is_active]

        total_granted = sum(b.amount for b in all_bonuses)
        last_24h = sum(
            b.amount
            for b in all_bonuses
            if b.created_at and b.created_at >= day_ago
        )

        return {
            "total_granted": total_granted,
            "active_count": len(active),
            "last_24h": last_24h,
            "total_count": len(all_bonuses),
        }

    async def get_recent_bonuses(self, limit: int = 15) -> list[BonusCredit]:
        """
        Get recent bonus credits with user and admin info.

        Args:
            limit: Max number of bonuses to return

        Returns:
            List of BonusCredit objects
        """
        return await self.bonus_repo.get_recent_with_relations(limit=limit)
