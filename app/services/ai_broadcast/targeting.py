"""User targeting and lookup utilities for AI Broadcast Service."""

from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appeal, User
from app.repositories.user_repository import UserRepository


class UserTargeting:
    """Handles user and admin lookup/targeting logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def find_user(self, identifier: str | int) -> User | None:
        """Find user by various identifiers."""
        if isinstance(identifier, int):
            return await self.user_repo.get_by_telegram_id(identifier)

        identifier = str(identifier).strip()

        # @username
        if identifier.startswith("@"):
            username = identifier[1:]
            return await self.user_repo.get_by_username(username)

        # ID:xxx
        if identifier.upper().startswith("ID:"):
            try:
                user_id = int(identifier[3:])
                return await self.user_repo.get_by_id(user_id)
            except ValueError:
                return None

        # Telegram ID as string
        if identifier.isdigit():
            return await self.user_repo.get_by_telegram_id(
                int(identifier)
            )

        # Try username without @
        return await self.user_repo.get_by_username(identifier)

    async def get_users_by_group(
        self, group: str, limit: int
    ) -> list[int]:
        """Get telegram_ids for a user group."""
        now = datetime.utcnow()

        if group == "active_appeals":
            # Users with open appeals
            stmt = (
                select(User.telegram_id)
                .join(Appeal, Appeal.user_id == User.id)
                .where(Appeal.status.in_(["open", "in_progress"]))
                .distinct()
                .limit(limit)
            )
        elif group == "active_deposits":
            # Users with active deposits
            from app.models import Deposit

            stmt = (
                select(User.telegram_id)
                .join(Deposit, Deposit.user_id == User.id)
                .where(Deposit.status == "active")
                .distinct()
                .limit(limit)
            )
        elif group == "active_24h":
            # Users active in last 24 hours
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(User.telegram_id)
                .where(User.last_activity >= cutoff)
                .limit(limit)
            )
        elif group == "active_7d":
            # Users active in last 7 days
            cutoff = now - timedelta(days=7)
            stmt = (
                select(User.telegram_id)
                .where(User.last_activity >= cutoff)
                .limit(limit)
            )
        elif group == "all":
            # All users (not banned)
            stmt = (
                select(User.telegram_id)
                .where(User.is_banned == False)  # noqa: E712
                .limit(limit)
            )
        else:
            return []

        result = await self.session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def get_users_details_by_group(
        self, group: str, limit: int
    ) -> list[dict]:
        """Get user details for a group."""
        now = datetime.utcnow()

        if group == "active_appeals":
            stmt = (
                select(User)
                .join(Appeal, Appeal.user_id == User.id)
                .where(Appeal.status.in_(["open", "in_progress"]))
                .distinct()
                .limit(limit)
            )
        elif group == "active_deposits":
            from app.models import Deposit

            stmt = (
                select(User)
                .join(Deposit, Deposit.user_id == User.id)
                .where(Deposit.status == "active")
                .distinct()
                .limit(limit)
            )
        elif group == "active_24h":
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(User)
                .where(User.last_activity >= cutoff)
                .limit(limit)
            )
        elif group == "active_7d":
            cutoff = now - timedelta(days=7)
            stmt = (
                select(User)
                .where(User.last_activity >= cutoff)
                .limit(limit)
            )
        elif group == "all":
            stmt = (
                select(User)
                .where(User.is_banned == False)  # noqa: E712
                .limit(limit)
            )
        else:
            return []

        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "last_activity": (
                    u.last_activity.isoformat()
                    if u.last_activity
                    else None
                ),
            }
            for u in users
        ]

    async def find_admin(self, identifier: str | int) -> Any:
        """Find admin by username or telegram_id."""
        from app.models import Admin

        try:
            if isinstance(identifier, int):
                telegram_id = identifier
            elif identifier.startswith("@"):
                # Find by username
                username = identifier[1:]  # Remove @
                stmt = select(Admin).where(Admin.username == username)
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()
            elif identifier.isdigit():
                telegram_id = int(identifier)
            else:
                # Try as username without @
                stmt = select(Admin).where(Admin.username == identifier)
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()

            # Find by telegram_id
            stmt = select(Admin).where(
                Admin.telegram_id == telegram_id
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error finding admin: {e}")
            return None
