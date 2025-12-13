"""
AI Settings - Admin management operations.
"""
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.services.ai.commons import verify_admin

VALID_ROLES = ["moderator", "admin", "extended_admin"]


class AdminOpsMixin:
    """Mixin for admin management operations."""

    session: AsyncSession
    admin_telegram_id: int | None

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    async def create_admin(
        self, telegram_id: int, username: str | None, role: str = "moderator"
    ) -> str:
        """Create a new admin."""
        admin, error = await self._verify_admin()
        if error:
            return error

        if role not in VALID_ROLES:
            return f"❌ Неверная роль. Доступные: {', '.join(VALID_ROLES)}"

        try:
            admin_repo = AdminRepository(self.session)
            existing = await admin_repo.get_by_telegram_id(telegram_id)
            if existing:
                return (
                    f"❌ Админ с ID {telegram_id} уже существует "
                    f"(роль: {existing.role})"
                )

            from app.models.admin import Admin
            new_admin = Admin(
                telegram_id=telegram_id,
                username=username,
                role=role,
                is_blocked=False,
            )
            self.session.add(new_admin)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Super admin created new admin: "
                f"telegram_id={telegram_id}, username={username}, role={role}"
            )
            return (
                f"✅ Администратор создан:\n"
                f"• Telegram ID: `{telegram_id}`\n"
                f"• Username: @{username or 'не указан'}\n"
                f"• Роль: `{role}`"
            )
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating admin: {e}")
            return f"❌ Ошибка: {e}"

    async def delete_admin(self, telegram_id: int) -> str:
        """Delete an admin."""
        admin, error = await self._verify_admin()
        if error:
            return error

        try:
            admin_repo = AdminRepository(self.session)
            target_admin = await admin_repo.get_by_telegram_id(telegram_id)
            if not target_admin:
                return f"❌ Админ с ID {telegram_id} не найден"

            await self.session.delete(target_admin)
            await self.session.commit()
            logger.info(
                f"[АРЬЯ] Super admin deleted admin: telegram_id={telegram_id}"
            )
            return f"✅ Администратор с ID `{telegram_id}` удалён"
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting admin: {e}")
            return f"❌ Ошибка: {e}"
