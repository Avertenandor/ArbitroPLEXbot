"""
Deposit level config repository.

Data access layer for DepositLevelConfig model.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit_level_config import DepositLevelConfig
from app.repositories.base import BaseRepository


class DepositLevelConfigRepository(BaseRepository[DepositLevelConfig]):
    """Deposit level config repository with specific queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit level config repository."""
        super().__init__(DepositLevelConfig, session)

    async def get_by_level_type(
        self, level_type: str
    ) -> DepositLevelConfig | None:
        """
        Get config by level type.

        Args:
            level_type: Level type (test, level_1, level_2, etc.)

        Returns:
            Config or None if not found
        """
        return await self.get_by(level_type=level_type)

    async def get_active_levels(self) -> list[DepositLevelConfig]:
        """
        Get all active level configurations.

        Returns:
            List of active configs
        """
        return await self.find_by(is_active=True)

    async def get_ordered_levels(
        self, active_only: bool = True
    ) -> list[DepositLevelConfig]:
        """
        Get level configurations ordered by order field.

        Args:
            active_only: If True, return only active levels

        Returns:
            List of configs ordered by order field
        """
        stmt = select(DepositLevelConfig).order_by(
            DepositLevelConfig.order
        )

        if active_only:
            stmt = stmt.where(DepositLevelConfig.is_active == True)  # noqa: E712

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_level_for_amount(
        self, amount: Decimal
    ) -> DepositLevelConfig | None:
        """
        Find appropriate level config for given amount.

        Args:
            amount: Deposit amount

        Returns:
            Matching level config or None if no match found
        """
        stmt = (
            select(DepositLevelConfig)
            .where(DepositLevelConfig.is_active == True)  # noqa: E712
            .where(DepositLevelConfig.min_amount <= amount)
            .where(DepositLevelConfig.max_amount >= amount)
            .order_by(DepositLevelConfig.order)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_ordered(self) -> list[DepositLevelConfig]:
        """
        Get all level configurations (including inactive) ordered by order field.

        Returns:
            List of all configs ordered by order field
        """
        stmt = select(DepositLevelConfig).order_by(
            DepositLevelConfig.order
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def activate_level(self, level_type: str) -> DepositLevelConfig | None:
        """
        Activate a level configuration.

        Args:
            level_type: Level type to activate

        Returns:
            Updated config or None if not found
        """
        config = await self.get_by_level_type(level_type)
        if config:
            config.is_active = True
            await self.session.flush()
            await self.session.refresh(config)
        return config

    async def deactivate_level(self, level_type: str) -> DepositLevelConfig | None:
        """
        Deactivate a level configuration.

        Args:
            level_type: Level type to deactivate

        Returns:
            Updated config or None if not found
        """
        config = await self.get_by_level_type(level_type)
        if config:
            config.is_active = False
            await self.session.flush()
            await self.session.refresh(config)
        return config

    async def update_corridor(
        self,
        level_type: str,
        min_amount: Decimal,
        max_amount: Decimal,
    ) -> DepositLevelConfig | None:
        """
        Update amount corridor for a level.

        Args:
            level_type: Level type to update
            min_amount: New minimum amount
            max_amount: New maximum amount

        Returns:
            Updated config or None if not found
        """
        config = await self.get_by_level_type(level_type)
        if config:
            config.min_amount = min_amount
            config.max_amount = max_amount
            await self.session.flush()
            await self.session.refresh(config)
        return config

    async def update_roi_settings(
        self,
        level_type: str,
        roi_percent: Decimal | None = None,
        roi_cap_percent: int | None = None,
    ) -> DepositLevelConfig | None:
        """
        Update ROI settings for a level.

        Args:
            level_type: Level type to update
            roi_percent: New ROI percent (optional)
            roi_cap_percent: New ROI cap percent (optional)

        Returns:
            Updated config or None if not found
        """
        config = await self.get_by_level_type(level_type)
        if config:
            if roi_percent is not None:
                config.roi_percent = roi_percent
            if roi_cap_percent is not None:
                config.roi_cap_percent = roi_cap_percent
            await self.session.flush()
            await self.session.refresh(config)
        return config

    async def update_plex_rate(
        self, level_type: str, plex_per_dollar: int
    ) -> DepositLevelConfig | None:
        """
        Update PLEX rate for a level.

        Args:
            level_type: Level type to update
            plex_per_dollar: New PLEX per dollar rate

        Returns:
            Updated config or None if not found
        """
        config = await self.get_by_level_type(level_type)
        if config:
            config.plex_per_dollar = plex_per_dollar
            await self.session.flush()
            await self.session.refresh(config)
        return config
