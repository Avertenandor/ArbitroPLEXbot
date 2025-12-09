"""
AI Appeals Service.

Provides appeal management tools for AI assistant with STRICT security:
- Only callable from admin AI assistant context
- Validates admin credentials before every operation
- Full audit logging

SECURITY: This service is ONLY accessible through the AI assistant
when a verified admin is in an authenticated admin session.
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appeal import Appeal, AppealStatus
from app.models.blacklist import Blacklist
from app.models.user import User
from app.repositories.admin_repository import AdminRepository


class AIAppealsService:
    """
    AI-powered appeals management service.
    
    SECURITY NOTES:
    - admin_data MUST come from authenticated admin session
    - All operations are logged with admin info
    - Only admins can perform actions
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        
        # Extract admin info for security logging
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username") or self.admin_data.get("Имя")
        
    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """
        Verify admin credentials from session data.
        
        Returns:
            Tuple of (admin_model, error_message)
        """
        if not self.admin_telegram_id:
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Не удалось определить администратора"
        
        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)
        
        if not admin:
            logger.warning(
                f"AI APPEALS SECURITY: Unauthorized attempt from telegram_id={self.admin_telegram_id}"
            )
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Администратор не найден"
        
        if admin.is_blocked:
            logger.warning(
                f"AI APPEALS SECURITY: Blocked admin attempt: {admin.telegram_id} (@{admin.username})"
            )
            return None, "❌ ОШИБКА: Администратор заблокирован"
        
        return admin, None

    async def get_appeals_list(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of appeals with optional status filter.
        
        Args:
            status: Filter by status (pending, under_review, approved, rejected)
            limit: Maximum number of appeals to return
            
        Returns:
            Result dict with appeals list
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Build query - no joinedload since Appeal doesn't have user relationship
        stmt = (
            select(Appeal)
            .order_by(Appeal.created_at.desc())
            .limit(limit)
        )
        
        if status:
            valid_statuses = ["pending", "under_review", "approved", "rejected"]
            if status.lower() not in valid_statuses:
                return {
                    "success": False, 
                    "error": f"❌ Неверный статус. Допустимые: {', '.join(valid_statuses)}"
                }
            stmt = stmt.where(Appeal.status == status.lower())
        
        result = await self.session.execute(stmt)
        appeals = list(result.scalars().all())
        
        if not appeals:
            status_text = f" со статусом '{status}'" if status else ""
            return {
                "success": True,
                "appeals": [],
                "message": f"ℹ️ Обращений{status_text} не найдено"
            }
        
        # Collect user_ids and fetch users in batch
        user_ids = [a.user_id for a in appeals if a.user_id]
        users_map = {}
        if user_ids:
            user_stmt = select(User).where(User.id.in_(user_ids))
            user_result = await self.session.execute(user_stmt)
            for u in user_result.scalars().all():
                users_map[u.id] = u
        
        # Format appeals
        appeals_list = []
        for a in appeals:
            # Get user info
            user = users_map.get(a.user_id)
            if user:
                user_info = f"@{user.username}" if user.username else f"ID:{user.telegram_id}"
            else:
                user_info = f"User#{a.user_id}"
            
            status_emoji = {
                "pending": "🟡",
                "under_review": "🔵", 
                "approved": "✅",
                "rejected": "❌"
            }.get(a.status, "⚪")
            
            appeals_list.append({
                "id": a.id,
                "user": user_info,
                "user_id": a.user_id,
                "status": f"{status_emoji} {a.status}",
                "text_preview": (a.appeal_text or "")[:100] + ("..." if len(a.appeal_text or "") > 100 else ""),
                "created": a.created_at.strftime("%d.%m.%Y %H:%M") if a.created_at else "—",
                "reviewed_at": a.reviewed_at.strftime("%d.%m.%Y %H:%M") if a.reviewed_at else None,
            })
        
        # Count by status
        count_stmt = select(Appeal.status, func.count(Appeal.id)).group_by(Appeal.status)
        count_result = await self.session.execute(count_stmt)
        counts = {row[0]: row[1] for row in count_result.all()}
        
        return {
            "success": True,
            "total_count": len(appeals_list),
            "counts": {
                "pending": counts.get("pending", 0),
                "under_review": counts.get("under_review", 0),
                "approved": counts.get("approved", 0),
                "rejected": counts.get("rejected", 0),
            },
            "appeals": appeals_list,
            "message": f"📋 Найдено {len(appeals_list)} обращений"
        }

    async def get_appeal_details(
        self,
        appeal_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific appeal.
        
        Args:
            appeal_id: Appeal ID
            
        Returns:
            Result dict with appeal details
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Get appeal
        stmt = select(Appeal).where(Appeal.id == appeal_id)
        result = await self.session.execute(stmt)
        appeal = result.scalar_one_or_none()
        
        if not appeal:
            return {"success": False, "error": f"❌ Обращение ID {appeal_id} не найдено"}
        
        # Get user info separately
        user_info = f"User#{appeal.user_id}"
        user_telegram = None
        if appeal.user_id:
            user_stmt = select(User).where(User.id == appeal.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                user_info = f"@{user.username}" if user.username else f"ID:{user.telegram_id}"
                user_telegram = user.telegram_id
        
        status_emoji = {
            "pending": "🟡 Ожидает",
            "under_review": "🔵 На рассмотрении",
            "approved": "✅ Одобрено",
            "rejected": "❌ Отклонено"
        }.get(appeal.status, appeal.status)
        
        # Get reviewer info if reviewed
        reviewer_info = None
        if appeal.reviewed_by_admin_id:
            admin_repo = AdminRepository(self.session)
            reviewer = await admin_repo.get_by_id(appeal.reviewed_by_admin_id)
            if reviewer:
                reviewer_info = f"@{reviewer.username}" if reviewer.username else f"Admin #{reviewer.id}"
        
        return {
            "success": True,
            "appeal": {
                "id": appeal.id,
                "user": user_info,
                "user_id": appeal.user_id,
                "user_telegram_id": user_telegram,
                "blacklist_id": appeal.blacklist_id,
                "status": status_emoji,
                "text": appeal.appeal_text,
                "created": appeal.created_at.strftime("%d.%m.%Y %H:%M") if appeal.created_at else "—",
                "reviewed_by": reviewer_info,
                "reviewed_at": appeal.reviewed_at.strftime("%d.%m.%Y %H:%M") if appeal.reviewed_at else None,
                "review_notes": appeal.review_notes,
            },
            "message": f"📋 Обращение #{appeal.id}"
        }

    async def take_appeal(
        self,
        appeal_id: int,
    ) -> dict[str, Any]:
        """
        Take appeal for review (set status to under_review).
        
        Args:
            appeal_id: Appeal ID
            
        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        # Get appeal
        stmt = select(Appeal).where(Appeal.id == appeal_id)
        result = await self.session.execute(stmt)
        appeal = result.scalar_one_or_none()
        
        if not appeal:
            return {"success": False, "error": f"❌ Обращение ID {appeal_id} не найдено"}
        
        if appeal.status != AppealStatus.PENDING:
            return {
                "success": False, 
                "error": f"❌ Обращение уже имеет статус '{appeal.status}'. Взять можно только 'pending'."
            }
        
        # Update appeal
        appeal.status = AppealStatus.UNDER_REVIEW
        appeal.reviewed_by_admin_id = admin.id
        
        await self.session.commit()
        
        logger.info(
            f"AI APPEALS: Admin {admin.telegram_id} (@{admin.username}) "
            f"took appeal {appeal_id} for review"
        )
        
        return {
            "success": True,
            "appeal_id": appeal_id,
            "new_status": "under_review",
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": f"✅ Обращение #{appeal_id} взято на рассмотрение"
        }

    async def resolve_appeal(
        self,
        appeal_id: int,
        decision: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Resolve appeal (approve or reject).
        
        SECURITY: Only admins can resolve appeals.
        
        Args:
            appeal_id: Appeal ID
            decision: "approve" or "reject"
            notes: Optional review notes
            
        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if decision not in ["approve", "reject"]:
            return {
                "success": False,
                "error": "❌ Решение должно быть 'approve' (одобрить) или 'reject' (отклонить)"
            }
        
        # Get appeal
        stmt = select(Appeal).where(Appeal.id == appeal_id)
        result = await self.session.execute(stmt)
        appeal = result.scalar_one_or_none()
        
        if not appeal:
            return {"success": False, "error": f"❌ Обращение ID {appeal_id} не найдено"}
        
        if appeal.status in [AppealStatus.APPROVED, AppealStatus.REJECTED]:
            return {
                "success": False,
                "error": f"❌ Обращение уже закрыто со статусом '{appeal.status}'"
            }
        
        # Update appeal
        new_status = AppealStatus.APPROVED if decision == "approve" else AppealStatus.REJECTED
        appeal.status = new_status
        appeal.reviewed_by_admin_id = admin.id
        appeal.reviewed_at = datetime.now(UTC)
        appeal.review_notes = f"[АРЬЯ] {notes}" if notes else "[АРЬЯ] Решение принято через AI-ассистента"
        
        # If approved, unblock user from blacklist
        if decision == "approve" and appeal.blacklist_id:
            bl_stmt = select(Blacklist).where(Blacklist.id == appeal.blacklist_id)
            bl_result = await self.session.execute(bl_stmt)
            blacklist = bl_result.scalar_one_or_none()
            
            if blacklist:
                blacklist.is_active = False
                blacklist.notes = (blacklist.notes or "") + f"\n[АРЬЯ] Разблокирован по обращению #{appeal_id}"
        
        await self.session.commit()
        
        # Get user info for logging
        user_info = f"User#{appeal.user_id}"
        if appeal.user_id:
            user_stmt = select(User).where(User.id == appeal.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            if user:
                user_info = f"@{user.username}" if user.username else f"ID:{user.telegram_id}"
        
        decision_emoji = "✅" if decision == "approve" else "❌"
        decision_text = "одобрено" if decision == "approve" else "отклонено"
        
        logger.info(
            f"AI APPEALS: Admin {admin.telegram_id} (@{admin.username}) "
            f"{decision_text} appeal {appeal_id} for user {user_info}"
        )
        
        result_msg = f"{decision_emoji} Обращение #{appeal_id} {decision_text}"
        if decision == "approve":
            result_msg += "\n🔓 Пользователь разблокирован"
        
        return {
            "success": True,
            "appeal_id": appeal_id,
            "user": user_info,
            "decision": decision,
            "new_status": new_status,
            "notes": notes,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": result_msg
        }

    async def reply_to_appeal(
        self,
        appeal_id: int,
        message: str,
        bot: Any = None,
    ) -> dict[str, Any]:
        """
        Send reply message to user who submitted the appeal.
        
        Args:
            appeal_id: Appeal ID
            message: Message text to send
            bot: Bot instance for sending
            
        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}
        
        if not bot:
            return {"success": False, "error": "❌ Бот не инициализирован"}
        
        if not message or len(message) < 5:
            return {"success": False, "error": "❌ Сообщение должно содержать минимум 5 символов"}
        
        # Get appeal
        stmt = select(Appeal).where(Appeal.id == appeal_id)
        result = await self.session.execute(stmt)
        appeal = result.scalar_one_or_none()
        
        if not appeal:
            return {"success": False, "error": f"❌ Обращение ID {appeal_id} не найдено"}
        
        # Get user separately
        user = None
        if appeal.user_id:
            user_stmt = select(User).where(User.id == appeal.user_id)
            user_result = await self.session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
        
        if not user or not user.telegram_id:
            return {"success": False, "error": "❌ Не удалось найти пользователя для отправки"}
        
        # Format message
        admin_name = f"@{admin.username}" if admin.username else "Администратор"
        formatted_message = (
            f"📬 **Ответ на ваше обращение #{appeal_id}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{message}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_От: {admin_name}_"
        )
        
        # Send message
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=formatted_message,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send reply to appeal {appeal_id}: {e}")
            return {"success": False, "error": f"❌ Не удалось отправить: {str(e)}"}
        
        user_info = f"@{user.username}" if user.username else f"ID:{user.telegram_id}"
        
        logger.info(
            f"AI APPEALS: Admin {admin.telegram_id} replied to appeal {appeal_id}: {message[:50]}..."
        )
        
        return {
            "success": True,
            "appeal_id": appeal_id,
            "user": user_info,
            "message_sent": message[:100] + "..." if len(message) > 100 else message,
            "message": "✅ Ответ отправлен пользователю"
        }
