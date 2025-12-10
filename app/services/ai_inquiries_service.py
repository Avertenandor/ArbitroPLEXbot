"""
AI User Inquiries Service.

Provides user inquiry management tools for AI assistant with STRICT security:
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
from sqlalchemy.orm import joinedload

from app.models.user_inquiry import InquiryMessage, InquiryStatus, UserInquiry
from app.repositories.admin_repository import AdminRepository


class AIInquiriesService:
    """
    AI-powered user inquiries management service.
    
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
        self.admin_username = (
            self.admin_data.get("username") or self.admin_data.get("Имя")
        )

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials from session data."""
        if not self.admin_telegram_id:
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin:
            logger.warning(
                f"AI INQUIRIES SECURITY: Unauthorized attempt "
                f"from telegram_id={self.admin_telegram_id}"
            )
            return None, "❌ ОШИБКА БЕЗОПАСНОСТИ: Администратор не найден"

        if admin.is_blocked:
            logger.warning(
                f"AI INQUIRIES SECURITY: Blocked admin attempt: "
                f"{admin.telegram_id} (@{admin.username})"
            )
            return None, "❌ ОШИБКА: Администратор заблокирован"

        return admin, None

    async def get_inquiries_list(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of user inquiries with optional status filter.
        
        Args:
            status: Filter by status (new, in_progress, closed)
            limit: Maximum number of inquiries to return
            
        Returns:
            Result dict with inquiries list
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Build query with relationships
        stmt = (
            select(UserInquiry)
            .options(joinedload(UserInquiry.user))
            .options(joinedload(UserInquiry.assigned_admin))
            .order_by(UserInquiry.created_at.desc())
            .limit(limit)
        )

        if status:
            valid_statuses = ["new", "in_progress", "closed"]
            if status.lower() not in valid_statuses:
                return {
                    "success": False,
                    "error": f"❌ Неверный статус. Допустимые: {', '.join(valid_statuses)}"
                }
            stmt = stmt.where(UserInquiry.status == status.lower())

        result = await self.session.execute(stmt)
        inquiries = list(result.scalars().unique().all())

        if not inquiries:
            status_text = f" со статусом '{status}'" if status else ""
            return {
                "success": True,
                "inquiries": [],
                "message": f"ℹ️ Обращений{status_text} не найдено"
            }

        # Format inquiries
        inquiries_list = []
        for inq in inquiries:
            # Get user info
            user_info = "Неизвестен"
            if inq.user:
                user_info = (
                    f"@{inq.user.username}"
                    if inq.user.username
                    else f"ID:{inq.user.telegram_id}"
                )

            # Get admin info
            admin_info = None
            if inq.assigned_admin:
                admin_info = (
                    f"@{inq.assigned_admin.username}"
                    if inq.assigned_admin.username
                    else f"Admin#{inq.assigned_admin_id}"
                )

            status_emoji = {
                "new": "🆕",
                "in_progress": "🔵",
                "closed": "✅"
            }.get(inq.status, "⚪")

            inquiries_list.append({
                "id": inq.id,
                "user": user_info,
                "user_id": inq.user_id,
                "telegram_id": inq.telegram_id,
                "status": f"{status_emoji} {inq.status}",
                "question_preview": (
                    (inq.initial_question or "")[:100] +
                    ("..." if len(inq.initial_question or "") > 100 else "")
                ),
                "assigned_to": admin_info,
                "created": (
                    inq.created_at.strftime("%d.%m.%Y %H:%M")
                    if inq.created_at else "—"
                ),
            })

        # Count by status
        count_stmt = (
            select(UserInquiry.status, func.count(UserInquiry.id))
            .group_by(UserInquiry.status)
        )
        count_result = await self.session.execute(count_stmt)
        counts = {row[0]: row[1] for row in count_result.all()}

        return {
            "success": True,
            "total_count": len(inquiries_list),
            "counts": {
                "new": counts.get("new", 0),
                "in_progress": counts.get("in_progress", 0),
                "closed": counts.get("closed", 0),
            },
            "inquiries": inquiries_list,
            "message": f"📋 Найдено {len(inquiries_list)} обращений"
        }

    async def get_inquiry_details(
        self,
        inquiry_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed information about a specific inquiry with messages.
        
        Args:
            inquiry_id: Inquiry ID
            
        Returns:
            Result dict with inquiry details and messages
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Get inquiry with relationships
        stmt = (
            select(UserInquiry)
            .options(joinedload(UserInquiry.user))
            .options(joinedload(UserInquiry.assigned_admin))
            .options(joinedload(UserInquiry.messages))
            .where(UserInquiry.id == inquiry_id)
        )
        result = await self.session.execute(stmt)
        inquiry = result.scalar_one_or_none()

        if not inquiry:
            return {
                "success": False,
                "error": f"❌ Обращение ID {inquiry_id} не найдено"
            }

        # Get user info
        user_info = "Неизвестен"
        if inquiry.user:
            user_info = (
                f"@{inquiry.user.username}"
                if inquiry.user.username
                else f"ID:{inquiry.user.telegram_id}"
            )

        # Get admin info
        admin_info = None
        if inquiry.assigned_admin:
            admin_info = (
                f"@{inquiry.assigned_admin.username}"
                if inquiry.assigned_admin.username
                else f"Admin#{inquiry.assigned_admin_id}"
            )

        status_emoji = {
            "new": "🆕 Новое",
            "in_progress": "🔵 В работе",
            "closed": "✅ Закрыто"
        }.get(inquiry.status, inquiry.status)

        # Format messages
        messages_list = []
        for msg in (inquiry.messages or []):
            sender = "👤 Пользователь" if msg.sender_type == "user" else "👨‍💼 Админ"
            messages_list.append({
                "sender": sender,
                "text": msg.message_text[:200] + ("..." if len(msg.message_text) > 200 else ""),
                "time": msg.created_at.strftime("%d.%m %H:%M") if msg.created_at else "—",
            })

        return {
            "success": True,
            "inquiry": {
                "id": inquiry.id,
                "user": user_info,
                "user_id": inquiry.user_id,
                "telegram_id": inquiry.telegram_id,
                "status": status_emoji,
                "question": inquiry.initial_question,
                "assigned_to": admin_info,
                "created": (
                    inquiry.created_at.strftime("%d.%m.%Y %H:%M")
                    if inquiry.created_at else "—"
                ),
                "assigned_at": (
                    inquiry.assigned_at.strftime("%d.%m.%Y %H:%M")
                    if inquiry.assigned_at else None
                ),
                "closed_at": (
                    inquiry.closed_at.strftime("%d.%m.%Y %H:%M")
                    if inquiry.closed_at else None
                ),
                "messages_count": len(messages_list),
                "messages": messages_list[-10:],  # Last 10 messages
            },
            "message": f"📋 Обращение #{inquiry.id}"
        }

    async def take_inquiry(
        self,
        inquiry_id: int,
    ) -> dict[str, Any]:
        """
        Take inquiry for processing (assign to current admin).
        
        Args:
            inquiry_id: Inquiry ID
            
        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Get inquiry
        stmt = (
            select(UserInquiry)
            .options(joinedload(UserInquiry.user))
            .where(UserInquiry.id == inquiry_id)
        )
        result = await self.session.execute(stmt)
        inquiry = result.scalar_one_or_none()

        if not inquiry:
            return {
                "success": False,
                "error": f"❌ Обращение ID {inquiry_id} не найдено"
            }

        if inquiry.status == InquiryStatus.CLOSED:
            return {
                "success": False,
                "error": "❌ Это обращение уже закрыто"
            }

        if inquiry.assigned_admin_id and inquiry.assigned_admin_id != admin.id:
            return {
                "success": False,
                "error": "❌ Обращение уже назначено другому админу"
            }

        # Assign to admin
        inquiry.status = InquiryStatus.IN_PROGRESS
        inquiry.assigned_admin_id = admin.id
        inquiry.assigned_at = datetime.now(UTC)

        await self.session.commit()

        # Get user info
        user_info = "Неизвестен"
        if inquiry.user:
            user_info = (
                f"@{inquiry.user.username}"
                if inquiry.user.username
                else f"ID:{inquiry.user.telegram_id}"
            )

        logger.info(
            f"AI INQUIRIES: Admin {admin.telegram_id} (@{admin.username}) "
            f"took inquiry {inquiry_id} from {user_info}"
        )

        return {
            "success": True,
            "inquiry_id": inquiry_id,
            "user": user_info,
            "question": inquiry.initial_question[:100] + "...",
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": f"✅ Обращение #{inquiry_id} взято в работу"
        }

    async def reply_to_inquiry(
        self,
        inquiry_id: int,
        message: str,
        bot: Any = None,
    ) -> dict[str, Any]:
        """
        Send reply to user's inquiry.
        
        Args:
            inquiry_id: Inquiry ID
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

        if not message or len(message) < 3:
            return {
                "success": False,
                "error": "❌ Сообщение должно содержать минимум 3 символа"
            }

        # Get inquiry
        stmt = (
            select(UserInquiry)
            .options(joinedload(UserInquiry.user))
            .where(UserInquiry.id == inquiry_id)
        )
        result = await self.session.execute(stmt)
        inquiry = result.scalar_one_or_none()

        if not inquiry:
            return {
                "success": False,
                "error": f"❌ Обращение ID {inquiry_id} не найдено"
            }

        if inquiry.status == InquiryStatus.CLOSED:
            return {
                "success": False,
                "error": "❌ Нельзя ответить на закрытое обращение"
            }

        # Auto-assign if not assigned
        if not inquiry.assigned_admin_id:
            inquiry.status = InquiryStatus.IN_PROGRESS
            inquiry.assigned_admin_id = admin.id
            inquiry.assigned_at = datetime.now(UTC)

        # Create message record
        new_message = InquiryMessage(
            inquiry_id=inquiry_id,
            sender_type="admin",
            sender_id=admin.id,
            message_text=f"[АРЬЯ] {message}",
            created_at=datetime.now(UTC),
        )
        self.session.add(new_message)

        await self.session.commit()

        # Send message to user
        admin_name = f"@{admin.username}" if admin.username else "Администратор"
        formatted_message = (
            f"📬 **Ответ на ваше обращение**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{message}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_От: {admin_name}_"
        )

        try:
            await bot.send_message(
                chat_id=inquiry.telegram_id,
                text=formatted_message,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send reply to inquiry {inquiry_id}: {e}")
            return {
                "success": False,
                "error": f"❌ Не удалось отправить: {str(e)}"
            }

        # Get user info
        user_info = "Неизвестен"
        if inquiry.user:
            user_info = (
                f"@{inquiry.user.username}"
                if inquiry.user.username
                else f"ID:{inquiry.user.telegram_id}"
            )

        logger.info(
            f"AI INQUIRIES: Admin {admin.telegram_id} replied to "
            f"inquiry {inquiry_id}: {message[:50]}..."
        )

        return {
            "success": True,
            "inquiry_id": inquiry_id,
            "user": user_info,
            "message_sent": message[:100] + ("..." if len(message) > 100 else ""),
            "message": "✅ Ответ отправлен пользователю"
        }

    async def close_inquiry(
        self,
        inquiry_id: int,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Close an inquiry.
        
        Args:
            inquiry_id: Inquiry ID
            reason: Optional closing reason
            
        Returns:
            Result dict
        """
        # Verify admin
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Get inquiry
        stmt = (
            select(UserInquiry)
            .options(joinedload(UserInquiry.user))
            .where(UserInquiry.id == inquiry_id)
        )
        result = await self.session.execute(stmt)
        inquiry = result.scalar_one_or_none()

        if not inquiry:
            return {
                "success": False,
                "error": f"❌ Обращение ID {inquiry_id} не найдено"
            }

        if inquiry.status == InquiryStatus.CLOSED:
            return {
                "success": False,
                "error": "❌ Обращение уже закрыто"
            }

        # Close inquiry
        inquiry.status = InquiryStatus.CLOSED
        inquiry.closed_at = datetime.now(UTC)
        inquiry.closed_by = "admin"

        # Add closing message if reason provided
        if reason:
            new_message = InquiryMessage(
                inquiry_id=inquiry_id,
                sender_type="admin",
                sender_id=admin.id,
                message_text=f"[АРЬЯ] Обращение закрыто: {reason}",
                created_at=datetime.now(UTC),
            )
            self.session.add(new_message)

        await self.session.commit()

        # Get user info
        user_info = "Неизвестен"
        if inquiry.user:
            user_info = (
                f"@{inquiry.user.username}"
                if inquiry.user.username
                else f"ID:{inquiry.user.telegram_id}"
            )

        logger.info(
            f"AI INQUIRIES: Admin {admin.telegram_id} closed "
            f"inquiry {inquiry_id}: {reason or 'no reason'}"
        )

        return {
            "success": True,
            "inquiry_id": inquiry_id,
            "user": user_info,
            "reason": reason,
            "admin": f"@{admin.username}" if admin.username else str(admin.telegram_id),
            "message": f"✅ Обращение #{inquiry_id} закрыто"
        }
