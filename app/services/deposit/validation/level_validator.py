"""
Level validation for deposits.

Validates deposit level eligibility:
- Level must be active
- Level must exist in configuration
- User must meet prerequisites
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.services.deposit.constants import (
    DEPOSIT_LEVEL_CONFIGS,
    DepositLevelConfig,
    get_level_config,
    level_type_to_db_level,
)


class LevelValidator:
    """Validator for deposit level configuration and status."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize level validator."""
        self.session = session
        self.version_repo = DepositLevelVersionRepository(session)

    async def can_purchase_level(
        self, user_id: int, level_type: str
    ) -> tuple[bool, str | None]:
        """
        Check if user can purchase a specific deposit level.

        This validates only the level configuration, not the sequence.
        Use SequenceValidator for sequence checks.

        Args:
            user_id: User ID
            level_type: Level type (e.g., "test", "level_1")

        Returns:
            Tuple of (can_purchase, error_message)
        """
        # Validate level exists
        config = get_level_config(level_type)
        if not config:
            return False, f"Неверный уровень депозита: {level_type}"

        # Check if level is active (R17-2)
        is_active = await self.is_level_active(level_type)
        if not is_active:
            return (
                False,
                f"{config.display_name} временно недоступен для покупки.",
            )

        return True, None

    async def is_level_active(self, level_type: str) -> bool:
        """
        Check if a deposit level is currently active.

        Args:
            level_type: Level type (e.g., "test", "level_1")

        Returns:
            True if level is active
        """
        db_level = level_type_to_db_level(level_type)
        if db_level is None:
            logger.warning(
                "Cannot convert level type to db_level",
                extra={"level_type": level_type},
            )
            return False

        # For db_level 0 (test), there's no version in DB, always active
        if db_level == 0:
            return True

        # Check version repository for levels 1-5
        level_version = await self.version_repo.get_current_version(db_level)

        # If no version exists, consider it inactive
        if not level_version:
            logger.warning(
                "No version found for level",
                extra={"level_type": level_type, "db_level": db_level},
            )
            return False

        return level_version.is_active

    def get_level_config_sync(
        self, level_type: str
    ) -> DepositLevelConfig | None:
        """
        Get level configuration synchronously.

        Args:
            level_type: Level type (e.g., "test", "level_1")

        Returns:
            DepositLevelConfig or None if not found
        """
        return get_level_config(level_type)

    def get_all_level_configs(self) -> dict[str, DepositLevelConfig]:
        """
        Get all level configurations.

        Returns:
            Dictionary mapping level_type to DepositLevelConfig
        """
        return DEPOSIT_LEVEL_CONFIGS.copy()
