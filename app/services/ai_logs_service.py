"""
AI Logs Service.

Provides admin action logs viewing for AI assistant:
- Get recent action logs
- Search logs
- Get admin activity summary
"""

from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.admin_action import AdminAction
from app.repositories.admin_action_repository import AdminActionRepository
from app.repositories.admin_repository import AdminRepository


class AILogsService:
    """
    AI-powered admin logs service.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.action_repo = AdminActionRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    async def get_recent_logs(
        self,
        limit: int = 30,
        action_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Get recent admin action logs.

        Args:
            limit: Max results
            action_type: Filter by action type (optional)
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(AdminAction).order_by(
            AdminAction.created_at.desc()
        ).limit(limit)

        if action_type:
            stmt = stmt.where(AdminAction.action_type == action_type)

        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())

        if not logs:
            return {
                "success": True,
                "count": 0,
                "logs": [],
                "message": "ℹ️ Логи не найдены"
            }

        # Get admin info
        admin_repo = AdminRepository(self.session)

        logs_list = []
        for log in logs:
            admin_info = None
            if log.admin_id:
                adm = await admin_repo.get_by_id(log.admin_id)
                if adm:
                    admin_info = f"@{adm.username}" if adm.username else f"ID:{adm.telegram_id}"

            logs_list.append({
                "id": log.id,
                "admin": admin_info,
                "action_type": log.action_type,
                "target_user_id": log.target_user_id,
                "details": log.details,
                "created": log.created_at.strftime("%d.%m.%Y %H:%M") if log.created_at else None,
            })

        return {
            "success": True,
            "count": len(logs_list),
            "logs": logs_list,
            "message": "📋 Последние действия админов"
        }

    async def get_admin_activity(
        self,
        admin_identifier: str | int,
        limit: int = 30,
    ) -> dict[str, Any]:
        """
        Get activity for a specific admin.

        Args:
            admin_identifier: @username or admin_id
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

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

        # Get logs for this admin
        stmt = select(AdminAction).where(
            AdminAction.admin_id == target.id
        ).order_by(AdminAction.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())

        logs_list = []
        for log in logs:
            logs_list.append({
                "id": log.id,
                "action_type": log.action_type,
                "target_user_id": log.target_user_id,
                "details": log.details,
                "created": log.created_at.strftime("%d.%m.%Y %H:%M") if log.created_at else None,
            })

        # Count by action type
        count_stmt = select(
            AdminAction.action_type,
            func.count(AdminAction.id)
        ).where(
            AdminAction.admin_id == target.id
        ).group_by(AdminAction.action_type)

        count_result = await self.session.execute(count_stmt)
        action_counts = {row[0]: row[1] for row in count_result.all()}

        return {
            "success": True,
            "admin": f"@{target.username}" if target.username else f"ID:{target.telegram_id}",
            "total_actions": sum(action_counts.values()),
            "by_action_type": action_counts,
            "recent_logs": logs_list,
            "message": "📊 Активность администратора"
        }

    async def search_logs(
        self,
        user_id: int | None = None,
        action_type: str | None = None,
        limit: int = 30,
    ) -> dict[str, Any]:
        """
        Search admin logs with filters.

        Args:
            user_id: Filter by target user ID
            action_type: Filter by action type
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(AdminAction).order_by(
            AdminAction.created_at.desc()
        ).limit(limit)

        if user_id:
            stmt = stmt.where(AdminAction.target_user_id == user_id)

        if action_type:
            stmt = stmt.where(AdminAction.action_type == action_type)

        result = await self.session.execute(stmt)
        logs = list(result.scalars().all())

        if not logs:
            return {
                "success": True,
                "count": 0,
                "logs": [],
                "message": "ℹ️ Логи не найдены по заданным критериям"
            }

        admin_repo = AdminRepository(self.session)

        logs_list = []
        for log in logs:
            admin_info = None
            if log.admin_id:
                adm = await admin_repo.get_by_id(log.admin_id)
                if adm:
                    admin_info = f"@{adm.username}" if adm.username else f"ID:{adm.telegram_id}"

            logs_list.append({
                "id": log.id,
                "admin": admin_info,
                "action_type": log.action_type,
                "target_user_id": log.target_user_id,
                "details": log.details,
                "created": log.created_at.strftime("%d.%m.%Y %H:%M") if log.created_at else None,
            })

        return {
            "success": True,
            "count": len(logs_list),
            "filters": {
                "user_id": user_id,
                "action_type": action_type,
            },
            "logs": logs_list,
            "message": "🔍 Результаты поиска по логам"
        }

    async def get_action_types_stats(self) -> dict[str, Any]:
        """
        Get statistics of action types.
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(
            AdminAction.action_type,
            func.count(AdminAction.id)
        ).group_by(AdminAction.action_type).order_by(
            func.count(AdminAction.id).desc()
        )

        result = await self.session.execute(stmt)
        stats = {row[0]: row[1] for row in result.all()}

        return {
            "success": True,
            "stats": stats,
            "total_actions": sum(stats.values()),
            "message": "📊 Статистика типов действий"
        }
