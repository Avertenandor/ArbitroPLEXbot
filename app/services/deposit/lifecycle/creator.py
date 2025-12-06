"""
Deposit creator module.

Handles deposit creation with validation and corridor checks.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.repositories.deposit_repository import DepositRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository


class DepositCreator:
    """Handles deposit creation with full validation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit creator."""
        self.session = session
        self.deposit_repo = DepositRepository(session)
        self.version_repo = DepositLevelVersionRepository(session)
        self.settings_repo = GlobalSettingsRepository(session)

    async def validate_and_create(
        self,
        user_id: int,
        level_type: int,
        amount: Decimal,
        tx_hash: str | None = None,
        redis_client: Any | None = None,
    ) -> Deposit:
        """
        Full validation and deposit creation.

        Args:
            user_id: User ID
            level_type: Deposit level (1-5)
            amount: Deposit amount
            tx_hash: Optional blockchain transaction hash
            redis_client: Optional Redis client for distributed lock

        Returns:
            Created deposit

        Raises:
            ValueError: If validation fails
        """
        # R15-5: Use distributed lock to prevent race conditions
        from app.utils.distributed_lock import get_distributed_lock

        lock = get_distributed_lock(
            redis_client=redis_client, session=self.session
        )
        lock_key = f"user:{user_id}:create_deposit"

        async with lock.lock(
            lock_key, timeout=30, blocking=True, blocking_timeout=5.0
        ) as acquired:
            if not acquired:
                logger.warning(
                    f"Could not acquire lock for creating deposit for user {user_id}"
                )
                raise ValueError(
                    "Операция уже выполняется. Пожалуйста, подождите."
                )

            # R17-3: Check emergency stop
            global_settings = await self.settings_repo.get_settings()
            if (
                settings.emergency_stop_deposits
                or getattr(global_settings, "emergency_stop_deposits", False)
            ):
                logger.warning(
                    "Deposit blocked by emergency stop for user %s, level %s",
                    user_id,
                    level_type,
                )
                raise ValueError(
                    "⚠️ Временная приостановка депозитов из-за технических работ.\n\n"
                    "Депозиты будут доступны после восстановления.\n\n"
                    "Следите за обновлениями в нашем канале."
                )

            # Validate level type
            if not 1 <= level_type <= 5:
                raise ValueError("Level must be 1-5")

            # Validate amount is positive
            if amount <= 0:
                raise ValueError("Amount must be positive")

            # R18-1: Dust attack protection
            min_deposit = Decimal(str(settings.minimum_deposit_amount))
            if amount < min_deposit:
                logger.warning(
                    f"Dust attack attempt blocked: user {user_id}, "
                    f"amount {amount} < minimum {min_deposit}"
                )
                raise ValueError(
                    f"Минимальная сумма депозита: {min_deposit} USDT. "
                    f"Попытка депозита {amount} USDT отклонена."
                )

            # Get level version (for corridor validation)
            level_version = await self.version_repo.get_current_version(level_type)
            if not level_version:
                raise ValueError(
                    f"Level {level_type} is not available. "
                    "This level has been temporarily disabled."
                )

            # R17-2: Check if level is active
            if not level_version.is_active:
                raise ValueError(
                    f"Level {level_type} is temporarily unavailable. "
                    "Please try again later or contact support."
                )

            # Validate amount is within corridor (min <= amount <= max)
            # For now, we use level_version.amount as both min and max
            # Future enhancement: add min_amount and max_amount to DepositLevelVersion
            if amount < level_version.amount:
                raise ValueError(
                    f"Amount {amount} is less than required "
                    f"{level_version.amount} for level {level_type}"
                )

            # Create deposit
            return await self.create_deposit(
                user_id=user_id,
                level_type=level_type,
                amount=amount,
                tx_hash=tx_hash,
                level_version=level_version,
            )

    async def create_deposit(
        self,
        user_id: int,
        level_type: int,
        amount: Decimal,
        tx_hash: str | None = None,
        level_version: Any = None,
    ) -> Deposit:
        """
        Create deposit with corridor validation.

        Args:
            user_id: User ID
            level_type: Deposit level (1-5)
            amount: Deposit amount
            tx_hash: Optional blockchain transaction hash
            level_version: Pre-loaded level version

        Returns:
            Created deposit

        Raises:
            ValueError: If creation fails
        """
        try:
            # Determine initial status based on blockchain maintenance mode
            # R11-2: If blockchain is down, create with PENDING_NETWORK_RECOVERY
            deposit_status = TransactionStatus.PENDING.value
            if settings.blockchain_maintenance_mode:
                deposit_status = TransactionStatus.PENDING_NETWORK_RECOVERY.value
                logger.info(
                    f"R11-2: Creating deposit with PENDING_NETWORK_RECOVERY status "
                    f"for user {user_id}, level {level_type}"
                )

            # R17-1: Calculate ROI cap from version
            roi_cap_percent = Decimal(str(level_version.roi_cap_percent))
            roi_cap = amount * (roi_cap_percent / 100)

            # Create deposit record
            deposit = await self.deposit_repo.create(
                user_id=user_id,
                level=level_type,
                amount=amount,
                tx_hash=tx_hash,
                deposit_version_id=level_version.id,
                roi_cap_amount=roi_cap,
                status=deposit_status,
            )

            await self.session.commit()
            logger.info(
                f"Deposit created: id={deposit.id}, user={user_id}, "
                f"level={level_type}, amount={amount}"
            )

            return deposit

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create deposit: {e}")
            raise
