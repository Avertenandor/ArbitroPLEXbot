"""
Admin Service - Admin Manager.

This module handles admin CRUD operations:
- Creating admins
- Retrieving admins
- Deleting admins
"""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository
from app.repositories.admin_session_repository import (
    AdminSessionRepository,
)

from .crypto import generate_master_key, hash_master_key


class AdminManager:
    """Manages admin account operations."""

    def __init__(
        self,
        session: AsyncSession,
        admin_repo: AdminRepository,
        session_repo: AdminSessionRepository,
    ) -> None:
        """
        Initialize admin manager.

        Args:
            session: Database session
            admin_repo: Admin repository
            session_repo: Admin session repository
        """
        self.session = session
        self.admin_repo = admin_repo
        self.session_repo = session_repo

    async def create_admin(
        self,
        telegram_id: int,
        role: str,
        created_by: int,
        username: str | None = None,
    ) -> tuple[Admin | None, str | None, str | None]:
        """
        Create new admin with master key.

        Args:
            telegram_id: Telegram user ID
            role: admin or super_admin
            created_by: Creator admin ID
            username: Telegram username (optional)

        Returns:
            Tuple of (admin, master_key, error_message)
        """
        # Check if admin exists
        existing = await self.admin_repo.find_by(
            telegram_id=telegram_id
        )

        if existing:
            return (
                None,
                None,
                "Админ с таким Telegram ID уже существует",
            )

        # Generate and hash master key
        plain_master_key = generate_master_key()
        hashed_master_key = hash_master_key(plain_master_key)

        # Create admin
        admin = await self.admin_repo.create(
            telegram_id=telegram_id,
            username=username,
            role=role,
            master_key=hashed_master_key,
            created_by=created_by,
        )

        await self.session.commit()

        logger.info(
            "Admin created",
            extra={
                "admin_id": admin.id,
                "telegram_id": telegram_id,
                "role": role,
                "created_by": created_by,
            },
        )

        return admin, plain_master_key, None

    async def get_admin_by_telegram_id(
        self, telegram_id: int
    ) -> Admin | None:
        """
        Get admin by Telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            Admin or None
        """
        admins = await self.admin_repo.find_by(
            telegram_id=telegram_id
        )
        return admins[0] if admins else None

    async def get_admin_by_id(self, admin_id: int) -> Admin | None:
        """
        Get admin by ID.

        Args:
            admin_id: Admin ID

        Returns:
            Admin or None
        """
        return await self.admin_repo.get_by_id(admin_id)

    async def list_all_admins(self) -> list[Admin]:
        """
        List all admins.

        Returns:
            List of all admins
        """
        return await self.admin_repo.find_all()

    async def delete_admin(self, admin_id: int) -> bool:
        """
        Delete admin.

        Args:
            admin_id: Admin ID

        Returns:
            Success flag
        """
        admin = await self.admin_repo.get_by_id(admin_id)

        if not admin:
            return False

        # Deactivate all sessions
        await self.session_repo.deactivate_all_for_admin(admin_id)

        # Delete admin
        await self.admin_repo.delete(admin_id)
        await self.session.commit()

        logger.info(
            "Admin deleted", extra={"admin_id": admin_id}
        )

        return True
