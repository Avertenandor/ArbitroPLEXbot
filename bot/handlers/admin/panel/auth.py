"""
Admin Authentication Handler

Handles master key input and admin authentication for accessing the admin panel.
This module is responsible for:
- Master key verification
- Admin session creation
- State restoration after authentication
- Redirection to intended admin menu after successful login
"""

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.services.admin_service import AdminService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_keyboard
from bot.states.admin_states import AdminStates


router = Router(name="admin_panel_auth")


async def get_admin_and_super_status(
    session: AsyncSession,
    telegram_id: int | None,
    data: dict[str, Any],
) -> tuple[Admin | None, bool]:
    """
    Get admin object and super_admin status.

    Args:
        session: Database session
        telegram_id: Telegram user ID
        data: Handler data dict

    Returns:
        Tuple of (Admin object or None, is_super_admin bool)
    """
    admin: Admin | None = data.get("admin")
    if not admin and telegram_id:
        # If admin not in data (e.g., before master key auth), fetch from DB
        admin_service = AdminService(session)
        admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    is_super_admin = admin.is_super_admin if admin else False
    return admin, is_super_admin


@router.message(AdminStates.awaiting_master_key_input)
async def handle_master_key_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle master key input for admin authentication.

    Args:
        message: Telegram message with master key
        session: Database session
        state: FSM context
        **data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        await message.answer("❌ Не удалось определить пользователя")
        return

    master_key = message.text.strip() if message.text else ""

    if not master_key:
        await message.answer("❌ Мастер-ключ не может быть пустым")
        return

    # Authenticate admin
    redis_client = data.get("redis_client")
    admin_service = AdminService(session, redis_client=redis_client)
    session_obj, admin_obj, error = await admin_service.login(
        telegram_id=telegram_id,
        master_key=master_key,
        ip_address=None,  # Telegram doesn't provide IP
        user_agent=None,  # Telegram doesn't provide user agent
    )

    if error or not session_obj or not admin_obj:
        error_msg = (
            f"❌ {error or 'Ошибка аутентификации'}\n\n"
            "Попробуйте ввести мастер-ключ еще раз:"
        )
        await message.answer(
            error_msg,
            parse_mode="Markdown",
        )
        return

    # Save session token in FSM state
    await state.update_data(admin_session_token=session_obj.session_token)

    # Restore previous state if it exists
    state_data = await state.get_data()
    previous_state = state_data.get("auth_previous_state")
    redirect_message_text = state_data.get("auth_redirect_message")

    if previous_state:
        await state.set_state(previous_state)
        # Clean up
        await state.update_data(
            auth_previous_state=None, auth_redirect_message=None
        )

        logger.info(
            f"Admin {telegram_id} authenticated successfully, "
            f"restoring state {previous_state}"
        )

        success_msg = (
            "✅ **Аутентификация успешна!**\n\n"
            "Вы вернулись в предыдущее меню. "
            "Пожалуйста, повторите ваше действие."
        )
        await message.answer(
            success_msg,
            parse_mode="Markdown",
        )
        return

    # Attempt to redirect based on button text if no state was restored
    if redirect_message_text:
        logger.info(
            f"Attempting to redirect admin {telegram_id} "
            f"to '{redirect_message_text}'"
        )
        # Clean up
        await state.update_data(auth_redirect_message=None)

        # Menu handlers mapping: button_text -> (handler_function, requires_state)
        # Using lazy imports to avoid circular dependencies
        menu_handlers = {
            "🆘 Техподдержка": (
                "bot.handlers.admin.support",
                "handle_admin_support_menu",
                True,
            ),
            "💰 Управление депозитами": (
                "bot.handlers.admin.deposit_management",
                "show_deposit_management_menu",
                False,
            ),
            "⚙️ Настроить уровни депозитов": (
                "bot.handlers.admin.deposit_settings",
                "show_deposit_settings",
                False,
            ),
            "👥 Управление админами": (
                "bot.handlers.admin.admins",
                "show_admin_management",
                False,
            ),
            "🚫 Управление черным списком": (
                "bot.handlers.admin.blacklist",
                "show_blacklist",
                False,
            ),
            "🔐 Управление кошельком": (
                "bot.handlers.admin.wallet_management",
                "show_wallet_dashboard",
                True,
            ),
            "💸 Заявки на вывод": (
                "bot.handlers.admin.panel.navigation",
                "handle_admin_withdrawals",
                False,
            ),
            "📢 Рассылка": (
                "bot.handlers.admin.broadcast",
                "handle_start_broadcast",
                True,
            ),
            "👥 Управление пользователями": (
                "bot.handlers.admin.panel.navigation",
                "handle_admin_users_menu",
                False,
            ),
            "📊 Статистика": (
                "bot.handlers.admin.panel.statistics",
                "handle_admin_stats",
                False,
            ),
            "🔑 Восстановление пароля": (
                "bot.handlers.admin.finpass_recovery",
                "show_recovery_requests",
                True,
            ),
            "📋 Логи действий": (
                "bot.handlers.admin.action_logs",
                "handle_action_logs",
                False,
            ),
            "⏰ Расписание задач": (
                "bot.handlers.admin.schedule_management",
                "show_schedule_management",
                True,
            ),
            "👑 Админ-панель": (
                None,
                None,
                None,
            ),  # Just continue to show admin panel below
        }

        # Special case: check for "Финансовая" in text
        handler_info = None
        if "Финансовая" in redirect_message_text:
            handler_info = (
                "bot.handlers.admin.financials",
                "show_financial_list",
                True,
            )
        else:
            handler_info = menu_handlers.get(redirect_message_text)

        if handler_info and handler_info[0] is not None:
            module_path, function_name, requires_state = handler_info
            # Dynamic import
            from importlib import import_module
            module = import_module(module_path)
            handler = getattr(module, function_name)

            # Call handler with appropriate parameters
            if requires_state:
                await handler(message, session, state, **data)
            else:
                await handler(message, session, **data)
            return
        elif redirect_message_text == "👑 Админ-панель":
            # Just continue to show admin panel below
            pass

    await state.set_state(None)  # Clear state

    logger.info(
        f"Admin {telegram_id} authenticated successfully, "
        f"session_id={session_obj.id}"
    )

    # Show admin panel
    text = """
👑 **Панель администратора**

Добро пожаловать в панель управления ArbitroPLEXbot Bot.

Выберите действие:
    """.strip()

    # Get admin and super_admin status
    telegram_id = message.from_user.id if message.from_user else None
    admin, is_super_admin = await get_admin_and_super_status(session, telegram_id, data)

    is_extended = admin.is_extended_admin if admin else False
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
            is_super_admin=is_super_admin,
            is_extended_admin=is_extended,
        ),
    )
