"""
Admin Service - Session Manager.

This module handles admin session creation, validation, and management.
"""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_session import AdminSession
from app.repositories.admin_repository import AdminRepository
from app.repositories.admin_session_repository import (
    AdminSessionRepository,
)

from .constants import SESSION_DURATION_HOURS
from .crypto import generate_session_token


class SessionManager:
    """Manages admin session lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        admin_repo: AdminRepository,
        session_repo: AdminSessionRepository,
    ) -> None:
        """
        Initialize session manager.

        Args:
            session: Database session
            admin_repo: Admin repository
            session_repo: Admin session repository
        """
        self.session = session
        self.admin_repo = admin_repo
        self.session_repo = session_repo

    async def create_session(
        self,
        admin_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminSession:
        """
        Create new admin session.

        Args:
            admin_id: Admin ID
            ip_address: IP address (optional)
            user_agent: User agent string (optional)

        Returns:
            Created session
        """
        # Deactivate all existing sessions
        await self.session_repo.deactivate_all_for_admin(admin_id)

        # Create new session
        session_token = generate_session_token()
        expires_at = datetime.now(UTC) + timedelta(
            hours=SESSION_DURATION_HOURS
        )

        session = await self.session_repo.create(
            admin_id=admin_id,
            session_token=session_token,
            is_active=True,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        await self.session.commit()

        logger.info(
            "Admin session created",
            extra={
                "admin_id": admin_id,
                "session_id": session.id,
            },
        )

        return session

    async def validate_session(
        self, session_token: str
    ) -> tuple[Admin | None, AdminSession | None, str | None]:
        """
        Validate session and update activity.

        Args:
            session_token: Session token

        Returns:
            Tuple of (admin, session, error_message)
        """
        sessions = await self.session_repo.find_by(
            session_token=session_token, is_active=True
        )

        if not sessions:
            return None, None, "Сессия не найдена"

        session = sessions[0]

        # Check if expired
        if session.is_expired:
            await self.session_repo.update(
                session.id, is_active=False
            )
            await self.session.commit()

            logger.info(
                "Session expired",
                extra={"session_id": session.id},
            )
            return None, None, "Сессия истекла. Войдите заново"

        # Check if inactive (no activity for 15 minutes)
        if session.is_inactive:
            await self.session_repo.update(
                session.id, is_active=False
            )
            await self.session.commit()

            logger.info(
                "Session inactive (15 minutes)",
                extra={"session_id": session.id},
            )
            return (
                None,
                None,
                "Сессия неактивна (бездействие более 15 минут). "
                "Войдите заново",
            )

        # Update activity
        await self.session_repo.update(
            session.id, last_activity=datetime.now(UTC)
        )

        # Load admin
        admin = await self.admin_repo.get_by_id(session.admin_id)

        if not admin:
            return None, None, "Admin not found"

        # R10-3: Check if admin is blocked
        if admin.is_blocked:
            logger.warning(
                f"R10-3: Blocked admin {admin.id} attempted to use session "
                f"{session_token[:8]}..."
            )
            # Invalidate session
            await self.session_repo.delete(session.id)
            await self.session.commit()
            return None, None, "Admin account is blocked"

        await self.session.commit()

        return admin, session, None

    async def logout(self, session_token: str) -> bool:
        """
        Logout admin (deactivate session).

        Args:
            session_token: Session token

        Returns:
            Success flag
        """
        sessions = await self.session_repo.find_by(
            session_token=session_token, is_active=True
        )

        if not sessions:
            return False

        session = sessions[0]
        await self.session_repo.update(
            session.id, is_active=False
        )

        await self.session.commit()

        logger.info(
            "Admin logged out",
            extra={"session_token": session_token},
        )

        return True

    async def deactivate_all_for_admin(self, admin_id: int) -> None:
        """
        Deactivate all sessions for an admin.

        Args:
            admin_id: Admin ID
        """
        await self.session_repo.deactivate_all_for_admin(admin_id)
        await self.session.commit()
