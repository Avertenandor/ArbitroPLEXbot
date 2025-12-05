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

from sqlalchemy.ext.asyncio import AsyncSession

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

    async def is_blacklisted(self, *args, **kwargs):
        """Check if user is blacklisted."""
        return await self.core.is_blacklisted(*args, **kwargs)

    async def add_to_blacklist(self, *args, **kwargs):
        """Add user to blacklist."""
        return await self.core.add_to_blacklist(*args, **kwargs)

    async def remove_from_blacklist(self, *args, **kwargs):
        """Remove user from blacklist."""
        return await self.core.remove_from_blacklist(*args, **kwargs)

    async def get_blacklist_entry(self, *args, **kwargs):
        """Get blacklist entry."""
        return await self.core.get_blacklist_entry(*args, **kwargs)

    async def get_all_active(self, *args, **kwargs):
        """Get all active blacklist entries."""
        return await self.core.get_all_active(*args, **kwargs)

    async def count_active(self):
        """Count active blacklist entries."""
        return await self.core.count_active()

    async def terminate_user(self, *args, **kwargs):
        """Terminate user account (R15-2)."""
        return await self.termination_manager.terminate_user(*args, **kwargs)

    async def block_user_with_active_operations(self, *args, **kwargs):
        """Block user and handle active operations (R15-1, R15-4)."""
        return await self.blocking_manager.block_user_with_active_operations(
            *args, **kwargs
        )


# Re-export for backward compatibility
__all__ = ['BlacklistService']
