"""
Admin authentication middleware.

Checks admin session and requires master key authentication for admin actions.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_service import AdminService
from bot.states.admin_states import AdminStates


class AdminAuthMiddleware(BaseMiddleware):
    """
    Admin authentication middleware.

    Checks for active admin session and requires master key if missing.
    Updates session activity on each admin action.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Check admin session and authenticate if needed.

        Args:
            handler: Next handler
            event: Telegram event
            data: Handler data

        Returns:
            Handler result
        """
        # Get required dependencies
        session, state, telegram_user = self._get_dependencies(event, data)
        if not session or not state or not telegram_user:
            return await handler(event, data)

        # Check if user is admin
        if not data.get("is_admin", False):
            return await handler(event, data)

        # Get and validate admin
        admin_service = AdminService(session)
        admin = await admin_service.get_admin_by_telegram_id(telegram_user.id)
        if not admin:
            logger.warning(
                f"User {telegram_user.id} marked as admin but not found in Admin table"
            )
            return await handler(event, data)

        # Check if admin is blocked
        if admin.is_blocked:
            await self._handle_blocked_admin(event, admin, telegram_user.id)
            return

        # Get current FSM state
        current_state = await state.get_state()

        # Allow master key input to proceed
        if current_state == AdminStates.awaiting_master_key_input:
            return await handler(event, data)

        # Get session token from FSM state
        state_data = await state.get_data()
        session_token = state_data.get("admin_session_token")

        # Require master key if no session token
        if not session_token:
            await self._require_master_key(event, state, current_state)
            return

        # Validate session token
        admin_obj, session_obj, error = await admin_service.validate_session(session_token)
        if error or not admin_obj or not session_obj:
            await self._require_master_key(event, state, current_state, error)
            return

        # Add admin data to context
        self._add_admin_data(data, admin_obj, session_obj, session_token)

        # Call next handler
        return await handler(event, data)

    def _get_dependencies(
        self, event: TelegramObject, data: dict[str, Any]
    ) -> tuple[AsyncSession | None, FSMContext | None, Any]:
        """
        Extract required dependencies from data.

        Args:
            event: Telegram event
            data: Handler data

        Returns:
            Tuple of (session, state, telegram_user)
        """
        session: AsyncSession = data.get("session")
        if not session:
            logger.error("No session in data - DatabaseMiddleware missing?")
            return None, None, None

        state: FSMContext = data.get("state")
        if not state:
            logger.error("No state in data - FSMContext missing?")
            return None, None, None

        telegram_user = self._get_telegram_user(event, data)
        return session, state, telegram_user

    def _get_telegram_user(self, event: TelegramObject, data: dict[str, Any]) -> Any:
        """
        Extract telegram user from event or data.

        Args:
            event: Telegram event
            data: Handler data

        Returns:
            Telegram user or None
        """
        telegram_user = data.get("event_from_user")
        if telegram_user:
            return telegram_user

        if isinstance(event, (Message, CallbackQuery)):
            return event.from_user

        return None

    async def _handle_blocked_admin(
        self, event: TelegramObject, admin: Any, telegram_id: int
    ) -> None:
        """
        Handle blocked admin access attempt.

        Args:
            event: Telegram event
            admin: Admin object
            telegram_id: Telegram user ID
        """
        logger.warning(
            f"R10-3: Blocked admin {admin.id} (telegram_id={telegram_id}) "
            f"attempted to access admin panel"
        )

        if isinstance(event, Message):
            await event.answer(
                "🚫 **Доступ запрещен**\n\n"
                "Ваш админ-аккаунт заблокирован из соображений безопасности.\n\n"
                "Обратитесь к супер-администратору для выяснения причин.",
                parse_mode="Markdown",
            )
        elif isinstance(event, CallbackQuery):
            await event.answer(
                "🚫 Доступ запрещен. Ваш админ-аккаунт заблокирован.",
                show_alert=True,
            )

    async def _require_master_key(
        self,
        event: TelegramObject,
        state: FSMContext,
        current_state: str | None,
        error: str | None = None,
    ) -> None:
        """
        Require master key authentication.

        Args:
            event: Telegram event
            state: FSM context
            current_state: Current FSM state
            error: Optional error message for invalid session
        """
        # Save current state to restore after auth
        if current_state != AdminStates.awaiting_master_key_input:
            await state.update_data(auth_previous_state=current_state)

            # Save redirect intent if message text is a navigation button
            if isinstance(event, Message) and event.text:
                await state.update_data(auth_redirect_message=event.text)

        await state.set_state(AdminStates.awaiting_master_key_input)

        if error:
            await state.update_data(admin_session_token=None)

        await self._send_auth_message(event, error)

    async def _send_auth_message(
        self, event: TelegramObject, error: str | None = None
    ) -> None:
        """
        Send authentication required message.

        Args:
            event: Telegram event
            error: Optional error message for invalid session
        """
        if isinstance(event, Message):
            if error:
                await event.answer(
                    f"❌ {error}\n\n"
                    "Введите мастер-ключ для повторной аутентификации:",
                    parse_mode="Markdown",
                )
            else:
                await event.answer(
                    "🔐 **Требуется аутентификация**\n\n"
                    "Для доступа к админ-панели введите мастер-ключ:",
                    parse_mode="Markdown",
                )
        elif isinstance(event, CallbackQuery):
            if error:
                await event.answer(f"❌ {error}")
            else:
                await event.answer("🔐 Требуется аутентификация. Введите мастер-ключ.")

    def _add_admin_data(
        self,
        data: dict[str, Any],
        admin_obj: Any,
        session_obj: Any,
        session_token: str,
    ) -> None:
        """
        Add admin data to handler context.

        Args:
            data: Handler data
            admin_obj: Admin object
            session_obj: Session object
            session_token: Session token
        """
        data["admin"] = admin_obj
        data["admin_session"] = session_obj
        data["admin_session_token"] = session_token
        data["is_super_admin"] = admin_obj.is_super_admin
        data["is_extended_admin"] = admin_obj.is_extended_admin
