"""AI Broadcast Service - allows ARIA to send messages to users."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot
from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appeal, User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository

"""NOTE: Access control

Per requirement: any active (non-blocked) admin can use broadcast tools via ARYA.
"""


class AIBroadcastService:
    """Service for ARIA to send messages and broadcasts."""

    def __init__(
        self,
        session: AsyncSession,
        bot: Bot,
        admin_telegram_id: int | None = None,
        admin_username: str | None = None,
    ):
        self.session = session
        self.bot = bot
        self.admin_telegram_id = admin_telegram_id
        self.admin_username = admin_username
        self.user_repo = UserRepository(session)

    async def _verify_admin(self) -> tuple[bool, str | None]:
        """Verify that the caller is an active (non-blocked) admin."""
        if not self.admin_telegram_id:
            return False, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return False, "❌ Администратор не найден или заблокирован"

        return True, None

    async def send_message_to_user(
        self,
        user_identifier: str | int,
        message_text: str,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Send a single message to a user.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            message_text: Message text to send
            parse_mode: Markdown or HTML

        Returns:
            Result dict with status
        """
        ok, err = await self._verify_admin()
        if not ok:
            logger.warning(f"BROADCAST DENIED: {err} (admin_id={self.admin_telegram_id})")
            return {"success": False, "error": err}

        try:
            # Find user
            user = await self._find_user(user_identifier)
            if not user:
                return {
                    "success": False,
                    "error": f"Пользователь '{user_identifier}' не найден",
                }

            # Send message
            await self.bot.send_message(
                user.telegram_id,
                message_text,
                parse_mode=parse_mode,
            )

            logger.info(
                f"ARIA (admin {self.admin_telegram_id}) sent message to user {user.telegram_id} (@{user.username})"
            )

            return {
                "success": True,
                "user_id": user.telegram_id,
                "username": user.username,
                "message": "Сообщение успешно отправлено",
            }

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "success": False,
                "error": "Ошибка отправки сообщения",
            }

    async def broadcast_to_group(
        self,
        group: str,
        message_text: str,
        limit: int = 100,
        parse_mode: str = "Markdown",
    ) -> dict[str, Any]:
        """
        Broadcast message to a group of users.

        Args:
            group: Group type:
                - "active_appeals" - users with open appeals
                - "active_deposits" - users with active deposits
                - "active_24h" - users active in last 24 hours
                - "all" - all users (careful!)
            message_text: Message to send
            limit: Max users to send to
            parse_mode: Markdown or HTML

        Returns:
            Result dict with stats
        """
        ok, err = await self._verify_admin()
        if not ok:
            logger.warning(
                f"BROADCAST DENIED: {err} (admin_id={self.admin_telegram_id}) attempted broadcast to group '{group}'"
            )
            return {"success": False, "error": err}

        try:
            # Get user IDs based on group
            user_ids = await self._get_users_by_group(group, limit)

            if not user_ids:
                return {
                    "success": False,
                    "error": f"Нет пользователей в группе '{group}'",
                    "total": 0,
                }

            # Send messages with rate limiting
            success = 0
            failed = 0
            failed_users = []

            for user_id in user_ids:
                try:
                    await self.bot.send_message(
                        user_id,
                        message_text,
                        parse_mode=parse_mode,
                    )
                    success += 1
                    # Rate limit: 20 msg/sec to avoid Telegram limits
                    await asyncio.sleep(0.05)
                except Exception as e:
                    failed += 1
                    failed_users.append({"user_id": user_id, "error": str(e)})

            logger.info(f"ARIA broadcast to '{group}': {success} sent, {failed} failed")

            return {
                "success": True,
                "group": group,
                "total": len(user_ids),
                "sent": success,
                "failed": failed,
                "failed_details": failed_users[:5] if failed_users else [],
                "message": f"Отправлено {success} из {len(user_ids)} сообщений",
            }

        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_users_list(
        self,
        group: str = "all",
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get list of users for preview before broadcast.

        Args:
            group: Group type (same as broadcast_to_group)
            limit: Max users to return

        Returns:
            List of users with details
        """
        try:
            users = await self._get_users_details_by_group(group, limit)

            return {
                "success": True,
                "group": group,
                "total": len(users),
                "users": users,
            }

        except Exception as e:
            logger.error(f"Get users list error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def invite_to_dialog(
        self,
        user_identifier: str | int,
        custom_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send personal invitation to dialog with ARIA.

        Args:
            user_identifier: @username, telegram_id, or ID:xxx
            custom_message: Optional custom message

        Returns:
            Result dict
        """
        user = await self._find_user(user_identifier)
        if not user:
            return {
                "success": False,
                "error": f"Пользователь '{user_identifier}' не найден",
            }

        # Default invitation message
        if custom_message:
            message = custom_message
        else:
            name = user.username or user.first_name or "друг"
            message = (
                f"👋 Привет, {name}!\n\n"
                f"Я **Арья** — AI-помощник ArbitroPLEX.\n\n"
                f"Заметила, что у тебя могут быть вопросы. "
                f"Я здесь, чтобы помочь!\n\n"
                f"Напиши мне прямо сейчас или нажми кнопку "
                f"**💬 Свободный диалог** в меню.\n\n"
                f"С удовольствием отвечу на любые вопросы! 🤗"
            )

        return await self.send_message_to_user(
            user.telegram_id,
            message,
        )

    async def mass_invite_to_dialog(
        self,
        group: str = "active_appeals",
        custom_message: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        Send invitations to dialog to a group of users.

        Args:
            group: Target group
            custom_message: Optional custom message template
            limit: Max invitations

        Returns:
            Result dict with stats
        """
        try:
            users = await self._get_users_details_by_group(group, limit)

            if not users:
                return {
                    "success": False,
                    "error": f"Нет пользователей в группе '{group}'",
                }

            success = 0
            failed = 0

            for user_data in users:
                name = user_data.get("username") or user_data.get("first_name") or "друг"

                if custom_message:
                    message = custom_message.replace("{name}", name)
                else:
                    message = (
                        f"👋 Привет, {name}!\n\n"
                        f"Я **Арья** — AI-помощник ArbitroPLEX.\n\n"
                        f"Хочу убедиться, что у тебя всё хорошо и "
                        f"ответить на любые вопросы.\n\n"
                        f"Напиши мне в **💬 Свободный диалог** — "
                        f"я на связи! 🤗"
                    )

                try:
                    await self.bot.send_message(
                        user_data["telegram_id"],
                        message,
                        parse_mode="Markdown",
                    )
                    success += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    failed += 1

            logger.info(f"ARIA mass invite to '{group}': {success} sent, {failed} failed")

            return {
                "success": True,
                "group": group,
                "total": len(users),
                "sent": success,
                "failed": failed,
                "message": f"Приглашения отправлены: {success} из {len(users)}",
            }

        except Exception as e:
            logger.error(f"Mass invite error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # ========== PRIVATE METHODS ==========

    async def _find_user(self, identifier: str | int) -> User | None:
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
            return await self.user_repo.get_by_telegram_id(int(identifier))

        # Try username without @
        return await self.user_repo.get_by_username(identifier)

    async def _get_users_by_group(self, group: str, limit: int) -> list[int]:
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
            stmt = select(User.telegram_id).where(User.last_activity >= cutoff).limit(limit)
        elif group == "active_7d":
            # Users active in last 7 days
            cutoff = now - timedelta(days=7)
            stmt = select(User.telegram_id).where(User.last_activity >= cutoff).limit(limit)
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

    async def _get_users_details_by_group(self, group: str, limit: int) -> list[dict]:
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
            stmt = select(User).where(User.last_activity >= cutoff).limit(limit)
        elif group == "active_7d":
            cutoff = now - timedelta(days=7)
            stmt = select(User).where(User.last_activity >= cutoff).limit(limit)
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
                "last_activity": u.last_activity.isoformat() if u.last_activity else None,
            }
            for u in users
        ]

    async def send_feedback_request(
        self,
        admin_identifier: str | int,
        topic: str,
        question: str,
    ) -> dict[str, Any]:
        """
        Send a feedback request to a specific admin.

        Args:
            admin_identifier: @username or telegram_id of admin
            topic: Topic of the feedback request
            question: Specific question to ask

        Returns:
            Result dict with status
        """
        from app.models import Admin

        try:
            # Find admin
            admin = await self._find_admin(admin_identifier)
            if not admin:
                return {
                    "success": False,
                    "error": f"Админ '{admin_identifier}' не найден",
                }

            # Format feedback request message
            message = (
                f"💬 **Запрос обратной связи от ARIA**\n\n"
                f"📋 **Тема:** {topic}\n\n"
                f"❓ **Вопрос:**\n{question}\n\n"
                f"_Пожалуйста, ответьте на это сообщение или нажмите '🤖 AI Помощник' "
                f"чтобы обсудить с ARIA._"
            )

            await self.bot.send_message(
                admin.telegram_id,
                message,
                parse_mode="Markdown",
            )

            logger.info(
                f"ARIA sent feedback request to admin {admin.telegram_id} (@{admin.username}) on topic: {topic}"
            )

            return {
                "success": True,
                "admin_id": admin.telegram_id,
                "admin_username": admin.username,
                "topic": topic,
                "message": f"Запрос отправлен @{admin.username}",
            }

        except Exception as e:
            logger.error(f"Failed to send feedback request: {e}")
            return {
                "success": False,
                "error": f"Ошибка отправки: {str(e)}",
            }

    async def broadcast_to_admins(
        self,
        message_text: str,
        request_feedback: bool = True,
    ) -> dict[str, Any]:
        """
        Broadcast message to all active admins.

        Args:
            message_text: Message to send
            request_feedback: Whether to add feedback prompt

        Returns:
            Result dict with stats
        """
        from sqlalchemy import select

        from app.models import Admin

        try:
            # Get all active admins
            stmt = select(Admin).where(Admin.is_active == True)  # noqa: E712
            result = await self.session.execute(stmt)
            admins = result.scalars().all()

            if not admins:
                return {
                    "success": False,
                    "error": "Нет активных админов",
                }

            # Add feedback prompt if requested
            if request_feedback:
                message_text += "\n\n💬 _Есть идеи или предложения? Нажмите '🤖 AI Помощник' чтобы обсудить с ARIA._"

            sent_count = 0
            failed_count = 0
            sent_to = []

            for admin in admins:
                try:
                    await self.bot.send_message(
                        admin.telegram_id,
                        message_text,
                        parse_mode="Markdown",
                    )
                    sent_count += 1
                    sent_to.append(f"@{admin.username}")
                    await asyncio.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to send to admin {admin.telegram_id}: {e}")
                    failed_count += 1

            logger.info(f"ARIA broadcast to {sent_count} admins: {', '.join(sent_to)}")

            return {
                "success": True,
                "sent": sent_count,
                "failed": failed_count,
                "admins": sent_to,
                "message": f"Отправлено {sent_count} админам",
            }

        except Exception as e:
            logger.error(f"Failed to broadcast to admins: {e}")
            return {
                "success": False,
                "error": f"Ошибка рассылки: {str(e)}",
            }

    async def _find_admin(self, identifier: str | int) -> Any:
        """Find admin by username or telegram_id."""
        from sqlalchemy import select

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
            stmt = select(Admin).where(Admin.telegram_id == telegram_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error finding admin: {e}")
            return None
