"""
Referral Link Module - REPLY AND INLINE KEYBOARDS!

Handles referral link sharing and copying functionality.
This module contains:
- Callback handler for copying referral link (inline button)
- Message handler for copying referral link (reply button)
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from bot.keyboards.reply import referral_keyboard


router = Router(name="referral_link")


@router.callback_query(F.data == "copy_ref_link")
async def handle_copy_ref_link(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Handle copy referral link button - send link as copyable message."""
    from aiogram import Bot

    from app.config.settings import settings

    user_service = UserService(session)

    bot_username = settings.telegram_bot_username
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    referral_link = user_service.generate_referral_link(user, bot_username)

    await callback.answer()
    await callback.message.answer(
        f"📋 *Ваша реферальная ссылка:*\n\n"
        f"`{referral_link}`\n\n"
        f"👆 Нажмите на ссылку чтобы скопировать",
        parse_mode="Markdown",
    )


@router.message(F.text == "📋 Скопировать ссылку")
async def handle_copy_link_button(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Handle copy referral link reply button - instant copy."""
    from aiogram import Bot

    from app.config.settings import settings

    user_service = UserService(session)

    bot_username = settings.telegram_bot_username
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    referral_link = user_service.generate_referral_link(user, bot_username)

    await message.answer(
        f"📋 *Ваша реферальная ссылка:*\n\n"
        f"`{referral_link}`\n\n"
        f"👆 *Нажмите на ссылку чтобы скопировать*\n\n"
        f"💡 Отправьте её друзьям и получайте *5%* с их депозитов и дохода!",
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )
