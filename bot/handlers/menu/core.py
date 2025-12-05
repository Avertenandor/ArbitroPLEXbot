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
from app.services.user_service import UserService
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard
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

    text = (
        f"{_('menu.main')}\n\n"
        f"{_('common.welcome_user', username=safe_username)}\n"
        f"💰 Баланс: `{available:.2f} USDT`\n\n"
        f"{_('common.choose_action')}\n\n"
        f"🐰 Партнер: [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)"
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
            "📊 *Главное меню*\n\nВыберите действие:",
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
