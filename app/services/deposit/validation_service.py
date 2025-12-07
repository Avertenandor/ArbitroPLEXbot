"""
Deposit validation service.

Validates deposit purchase eligibility based on:
1. Strict order (must buy levels sequentially: test -> level_1 -> level_2 -> ...)
2. No duplicate levels (cannot buy the same level twice)
3. Level must be active
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from app.repositories.referral_repository import ReferralRepository
from app.services.deposit.constants import (
    DEPOSIT_LEVELS,
    PARTNER_REQUIREMENTS,
    db_level_to_level_type,
    get_level_config,
    level_type_to_db_level,
)
from app.services.deposit.validation import (
    AmountValidator,
    LevelValidator,
    SequenceValidator,
)
from app.services.referral_service import ReferralService


class DepositValidationService:
    """Service for validating deposit purchase eligibility."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit validation service."""
        self.session = session
        self.deposit_repo = DepositRepository(session)
        self.referral_repo = ReferralRepository(session)
        self.referral_service = ReferralService(session)

        # Validators
        self.level_validator = LevelValidator(session)
        self.amount_validator = AmountValidator()
        self.sequence_validator = SequenceValidator(session)

    async def can_purchase_level(
        self, user_id: int, level: int
    ) -> tuple[bool, str | None]:
        """
        Check if user can purchase a specific deposit level.

        Legacy method for backward compatibility. Supports levels 1-5.

        Args:
            user_id: User ID
            level: Deposit level (1-5)

        Returns:
            Tuple of (can_purchase, error_message)
        """
        # Convert db_level to level_type
        level_type = db_level_to_level_type(level)
        if not level_type:
            return False, f"Неверный уровень депозита: {level}"

        # Use new validation logic
        return await self.can_purchase_level_by_type(user_id, level_type)

    async def can_purchase_level_by_type(
        self, user_id: int, level_type: str
    ) -> tuple[bool, str | None]:
        """
        Check if user can purchase a specific deposit level by level type.

        New method using level types (test, level_1, level_2, etc.).

        Args:
            user_id: User ID
            level_type: Level type (e.g., "test", "level_1")

        Returns:
            Tuple of (can_purchase, error_message)
        """
        # Check 0: Level must exist and be active (R17-2)
        can_purchase, error = await self.level_validator.can_purchase_level(
            user_id, level_type
        )
        if not can_purchase:
            return False, error

        # Check 1: User must not already have this level (no duplicates)
        has_level = await self.sequence_validator.has_active_level(
            user_id, level_type
        )
        if has_level:
            config = get_level_config(level_type)
            return (
                False,
                f"{config.display_name} уже приобретен. "
                f"Нельзя купить один уровень дважды.",
            )

        # Check 2: Strict order - must have all previous levels
        has_previous = await self.sequence_validator.has_all_previous_levels(
            user_id, level_type
        )
        if not has_previous:
            config = get_level_config(level_type)
            return (
                False,
                f"Для покупки {config.display_name} необходимо сначала "
                f"приобрести все предыдущие уровни.\n\n"
                f"Порядок покупки: test → уровень 1 → уровень 2 → "
                f"уровень 3 → уровень 4 → уровень 5",
            )

        # Check 3: Partner requirements (legacy, currently disabled)
        db_level = level_type_to_db_level(level_type)
        if db_level and db_level > 1:
            has_partners = await self._has_required_partners(user_id, db_level)
            if not has_partners:
                required = PARTNER_REQUIREMENTS.get(db_level, 0)
                if required > 0:
                    return (
                        False,
                        f"Для покупки уровня {db_level} необходимо минимум "
                        f"{required} активный партнер уровня L1 с "
                        f"активным депозитом.",
                    )

        return True, None

    async def _has_all_previous_levels(
        self, user_id: int, target_level: int
    ) -> bool:
        """
        Check if user has all previous deposit levels.

        Legacy method for backward compatibility.

        Args:
            user_id: User ID
            target_level: Target level to check (1-5)

        Returns:
            True if all previous levels exist and are confirmed
        """
        # Convert to level_type
        level_type = db_level_to_level_type(target_level)
        if not level_type:
            return False

        # Use new validator
        return await self.sequence_validator.has_all_previous_levels(
            user_id, level_type
        )

    async def _has_required_partners(
        self, user_id: int, level: int
    ) -> bool:
        """
        Check if user has required active partners.

        Legacy method. Currently partner requirements are disabled.

        Args:
            user_id: User ID
            level: Deposit level (1-5)

        Returns:
            True if user has required active partners
        """
        required = PARTNER_REQUIREMENTS.get(level, 0)
        if required == 0:
            return True  # No partners required

        # Get level 1 referrals (direct partners)
        l1_referrals = await self.referral_repo.get_by_referrer(
            referrer_id=user_id, level=1
        )

        if len(l1_referrals) < required:
            logger.debug(
                "Insufficient partners",
                extra={
                    "user_id": user_id,
                    "level": level,
                    "required": required,
                    "actual": len(l1_referrals),
                },
            )
            return False

        # Check if partners have active deposits
        active_partners = 0
        for referral in l1_referrals:
            partner_id = referral.referral_id
            # Check if partner has at least one confirmed deposit
            partner_deposits = await self.deposit_repo.find_by(
                user_id=partner_id,
                status=TransactionStatus.CONFIRMED.value,
            )
            if partner_deposits:
                active_partners += 1

        has_required = active_partners >= required

        logger.debug(
            "Partner check result",
            extra={
                "user_id": user_id,
                "level": level,
                "required": required,
                "active_partners": active_partners,
                "has_required": has_required,
            },
        )

        return has_required

    async def get_available_levels(self, user_id: int) -> dict:
        """
        Get available deposit levels for user with statuses.

        Includes test level (0) and levels 1-5.

        Args:
            user_id: User ID

        Returns:
            Dict with level statuses: available, unavailable, active
        """
        from app.services.deposit.constants import (
            DEPOSIT_LEVEL_CONFIGS,
            LEVEL_TYPE_TEST,
            LEVEL_TYPE_LEVEL_1,
            LEVEL_TYPE_LEVEL_2,
            LEVEL_TYPE_LEVEL_3,
            LEVEL_TYPE_LEVEL_4,
            LEVEL_TYPE_LEVEL_5,
        )

        # Get user's confirmed deposits
        deposits = await self.deposit_repo.find_by(
            user_id=user_id,
            status=TransactionStatus.CONFIRMED.value,
        )
        user_levels = set(d.level for d in deposits)

        levels_status = {}

        # All levels including test (0)
        level_types = [
            (0, LEVEL_TYPE_TEST),
            (1, LEVEL_TYPE_LEVEL_1),
            (2, LEVEL_TYPE_LEVEL_2),
            (3, LEVEL_TYPE_LEVEL_3),
            (4, LEVEL_TYPE_LEVEL_4),
            (5, LEVEL_TYPE_LEVEL_5),
        ]

        for db_level, level_type in level_types:
            config = DEPOSIT_LEVEL_CONFIGS[level_type]
            amount = config.amount
            can_purchase, error = await self.can_purchase_level_by_type(user_id, level_type)
            has_level = db_level in user_levels

            if has_level:
                status = "active"
                status_text = "Активен"
            elif can_purchase:
                status = "available"
                status_text = "Доступен к покупке"
            else:
                status = "unavailable"
                status_text = "Не доступен"

            levels_status[db_level] = {
                "level": db_level,
                "level_type": level_type,
                "amount": amount,
                "display_name": config.display_name,
                "status": status,
                "status_text": status_text,
                "error": error if not can_purchase else None,
            }

        return levels_status
