"""
AI Admin Management Service.

Provides admin management tools for AI assistant:
- View all admins and their roles
- Add/remove admins
- Block/unblock admins
- View admin activity

SECURITY: SUPER_ADMIN only for most operations.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository


# Only these users can manage admins
SUPER_ADMIN_IDS = [
    1040687384,  # @VladarevInvestBrok (Командир/super_admin)
]


class AIAdminManagementService:
    """
    AI-powered admin management service.

    SECURITY: Super admin only for all management operations.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    def _is_super_admin(self) -> bool:
        """Check if current admin is super_admin."""
        return self.admin_telegram_id in SUPER_ADMIN_IDS

    async def get_admins_list(self) -> dict[str, Any]:
        """
        Get list of all administrators.

        Returns:
            List of admins with their roles and status
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(Admin).order_by(Admin.role.desc(), Admin.created_at.asc())
        result = await self.session.execute(stmt)
        admins = list(result.scalars().all())

        admins_list = []
        for a in admins:
            role_emoji = {
                "super_admin": "👑",
                "admin": "👤",
                "support": "💬",
            }.get(a.role, "❓")

            status_emoji = "🚫" if a.is_blocked else "✅"

            admins_list.append({
                "id": a.id,
                "telegram_id": a.telegram_id,
                "username": f"@{a.username}" if a.username else f"ID:{a.telegram_id}",
                "role": f"{role_emoji} {a.role}",
                "is_blocked": a.is_blocked,
                "status": status_emoji,
                "created": a.created_at.strftime("%d.%m.%Y") if a.created_at else None,
                "last_active": a.last_active_at.strftime("%d.%m.%Y %H:%M") if a.last_active_at else None,
            })

        return {
            "success": True,
            "count": len(admins_list),
            "admins": admins_list,
            "message": f"👥 Администраторов: {len(admins_list)}"
        }

    async def get_admin_details(self, admin_identifier: str | int) -> dict[str, Any]:
        """
        Get detailed info about a specific admin.

        Args:
            admin_identifier: @username or telegram_id
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Only super_admin can view other admin details
        if not self._is_super_admin():
            return {
                "success": False,
                "error": "❌ Только Командир может просматривать детали администраторов"
            }

        admin_repo = AdminRepository(self.session)

        # Find target admin
        target = None
        if isinstance(admin_identifier, int) or (isinstance(admin_identifier, str) and admin_identifier.isdigit()):
            target = await admin_repo.get_by_telegram_id(int(admin_identifier))
        elif isinstance(admin_identifier, str) and admin_identifier.startswith("@"):
            username = admin_identifier[1:]
            stmt = select(Admin).where(Admin.username == username)
            result = await self.session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            return {"success": False, "error": f"❌ Администратор '{admin_identifier}' не найден"}

        role_desc = {
            "super_admin": "👑 Супер-администратор (полный доступ)",
            "admin": "👤 Администратор (расширенный доступ)",
            "support": "💬 Поддержка (ограниченный доступ)",
        }.get(target.role, f"❓ {target.role}")

        return {
            "success": True,
            "admin": {
                "id": target.id,
                "telegram_id": target.telegram_id,
                "username": f"@{target.username}" if target.username else None,
                "first_name": target.first_name,
                "role": role_desc,
                "is_blocked": target.is_blocked,
                "created_at": target.created_at.strftime("%d.%m.%Y %H:%M") if target.created_at else None,
                "last_active_at": target.last_active_at.strftime("%d.%m.%Y %H:%M") if target.last_active_at else None,
            },
            "message": "📋 Профиль администратора"
        }

    async def block_admin(
        self,
        admin_identifier: str | int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Block an administrator.

        SECURITY: SUPER_ADMIN only!

        Args:
            admin_identifier: @username or telegram_id
            reason: Block reason
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_super_admin():
            logger.warning(
                f"AI ADMIN SECURITY: Non-superadmin {self.admin_telegram_id} "
                f"attempted to block admin"
            )
            return {
                "success": False,
                "error": "❌ ТОЛЬКО КОМАНДИР может блокировать администраторов!"
            }

        admin_repo = AdminRepository(self.session)

        # Find target admin
        target = None
        if isinstance(admin_identifier, int) or (isinstance(admin_identifier, str) and admin_identifier.isdigit()):
            target = await admin_repo.get_by_telegram_id(int(admin_identifier))
        elif isinstance(admin_identifier, str) and admin_identifier.startswith("@"):
            username = admin_identifier[1:]
            stmt = select(Admin).where(Admin.username == username)
            result = await self.session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            return {"success": False, "error": f"❌ Администратор '{admin_identifier}' не найден"}

        # Prevent blocking super_admin
        if target.telegram_id in SUPER_ADMIN_IDS:
            return {"success": False, "error": "❌ Нельзя заблокировать супер-администратора!"}

        if target.is_blocked:
            return {"success": False, "error": "❌ Администратор уже заблокирован"}

        target.is_blocked = True
        await self.session.commit()

        logger.warning(
            f"AI ADMIN: Super-admin {self.admin_telegram_id} blocked admin "
            f"{target.telegram_id} (@{target.username}): {reason}"
        )

        return {
            "success": True,
            "admin": f"@{target.username}" if target.username else f"ID:{target.telegram_id}",
            "reason": reason,
            "message": "🚫 Администратор заблокирован"
        }

    async def unblock_admin(self, admin_identifier: str | int) -> dict[str, Any]:
        """
        Unblock an administrator.

        SECURITY: SUPER_ADMIN only!
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_super_admin():
            return {
                "success": False,
                "error": "❌ ТОЛЬКО КОМАНДИР может разблокировать администраторов!"
            }

        admin_repo = AdminRepository(self.session)

        # Find target admin
        target = None
        if isinstance(admin_identifier, int) or (isinstance(admin_identifier, str) and admin_identifier.isdigit()):
            target = await admin_repo.get_by_telegram_id(int(admin_identifier))
        elif isinstance(admin_identifier, str) and admin_identifier.startswith("@"):
            username = admin_identifier[1:]
            stmt = select(Admin).where(Admin.username == username)
            result = await self.session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            return {"success": False, "error": f"❌ Администратор '{admin_identifier}' не найден"}

        if not target.is_blocked:
            return {"success": False, "error": "❌ Администратор не заблокирован"}

        target.is_blocked = False
        await self.session.commit()

        logger.info(
            f"AI ADMIN: Super-admin {self.admin_telegram_id} unblocked admin "
            f"{target.telegram_id} (@{target.username})"
        )

        return {
            "success": True,
            "admin": f"@{target.username}" if target.username else f"ID:{target.telegram_id}",
            "message": "✅ Администратор разблокирован"
        }

    async def change_admin_role(
        self,
        admin_identifier: str | int,
        new_role: str,
    ) -> dict[str, Any]:
        """
        Change admin role.

        SECURITY: SUPER_ADMIN only!

        Args:
            admin_identifier: @username or telegram_id
            new_role: New role (admin, support)
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_super_admin():
            return {
                "success": False,
                "error": "❌ ТОЛЬКО КОМАНДИР может изменять роли администраторов!"
            }

        valid_roles = ["admin", "support"]
        if new_role.lower() not in valid_roles:
            return {
                "success": False,
                "error": f"❌ Неверная роль. Допустимые: {', '.join(valid_roles)}"
            }

        admin_repo = AdminRepository(self.session)

        # Find target admin
        target = None
        if isinstance(admin_identifier, int) or (isinstance(admin_identifier, str) and admin_identifier.isdigit()):
            target = await admin_repo.get_by_telegram_id(int(admin_identifier))
        elif isinstance(admin_identifier, str) and admin_identifier.startswith("@"):
            username = admin_identifier[1:]
            stmt = select(Admin).where(Admin.username == username)
            result = await self.session.execute(stmt)
            target = result.scalar_one_or_none()

        if not target:
            return {"success": False, "error": f"❌ Администратор '{admin_identifier}' не найден"}

        # Prevent changing super_admin role
        if target.role == "super_admin":
            return {"success": False, "error": "❌ Нельзя изменить роль супер-администратора!"}

        old_role = target.role
        target.role = new_role.lower()
        await self.session.commit()

        logger.info(
            f"AI ADMIN: Super-admin {self.admin_telegram_id} changed role for "
            f"{target.telegram_id} (@{target.username}): {old_role} → {new_role}"
        )

        return {
            "success": True,
            "admin": f"@{target.username}" if target.username else f"ID:{target.telegram_id}",
            "old_role": old_role,
            "new_role": new_role,
            "message": f"✅ Роль изменена: {old_role} → {new_role}"
        }

    async def get_admin_stats(self) -> dict[str, Any]:
        """
        Get statistics about administrators.

        Returns:
            Admin statistics
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Count by role
        role_stmt = select(Admin.role, func.count(Admin.id)).group_by(Admin.role)
        role_result = await self.session.execute(role_stmt)
        by_role = {row[0]: row[1] for row in role_result.all()}

        # Count blocked
        blocked_stmt = select(func.count(Admin.id)).where(Admin.is_blocked == True)
        blocked_result = await self.session.execute(blocked_stmt)
        blocked_count = blocked_result.scalar() or 0

        # Total
        total_stmt = select(func.count(Admin.id))
        total_result = await self.session.execute(total_stmt)
        total_count = total_result.scalar() or 0

        return {
            "success": True,
            "stats": {
                "total": total_count,
                "super_admins": by_role.get("super_admin", 0),
                "admins": by_role.get("admin", 0),
                "support": by_role.get("support", 0),
                "blocked": blocked_count,
                "active": total_count - blocked_count,
            },
            "message": "👥 Статистика администраторов"
        }
