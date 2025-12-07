"""
Core menu handlers.

This module contains the main menu display and navigation handlers.
Handles main menu navigation - ONLY REPLY KEYBOARDS!
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.deposit import DepositService
from app.services.user_service import UserService
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

router = Router()


async def show_main_menu(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show main menu.

    Args:
        message: Message object
        session: Database session
        user: Current user
        state: FSM state
        **data: Handler data (includes is_admin from AuthMiddleware)
    """
    logger.info(f"[MENU] show_main_menu called for user {user.telegram_id} (@{user.username})")

    # Clear any active FSM state
    await state.clear()

    # Get blacklist status
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = await blacklist_repo.find_by_telegram_id(
        user.telegram_id
    )
    logger.info(
        f"[MENU] Blacklist entry for user {user.telegram_id}: "
        f"exists={blacklist_entry is not None}, "
        f"active={blacklist_entry.is_active if blacklist_entry else False}"
    )

    # Get is_admin from middleware data (set by AuthMiddleware)
    is_admin = data.get("is_admin", False)
    logger.info(
        f"[MENU] is_admin from data for user {user.telegram_id}: {is_admin}, "
        f"data keys: {list(data.keys())}"
    )

    # R13-3: Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Escape username for Markdown
    safe_username = escape_markdown(user.username) if user.username else _('common.user')

    # Get balance for quick view
    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)
    available = balance.get('available_balance', 0) if balance else 0

    # Get PLEX balance and calculate days
    from decimal import Decimal
    plex_balance = user.last_plex_balance or Decimal("0")
    required_daily = user.required_daily_plex

    # Calculate days (~X дней)
    if required_daily > 0:
        days = int(plex_balance / required_daily)
    else:
        days = 0

    # Get active deposits info
    deposit_service = DepositService(session)
    active_deposits = await deposit_service.get_active_deposits(user.id)
    
    # Build deposits summary section
    deposits_section = ""
    if active_deposits:
        total_deposited = sum(float(d.amount) for d in active_deposits)
        total_roi_paid = sum(float(d.roi_paid_amount or 0) for d in active_deposits)
        total_roi_cap = sum(float(d.roi_cap_amount or 0) for d in active_deposits)
        
        if total_roi_cap > 0:
            overall_progress = (total_roi_paid / total_roi_cap) * 100
        else:
            overall_progress = 0
        
        deposits_section = (
            f"📦 Депозит: `{format_usdt(total_deposited)} USDT`\n"
            f"📈 ROI: `{overall_progress:.1f}%` получено `{format_usdt(total_roi_paid)} USDT`\n"
        )
    else:
        deposits_section = "📦 Депозит: _нет активных_\n"

    text = (
        f"📊 *ГЛАВНОЕ МЕНЮ*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Добро пожаловать, {safe_username}\\!\n\n"
        f"💰 Баланс: `{available:.2f} USDT`\n"
        f"{deposits_section}"
        f"⚡ PLEX: `{float(plex_balance):.0f}` монет \\(\\~{days} дней\\)\n\n"
        f"Выберите раздел:"
    )

    logger.info(
        f"[MENU] Creating keyboard for user {user.telegram_id} with "
        f"is_admin={is_admin}, blacklist_entry={blacklist_entry is not None}"
    )
    keyboard = main_menu_reply_keyboard(
        user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
    )
    logger.info(f"[MENU] Sending main menu to user {user.telegram_id}")

    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    logger.info(f"[MENU] Main menu sent successfully to user {user.telegram_id}")


@router.message(F.text.in_({
    "📊 Главное меню",
    "⬅ Назад",
    "⏭ Пропустить",  # Registration skip (leftover keyboard)
    "⏭️ Пропустить",  # Same with FE0F
    "✅ Да, оставить контакты",  # Registration contacts (leftover keyboard)
}))
async def handle_main_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle main menu button."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] handle_main_menu called for user {telegram_id}, text: {message.text}")

    user: User | None = data.get("user")
    is_admin = data.get("is_admin")
    logger.info(f"[MENU] User from data: {user.id if user else None}, is_admin={is_admin}, data keys: {list(data.keys())}")

    if not user:
        # Если по какой-то причине DI не предоставил user, просто очистим
        # состояние и покажем базовое меню без учёта статусов.
        logger.warning(f"[MENU] No user in data for telegram_id {telegram_id}, using fallback")
        await state.clear()
        is_admin = data.get("is_admin", False)
        logger.info(f"[MENU] Fallback menu with is_admin={is_admin}")
        await message.answer(
            "📊 *ГЛАВНОЕ МЕНЮ*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Выберите раздел:",
            reply_markup=main_menu_reply_keyboard(
                user=None, blacklist_entry=None, is_admin=is_admin
            ),
            parse_mode="Markdown",
        )
        return
    logger.info(f"[MENU] Calling show_main_menu for user {user.telegram_id}")

    # Create safe data copy and remove arguments that are passed positionally
    safe_data = data.copy()
    safe_data.pop('user', None)
    safe_data.pop('state', None)
    safe_data.pop('session', None)  # session is also passed positionally

    await show_main_menu(message, session, user, state, **safe_data)
