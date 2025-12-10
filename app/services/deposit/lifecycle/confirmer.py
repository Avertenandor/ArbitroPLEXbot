"""
Deposit confirmer module.

Handles USDT confirmation, deposit activation, and PLEX requirement creation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.models.plex_payment import PlexPaymentRequirement
from app.repositories.deposit_repository import DepositRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository


class DepositConfirmer:
    """Handles deposit confirmation and activation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit confirmer."""
        self.session = session
        self.deposit_repo = DepositRepository(session)
        self.settings_repo = GlobalSettingsRepository(session)

    async def confirm_usdt_payment(
        self, deposit_id: int, tx_hash: str
    ) -> Deposit | None:
        """
        Confirm USDT payment for deposit.

        Updates deposit with transaction hash and marks as pending confirmation.

        Args:
            deposit_id: Deposit ID
            tx_hash: Transaction hash

        Returns:
            Updated deposit or None
        """
        try:
            deposit = await self.deposit_repo.update(
                deposit_id,
                tx_hash=tx_hash,
                status=TransactionStatus.PENDING.value,
            )

            if deposit:
                await self.session.commit()
                logger.info(
                    f"USDT payment confirmed for deposit {deposit_id}, "
                    f"tx_hash={tx_hash}"
                )

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to confirm USDT payment: {e}")
            raise

    async def activate_deposit(
        self, deposit_id: int, block_number: int
    ) -> Deposit | None:
        """
        Activate deposit after blockchain confirmation.

        Sets status to CONFIRMED, creates PLEX payment requirement,
        and processes referral rewards.

        Args:
            deposit_id: Deposit ID
            block_number: Confirmation block number

        Returns:
            Updated deposit or None
        """
        try:
            # R12-1: Calculate next_accrual_at based on settings
            global_settings = await self.settings_repo.get_settings()
            roi_settings = global_settings.roi_settings or {}
            accrual_period_hours = int(
                roi_settings.get("REWARD_ACCRUAL_PERIOD_HOURS", 6)
            )

            now = datetime.now(UTC)
            next_accrual = now + timedelta(hours=accrual_period_hours)

            # Update deposit status to CONFIRMED
            deposit = await self.deposit_repo.update(
                deposit_id,
                status=TransactionStatus.CONFIRMED.value,
                block_number=block_number,
                confirmed_at=now,
                next_accrual_at=next_accrual,
            )

            if not deposit:
                logger.error(f"Deposit {deposit_id} not found for activation")
                return None

            # Create PLEX payment requirement
            await self.create_plex_requirement(
                deposit_id=deposit.id,
                user_id=deposit.user_id,
                deposit_amount=deposit.amount,
                deposit_created_at=now,
            )

            await self.session.commit()
            logger.info(f"Deposit activated: id={deposit_id}")

            # Process referral rewards after activation
            await self._process_referral_rewards(
                user_id=deposit.user_id,
                deposit_amount=deposit.amount,
                deposit_id=deposit_id,
            )

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to activate deposit: {e}")
            raise

    async def create_plex_requirement(
        self,
        deposit_id: int,
        user_id: int,
        deposit_amount: Decimal,
        deposit_created_at: datetime,
    ) -> PlexPaymentRequirement | None:
        """
        Create PLEX payment requirement for deposit.

        Sets plex_daily_required = deposit_amount * 10.

        Args:
            deposit_id: Deposit ID
            user_id: User ID
            deposit_amount: Deposit amount in USDT
            deposit_created_at: When deposit was created

        Returns:
            Created PlexPaymentRequirement or None
        """
        try:
            from app.services.plex_payment_service import PlexPaymentService

            plex_service = PlexPaymentService(self.session)
            requirement = await plex_service.create_payment_requirement(
                user_id=user_id,
                deposit_id=deposit_id,
                deposit_amount=deposit_amount,
                deposit_created_at=deposit_created_at,
            )

            logger.info(
                f"Created PLEX payment requirement for deposit {deposit_id}: "
                f"{requirement.daily_plex_required} PLEX/day"
            )

            return requirement

        except Exception as e:
            logger.error(
                f"Failed to create PLEX payment requirement for deposit "
                f"{deposit_id}: {e}"
            )
            # Don't fail deposit confirmation if PLEX req creation fails
            return None

    async def _process_referral_rewards(
        self, user_id: int, deposit_amount: Decimal, deposit_id: int
    ) -> None:
        """
        Process referral rewards after deposit confirmation.

        Args:
            user_id: User ID
            deposit_amount: Deposit amount
            deposit_id: Deposit ID
        """
        try:
            from app.services.referral_service import ReferralService

            referral_service = ReferralService(self.session)
            success, total_rewards, error = (
                await referral_service.process_referral_rewards(
                    user_id=user_id, deposit_amount=deposit_amount
                )
            )

            if success:
                logger.info(
                    f"Referral rewards processed for deposit {deposit_id}: "
                    f"total={total_rewards} USDT"
                )
            else:
                logger.warning(
                    f"Failed to process referral rewards for deposit {deposit_id}: "
                    f"{error}"
                )

        except Exception as e:
            logger.error(
                f"Error processing referral rewards for deposit {deposit_id}: {e}"
            )
            # Don't fail deposit activation if referral processing fails
