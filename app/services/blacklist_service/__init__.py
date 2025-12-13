"""
Blacklist Service - Main Module.

This module manages user blacklist for pre-registration and ban prevention.

Module Structure:
- core.py: Basic blacklist operations (is_blacklisted, add, remove, get)
- user_termination.py: User account termination logic (R15-2)
- user_blocking.py: User blocking with active operations (R15-1, R15-4)

Public Interface:
- BlacklistService: Main service class (backward compatible)

Features:
- Add/remove from blacklist
- Check if user is blacklisted
- Reason tracking
- Admin logging
- User termination
- User blocking with operation handling
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

# Re-export for backward compatibility
from app.models.blacklist import Blacklist, BlacklistActionType

from .core import BlacklistCore
from .user_blocking import UserBlockingManager
from .user_termination import UserTerminationManager


class BlacklistService:
    """
    Service for managing blacklist.

    This is the main service class that provides backward compatibility
    with the original monolithic implementation.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize blacklist service.

        Args:
            session: Database session
        """
        self.session = session

        # Initialize all components
        self.core = BlacklistCore(session)
        self.termination_manager = UserTerminationManager(self.core)
        self.blocking_manager = UserBlockingManager(self.core)

        # Expose repository for backward compatibility
        self.repository = self.core.repository

    # Delegate methods to appropriate components for backward compatibility

    async def is_blacklisted(
        self,
        telegram_id: int | None = None,
        wallet_address: str | None = None,
    ) -> bool:
        """Check if user is blacklisted."""
        return await self.core.is_blacklisted(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
        )

    async def add_to_blacklist(
        self,
        telegram_id: int | None = None,
        wallet_address: str | None = None,
        reason: str = "Manual blacklist",
        added_by_admin_id: int | None = None,
        action_type: str = "registration_denied",
    ) -> Blacklist:
        """Add user to blacklist."""
        return await self.core.add_to_blacklist(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
            reason=reason,
            added_by_admin_id=added_by_admin_id,
            action_type=action_type,
        )

    async def remove_from_blacklist(
        self,
        telegram_id: int | None = None,
        wallet_address: str | None = None,
    ) -> bool:
        """Remove user from blacklist."""
        return await self.core.remove_from_blacklist(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
        )

    async def get_blacklist_entry(
        self,
        telegram_id: int | None = None,
        wallet_address: str | None = None,
    ) -> Blacklist | None:
        """Get blacklist entry."""
        return await self.core.get_blacklist_entry(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
        )

    async def get_all_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Blacklist]:
        """Get all active blacklist entries."""
        return await self.core.get_all_active(
            limit=limit,
            offset=offset,
        )

    async def count_active(self) -> int:
        """Count active blacklist entries."""
        return await self.core.count_active()

    async def terminate_user(
        self,
        user_id: int,
        reason: str,
        admin_id: int | None = None,
        redis_client: Any | None = None,
    ) -> dict:
        """Terminate user account (R15-2)."""
        return await self.termination_manager.terminate_user(
            user_id=user_id,
            reason=reason,
            admin_id=admin_id,
            redis_client=redis_client,
        )

    async def block_user_with_active_operations(
        self,
        user_id: int,
        reason: str,
        admin_id: int | None = None,
        redis_client: Any | None = None,
    ) -> dict:
        """Block user and handle active operations (R15-1, R15-4)."""
        return await self.blocking_manager.block_user_with_active_operations(
            user_id=user_id,
            reason=reason,
            admin_id=admin_id,
            redis_client=redis_client,
        )


__all__ = ['BlacklistService', 'BlacklistActionType']
