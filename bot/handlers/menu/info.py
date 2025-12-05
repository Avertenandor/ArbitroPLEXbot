"""
Information page handlers.

This module contains handlers for displaying informational pages like rules,
ecosystem tools, and partner information.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from bot.constants.rules import RULES_FULL_TEXT
from bot.keyboards.reply import main_menu_reply_keyboard

router = Router()


@router.message(StateFilter('*'), F.text.in_({"🐰 Купить кролика", "🐰 DEXRabbit"}))
async def show_rabbit_partner(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show partner rabbit farm info."""
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    text = (
        "🐰 **Токенизированная ферма кроликов**\n\n"
        "Для работы в ArbitroPLEXbot каждый пользователь должен быть "
        "владельцем **минимум одного кролика** на ферме наших партнеров.\n\n"
        "**DEXRabbit** — это:\n"
        "• Покупка и удалённое содержание кроликов на ферме\n"
        "• Работа с USDT\n"
        "• Маркетплейс перепродаж\n"
        "• Реферальная программа 3×5%\n\n"
        "⚠️ **Это обязательное условие для работы в нашей экосистеме!**"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🐰 Перейти к покупке кролика",
            url="https://t.me/dexrabbit_bot?start=ref_9"
        )],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button
    await message.answer(
        "⬅️ Для возврата в меню нажмите кнопку ниже:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text == "📋 Правила")
async def show_rules(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show platform rules."""
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    await message.answer(
        RULES_FULL_TEXT,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в главное меню:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text.in_({"🌐 Инструменты нашей экосистемы", "🌐 Экосистема"}))
async def show_ecosystem_tools(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show ecosystem tools menu."""
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    text = (
        "🌐 **Инструменты нашей экосистемы**\n\n"
        "Все проекты и сервисы нашей крипто-фиатной экосистемы "
        "на базе монеты **PLEX**:\n\n"
        "Нажмите на интересующий вас проект для перехода:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤖 ArbitroPLEXbot — Торговый бот",
            url="https://arbitrage-bot.com/"
        )],
        [InlineKeyboardButton(
            text="🐰 DEXRabbit — Ферма кроликов",
            url="https://xn--80apagbbfxgmuj4j.site/"
        )],
        [InlineKeyboardButton(
            text="👑 RoyalKeta — Premium сервис",
            url="https://royalketa.com/"
        )],
        [InlineKeyboardButton(
            text="🎬 FreeTube — Видео платформа",
            url="https://freetube.online/"
        )],
        [InlineKeyboardButton(
            text="🛒 BestTrade Store — Магазин ботов",
            url="https://best-trade.store/bots/"
        )],
        [InlineKeyboardButton(
            text="📊 DataPLEX — Аналитика",
            url="https://data-plex.net/"
        )],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в главное меню:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )
