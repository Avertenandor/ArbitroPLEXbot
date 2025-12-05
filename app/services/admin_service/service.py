"""
Admin Service - Main Service Class.

This module provides the main AdminService class that orchestrates
all admin-related operations by delegating to specialized managers.
"""

from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.repositories.admin_repository import AdminRepository
from app.repositories.admin_session_repository import (
    AdminSessionRepository,
)

from .admin_manager import AdminManager
from .crypto import (
    generate_master_key,
    generate_session_token,
    hash_master_key,
    verify_master_key,
)
from .rate_limiter import RateLimiter
from .session_manager import SessionManager


class AdminService:
    """
    Admin service for authentication and session management.

    This class orchestrates all admin-related operations by delegating
    to specialized managers:
    - AdminManager: Admin CRUD operations
    - SessionManager: Session lifecycle management
    - RateLimiter: Rate limiting and security
    """

    def __init__(
        self,
        session: AsyncSession,
        redis_client: Any | None = None,
    ) -> None:
        """
        Initialize admin service.

        Args:
            session: Database session
            redis_client: Optional Redis client for rate limiting
        """
        self.session = session
        self.redis_client = redis_client

        # Initialize repositories
        self.admin_repo = AdminRepository(session)
        self.session_repo = AdminSessionRepository(session)

        # Initialize managers
        self.admin_manager = AdminManager(
            session, self.admin_repo, self.session_repo
        )
        self.session_manager = SessionManager(
            session, self.admin_repo, self.session_repo
        )
        self.rate_limiter = RateLimiter(
            session, self.admin_repo, redis_client
        )

    # =========================================================================
    # Static utility methods (for backward compatibility)
    # =========================================================================

    @staticmethod
    def generate_master_key() -> str:
        """Generate random master key."""
        return generate_master_key()

    @staticmethod
    def hash_master_key(master_key: str) -> str:
        """Hash master key using bcrypt."""
        return hash_master_key(master_key)

    @staticmethod
    def verify_master_key(plain_key: str, hashed_key: str) -> bool:
        """Verify master key against hash."""
        return verify_master_key(plain_key, hashed_key)

    @staticmethod
    def generate_session_token() -> str:
        """Generate random session token."""
        return generate_session_token()

    # =========================================================================
    # Admin management methods
    # =========================================================================

    async def create_admin(
        self,
        telegram_id: int,
        role: str,
        created_by: int,
        username: str | None = None,
    ) -> tuple[Admin | None, str | None, str | None]:
        """Create new admin with master key."""
        return await self.admin_manager.create_admin(
            telegram_id, role, created_by, username
        )

    async def get_admin_by_telegram_id(
        self, telegram_id: int
    ) -> Admin | None:
        """Get admin by Telegram ID."""
        return await self.admin_manager.get_admin_by_telegram_id(
            telegram_id
        )

    async def get_admin_by_id(self, admin_id: int) -> Admin | None:
        """Get admin by ID."""
        return await self.admin_manager.get_admin_by_id(admin_id)

    async def list_all_admins(self) -> list[Admin]:
        """List all admins."""
        return await self.admin_manager.list_all_admins()

    async def get_all_admins(self) -> list[Admin]:
        """Get all admins (alias)."""
        return await self.list_all_admins()

    async def delete_admin(self, admin_id: int) -> bool:
        """Delete admin."""
        return await self.admin_manager.delete_admin(admin_id)

    # =========================================================================
    # Authentication and session methods
    # =========================================================================

    async def login(
        self,
        telegram_id: int,
        master_key: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[AdminSession | None, Admin | None, str | None]:
        """
        Authenticate admin and create session.

        Args:
            telegram_id: Telegram user ID
            master_key: Plain master key
            ip_address: IP address (optional)
            user_agent: User agent string (optional)

        Returns:
            Tuple of (session, admin, error_message)
        """
        # Find admin
        admins = await self.admin_repo.find_by(
            telegram_id=telegram_id
        )

        if not admins:
            logger.warning(
                "Admin not found", extra={"telegram_id": telegram_id}
            )
            return None, None, "Администратор не найден"

        admin = admins[0]

        if not admin.master_key:
            return None, None, "Мастер-ключ не установлен"

        # Verify master key
        if not verify_master_key(master_key, admin.master_key):
            # Track failed login attempt
            await self.rate_limiter.track_failed_login(telegram_id)

            logger.warning(
                "Invalid master key attempt",
                extra={
                    "admin_id": admin.id,
                    "telegram_id": telegram_id,
                },
            )
            return None, None, "Неверный мастер-ключ"

        # Clear failed login attempts on successful login
        await self.rate_limiter.clear_failed_login_attempts(telegram_id)

        # Create session
        session = await self.session_manager.create_session(
            admin.id, ip_address, user_agent
        )

        logger.info(
            "Admin logged in",
            extra={
                "admin_id": admin.id,
                "telegram_id": telegram_id,
                "session_id": session.id,
            },
        )

        return session, admin, None

    async def logout(self, session_token: str) -> bool:
        """Logout admin (deactivate session)."""
        return await self.session_manager.logout(session_token)

    async def validate_session(
        self, session_token: str
    ) -> tuple[Admin | None, AdminSession | None, str | None]:
        """Validate session and update activity."""
        return await self.session_manager.validate_session(
            session_token
        )

    # =========================================================================
    # Private methods (for backward compatibility)
    # =========================================================================

    async def _track_failed_login(self, telegram_id: int) -> None:
        """Track failed login attempt (deprecated, use rate_limiter)."""
        await self.rate_limiter.track_failed_login(telegram_id)

    async def _clear_failed_login_attempts(self, telegram_id: int) -> None:
        """Clear failed login attempts (deprecated, use rate_limiter)."""
        await self.rate_limiter.clear_failed_login_attempts(telegram_id)

    async def _block_telegram_id_for_failed_logins(
        self, telegram_id: int
    ) -> None:
        """Block Telegram ID (deprecated, use rate_limiter)."""
        await self.rate_limiter._block_telegram_id(telegram_id)

    async def _notify_super_admins_of_block(
        self, telegram_id: int
    ) -> None:
        """Notify super_admins (deprecated, use rate_limiter)."""
        await self.rate_limiter._notify_super_admins_of_block(
            telegram_id
        )
