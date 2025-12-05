"""
Individual reward calculation module.

Handles the calculation of rewards for individual deposits based on their
next_accrual_at timestamp and corridor settings.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.repositories.deposit_repository import DepositRepository
from app.repositories.deposit_reward_repository import DepositRewardRepository
from app.services.reward.reward_calculator import RewardCalculator


class IndividualRewardProcessor:
    """Processes individual deposit rewards."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize individual reward processor.

        Args:
            session: Database session
        """
        self.session = session
        self.deposit_repo = DepositRepository(session)
        self.reward_repo = DepositRewardRepository(session)
        self.calculator = RewardCalculator(session)

    async def calculate_individual_rewards(
        self,
        balance_creditor: "RewardBalanceHandler",
    ) -> None:
        """
        Calculate rewards for deposits that are due for accrual.

        This method processes individual deposits based on their
        next_accrual_at timestamp and corridor settings.

        Args:
            balance_creditor: Balance handler for crediting rewards
        """
        from app.services.referral_service import ReferralService
        from app.services.roi_corridor_service import RoiCorridorService

        corridor_service = RoiCorridorService(self.session)
        referral_service = ReferralService(self.session)

        # Get deposits due for accrual with pessimistic lock
        # This prevents race conditions with concurrent reward calculations
        now = datetime.now(UTC)
        stmt = select(Deposit).where(
            Deposit.status == "confirmed",
            Deposit.is_roi_completed == False,  # noqa: E712
            Deposit.next_accrual_at <= now,
        ).with_for_update()  # Lock deposits to prevent concurrent modifications
        result = await self.session.execute(stmt)
        deposits = list(result.scalars().all())

        logger.info(
            "Processing individual rewards",
            extra={"deposits_count": len(deposits)},
        )

        for deposit in deposits:
            try:
                # Get corridor config
                config = await corridor_service.get_corridor_config(
                    deposit.level
                )

                # Determine rate
                if config["mode"] == "custom":
                    rate = corridor_service.generate_rate_from_corridor(
                        config["roi_min"], config["roi_max"]
                    )
                else:  # equal
                    rate = config["roi_fixed"]

                # Calculate reward using RewardCalculator
                reward_amount = self.calculator.calculate_reward_amount(
                    deposit.amount, rate, days=1
                )

                # Check ROI cap using RewardCalculator
                reward_amount = self.calculator.cap_reward_to_remaining_roi(
                    reward_amount, deposit
                )

                if reward_amount <= 0:
                    logger.debug(
                        "Skipping deposit with zero reward",
                        extra={"deposit_id": deposit.id},
                    )
                    continue

                # Create reward
                await self.reward_repo.create(
                    user_id=deposit.user_id,
                    deposit_id=deposit.id,
                    reward_session_id=None,  # Individual accrual
                    deposit_level=deposit.level,
                    deposit_amount=deposit.amount,
                    reward_rate=rate,
                    reward_amount=reward_amount,
                    paid=False,
                    calculated_at=datetime.now(UTC),
                )

                # Update deposit
                new_roi_paid = (
                    deposit.roi_paid_amount or Decimal("0")
                ) + reward_amount
                period_hours = await corridor_service.get_accrual_period_hours()
                next_accrual = now + timedelta(hours=period_hours)

                await self.deposit_repo.update(
                    deposit.id,
                    roi_paid_amount=new_roi_paid,
                    next_accrual_at=next_accrual,
                )

                # R19: Process referral rewards from ROI
                await referral_service.process_roi_referral_rewards(
                    deposit.user_id, reward_amount
                )

                # Check if ROI completed using RewardCalculator
                if self.calculator.is_roi_cap_reached(deposit, total_earned=new_roi_paid):
                    await self.deposit_repo.update(
                        deposit.id,
                        is_roi_completed=True,
                        completed_at=now,
                    )

                    # Send notification
                    await self._send_roi_completed_notification(deposit)

                    logger.info(
                        "Deposit ROI completed",
                        extra={
                            "deposit_id": deposit.id,
                            "user_id": deposit.user_id,
                            "total_paid": str(new_roi_paid),
                        },
                    )
                else:
                    logger.debug(
                        "Reward calculated",
                        extra={
                            "deposit_id": deposit.id,
                            "rate": str(rate),
                            "amount": str(reward_amount),
                            "next_accrual": next_accrual.isoformat(),
                        },
                    )

                # Credit ROI to user's internal balance and create accounting transaction
                await balance_creditor.credit_roi_to_balance(
                    user_id=deposit.user_id,
                    reward_amount=reward_amount,
                    deposit_id=deposit.id,
                )

            except Exception as e:
                logger.error(
                    f"Error processing deposit {deposit.id}: {e}",
                    extra={"deposit_id": deposit.id, "error": str(e)},
                )
                continue

        await self.session.commit()

        logger.info(
            "Individual rewards processing completed",
            extra={"processed": len(deposits)},
        )

    async def _send_roi_completed_notification(
        self, deposit: Deposit
    ) -> None:
        """
        Send notification when ROI reaches 500%.

        Args:
            deposit: Completed deposit
        """
        try:
            from bot.utils.notification import send_telegram_message

            text = (
                "🎉 Обязательства системы выполнены в объеме 500%!\n\n"
                f"💰 Вы заработали: {deposit.roi_paid_amount:.2f} USDT\n"
                "📈 Ваш ROI равен 500%\n\n"
                "⚠️ Ваш текущий депозит деактивирован системой.\n\n"
                "✅ Вы можете открыть новый депозит и продолжить "
                "зарабатывать с системой!"
            )

            await send_telegram_message(deposit.user.telegram_id, text)

            logger.info(
                "ROI completion notification sent",
                extra={
                    "deposit_id": deposit.id,
                    "user_id": deposit.user_id,
                    "telegram_id": deposit.user.telegram_id,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to send ROI notification: {e}",
                extra={"deposit_id": deposit.id, "error": str(e)},
            )
