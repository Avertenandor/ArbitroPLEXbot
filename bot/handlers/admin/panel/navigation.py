"""
Admin Panel Navigation Handlers

Handlers for navigating between admin panel menus and submenus:
- Wallet management
- Blacklist management
- User management
- Withdrawal requests
- Deposit settings
- Deposit management
- Admin management
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_users_keyboard, get_admin_keyboard_from_data
from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router(name="admin_panel_navigation")


@router.message(F.text == "🔐 Управление кошельком")
async def handle_admin_wallet_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle wallet management menu from admin panel."""
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    # Redirect to wallet dashboard
    from bot.handlers.admin.wallet_management import show_wallet_dashboard

    await show_wallet_dashboard(message, session, state, **data)


@router.message(F.text == "🚫 Управление черным списком")
async def handle_admin_blacklist_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to blacklist management."""
    from bot.handlers.admin.blacklist import show_blacklist

    await show_blacklist(message, session, **data)


@router.message(F.text == "👥 Управление пользователями")
async def handle_admin_users_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show admin users management menu"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    text = """👥 **Управление пользователями**

Выберите действие:"""

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_users_keyboard(),
    )


@router.message(F.text == "💸 Заявки на вывод")
async def handle_admin_withdrawals(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to withdrawals submenu with full functionality."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Redirect to the detailed withdrawals handler
    from bot.handlers.admin.withdrawals import handle_pending_withdrawals

    await handle_pending_withdrawals(message, session, **data)


@router.message(F.text == "⚙️ Настроить уровни депозитов")
async def handle_admin_deposit_settings(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to deposit settings management (legacy)."""
    from bot.handlers.admin.deposit_settings.display import (
        show_deposit_settings,
    )

    await show_deposit_settings(message, session, **data)


@router.message(F.text == "💰 Управление депозитами")
async def handle_admin_deposit_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to deposit management."""
    from bot.handlers.admin.deposit_management import (
        show_deposit_management_menu,
    )

    await show_deposit_management_menu(message, session, **data)


@router.message(F.text == "👥 Управление админами")
async def handle_admin_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to admin management."""
    from bot.handlers.admin.admins import show_admin_management

    await show_admin_management(message, session, **data)


@router.message(StateFilter(None), F.text == "❌ Отмена")
async def handle_global_admin_cancel(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Глобальный обработчик отмены для админов без активного FSM-состояния.

    Если админ нажимает "❌ Отмена" вне каких-либо шагов диалога,
    возвращаем его в главное админ-меню, сохраняя admin_session_token.
    """
    # Обрабатываем только если это действительно админский контекст
    if not data.get("is_admin") and not data.get("admin"):
        return

    await clear_state_preserve_admin_token(state)
    await message.answer(
        "👑 Админ-панель. Выберите раздел:",
        reply_markup=get_admin_keyboard_from_data(data),
    )
