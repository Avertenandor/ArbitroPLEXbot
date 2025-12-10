"""
Sequence validation for deposit levels.

Validates the sequential order of deposit levels:
- test -> level_1 -> level_2 -> level_3 -> level_4 -> level_5
- No duplicate levels allowed
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from app.services.deposit.constants import (
    LEVEL_TYPE_TEST,
    LEVEL_TYPES,
    get_level_config,
    get_previous_level_type,
    level_type_to_db_level,
)


class SequenceValidator:
    """Validator for deposit level sequence and order."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize sequence validator."""
        self.session = session
        self.deposit_repo = DepositRepository(session)

    async def has_previous_level(
        self, user_id: int, level_type: str
    ) -> bool:
        """
        Check if user has the immediately previous level.

        Args:
            user_id: User ID
            level_type: Target level type

        Returns:
            True if user has previous level
        """
        # Test level has no previous level
        if level_type == LEVEL_TYPE_TEST:
            return True

        previous_level_type = get_previous_level_type(level_type)
        if not previous_level_type:
            return True

        # Check if user has previous level
        return await self._has_level(user_id, previous_level_type)

    async def has_all_previous_levels(
        self, user_id: int, level_type: str
    ) -> bool:
        """
        Check if user has all previous levels in sequence.

        Args:
            user_id: User ID
            level_type: Target level type

        Returns:
            True if all previous levels exist and are confirmed
        """
        # Get target level index
        try:
            target_index = LEVEL_TYPES.index(level_type)
        except ValueError:
            logger.warning(
                "Invalid level type",
                extra={"level_type": level_type},
            )
            return False

        # Test level has no prerequisites
        if target_index == 0:
            return True

        # Get all user's confirmed deposits
        deposits = await self.deposit_repo.find_by(
            user_id=user_id,
            status=TransactionStatus.CONFIRMED.value,
        )

        # Get unique db_levels that user has
        user_db_levels = set(d.level for d in deposits)

        # Check if user has all previous levels
        for i in range(target_index):
            required_level_type = LEVEL_TYPES[i]
            required_db_level = level_type_to_db_level(required_level_type)

            if required_db_level is None:
                logger.warning(
                    "Cannot convert level type to db_level",
                    extra={"level_type": required_level_type},
                )
                return False

            if required_db_level not in user_db_levels:
                logger.debug(
                    "Missing previous level",
                    extra={
                        "user_id": user_id,
                        "target_level": level_type,
                        "missing_level": required_level_type,
                        "user_levels": list(user_db_levels),
                    },
                )
                return False

        return True

    async def has_active_level(
        self, user_id: int, level_type: str
    ) -> bool:
        """
        Check if user already has this level active.

        This prevents duplicate purchases of the same level.

        Args:
            user_id: User ID
            level_type: Level type to check

        Returns:
            True if user already has this level
        """
        return await self._has_level(user_id, level_type)

    async def can_open_next_level(
        self, user_id: int
    ) -> tuple[str | None, str | None]:
        """
        Determine which level the user can open next.

        Args:
            user_id: User ID

        Returns:
            Tuple of (next_level_type, error_message)
            - If user can open a level: (level_type, None)
            - If user cannot open any level: (None, error_message)
        """
        # Get all user's confirmed deposits
        deposits = await self.deposit_repo.find_by(
            user_id=user_id,
            status=TransactionStatus.CONFIRMED.value,
        )

        # Get unique db_levels that user has
        user_db_levels = set(d.level for d in deposits)

        # Find the next level in sequence
        for level_type in LEVEL_TYPES:
            db_level = level_type_to_db_level(level_type)
            if db_level is None:
                continue

            # If user doesn't have this level, check if they can open it
            if db_level not in user_db_levels:
                # Check if user has all previous levels
                can_open = await self.has_all_previous_levels(
                    user_id, level_type
                )
                if can_open:
                    return level_type, None
                else:
                    # User is missing a prerequisite level
                    previous_type = get_previous_level_type(level_type)
                    if previous_type:
                        config = get_level_config(previous_type)
                        return None, (
                            f"Для открытия следующего уровня необходимо "
                            f"сначала приобрести {config.display_name}"
                        )
                    return None, "Необходимо начать с тестового уровня"

        # User has all levels
        return None, "Вы уже открыли все доступные уровни"

    async def _has_level(self, user_id: int, level_type: str) -> bool:
        """
        Check if user has a specific level.

        Args:
            user_id: User ID
            level_type: Level type to check

        Returns:
            True if user has this level
        """
        db_level = level_type_to_db_level(level_type)
        if db_level is None:
            return False

        deposits = await self.deposit_repo.find_by(
            user_id=user_id,
            level=db_level,
            status=TransactionStatus.CONFIRMED.value,
        )

        return len(deposits) > 0
