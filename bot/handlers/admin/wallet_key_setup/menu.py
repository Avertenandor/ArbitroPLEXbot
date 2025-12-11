"""
Wallet Menu Handlers.

Provides menu navigation for wallet management.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings

from .router import router


async def handle_wallet_menu(message: Message, state: FSMContext, **data: Any) -> None:
    """Show wallet management menu (Redirect to new dashboard)."""
    # Check admin permissions: only super admin can access this menu
    user = data.get("event_from_user") or message.from_user

    # Use super_admin_telegram_id as single source of truth
    if not user or user.id != settings.super_admin_telegram_id:
        await message.answer("❌ Команда доступна только главному администратору")
        return

    # Redirect to new dashboard
    from bot.handlers.admin.wallet_management import show_wallet_dashboard
    # Pass session=None as it is currently unused in show_wallet_dashboard
    await show_wallet_dashboard(message, None, state, **data)


@router.message(F.text == "📊 Статус кошельков")
async def handle_wallet_status(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show wallet status (redirect to new dashboard)."""
    from bot.handlers.admin.wallet_management import show_wallet_dashboard
    await show_wallet_dashboard(message, session, state, **data)


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(message: Message, session: AsyncSession, **data: Any):
    """Return to admin panel."""
    from bot.handlers.admin.panel import handle_admin_panel_button
    await handle_admin_panel_button(message, session, **data)
