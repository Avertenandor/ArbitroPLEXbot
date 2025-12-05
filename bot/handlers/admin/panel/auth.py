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
from bot.keyboards.reply import admin_keyboard, get_admin_keyboard_from_data
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
        await message.answer(
            f"❌ {error or 'Ошибка аутентификации'}\n\n"
            "Попробуйте ввести мастер-ключ еще раз:",
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
        await state.update_data(auth_previous_state=None, auth_redirect_message=None)

        logger.info(
            f"Admin {telegram_id} authenticated successfully, "
            f"restoring state {previous_state}"
        )

        await message.answer(
            "✅ **Аутентификация успешна!**\n\n"
            "Вы вернулись в предыдущее меню. Пожалуйста, повторите ваше действие.",
            parse_mode="Markdown",
        )
        return

    # Attempt to redirect based on button text if no state was restored
    if redirect_message_text:
        logger.info(f"Attempting to redirect admin {telegram_id} to '{redirect_message_text}'")
        # Clean up
        await state.update_data(auth_redirect_message=None)

        # Route to specific handlers manually based on saved text
        # Note: Don't modify message.text - aiogram Message objects are frozen
        if redirect_message_text == "🆘 Техподдержка":
            from bot.handlers.admin.support import handle_admin_support_menu
            await handle_admin_support_menu(message, state, **data)
            return
        elif redirect_message_text == "💰 Управление депозитами":
            from bot.handlers.admin.deposit_management import (
                show_deposit_management_menu,
            )
            await show_deposit_management_menu(message, session, **data)
            return
        elif redirect_message_text == "⚙️ Настроить уровни депозитов":
            from bot.handlers.admin.deposit_settings import (
                show_deposit_settings,
            )
            await show_deposit_settings(message, session, **data)
            return
        elif redirect_message_text == "👥 Управление админами":
            from bot.handlers.admin.admins import show_admin_management
            await show_admin_management(message, session, **data)
            return
        elif redirect_message_text == "🚫 Управление черным списком":
            from bot.handlers.admin.blacklist import show_blacklist
            await show_blacklist(message, session, **data)
            return
        elif redirect_message_text == "🔐 Управление кошельком":
            from bot.handlers.admin.wallet_management import (
                show_wallet_dashboard,
            )
            await show_wallet_dashboard(message, session, state, **data)
            return
        elif redirect_message_text == "💸 Заявки на вывод":
            from bot.handlers.admin.panel.navigation import handle_admin_withdrawals
            await handle_admin_withdrawals(message, session, **data)
            return
        elif redirect_message_text == "📢 Рассылка":
            from bot.handlers.admin.broadcast import handle_broadcast_menu
            await handle_broadcast_menu(message, session, **data)
            return
        elif redirect_message_text == "👥 Управление пользователями":
            from bot.handlers.admin.panel.navigation import handle_admin_users_menu
            await handle_admin_users_menu(message, session, **data)
            return
        elif redirect_message_text == "📊 Статистика":
            from bot.handlers.admin.panel.statistics import handle_admin_stats
            await handle_admin_stats(message, session, **data)
            return
        elif redirect_message_text == "🔑 Восстановление пароля":
            from bot.handlers.admin.finpass_recovery import (
                show_recovery_requests,
            )
            await show_recovery_requests(message, session, state, **data)
            return
        elif redirect_message_text and "Финансовая" in redirect_message_text:
            from bot.handlers.admin.financials import show_financial_list
            await show_financial_list(message, session, state, **data)
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
    admin, is_super_admin = await get_admin_and_super_status(
        session, telegram_id, data
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
            is_super_admin=is_super_admin,
            is_extended_admin=admin.is_extended_admin if admin else False
        ),
    )
