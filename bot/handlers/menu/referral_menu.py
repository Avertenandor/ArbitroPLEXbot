"""
Referral menu handlers.

This module contains handlers for displaying the referral menu with stats and share options.
"""

from typing import Any
from urllib.parse import quote

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.user import User
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from bot.keyboards.reply import referral_keyboard
from bot.utils.formatters import format_usdt
from bot.utils.user_loader import UserLoader


router = Router()


@router.message(StateFilter('*'), F.text == "👥 Рефералы")
async def show_referral_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show referral menu with quick stats and link."""
    telegram_id = message.from_user.id if message.from_user else None
    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    user_service = UserService(session)
    referral_service = ReferralService(session)

    bot_username = settings.telegram_bot_username
    referral_link = user_service.generate_referral_link(user, bot_username)

    # Get quick stats
    stats = await referral_service.get_referral_stats(user.id)
    daily = await referral_service.get_daily_earnings_stats(user.id, days=1)
    today_earned = daily.get("today_earned", 0)

    total_referrals = (
        stats['direct_referrals'] +
        stats['level2_referrals'] +
        stats['level3_referrals']
    )

    # Build welcome screen with stats
    text = (
        "👥 *Партнёрская программа ArbitroPLEX*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Ваша ссылка:*\n`{referral_link}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 *Ваша статистика:*\n"
        f"👥 Всего партнёров: *{total_referrals}*\n"
        f"💰 Заработано всего: *{format_usdt(stats['total_earned'])} USDT*\n"
        f"🌟 Сегодня: *{format_usdt(today_earned)} USDT*\n\n"
        "💎 *Комиссии:*\n"
        "├ 1 уровень: *5%* от депозитов и дохода\n"
        "├ 2 уровень: *5%* от депозитов и дохода\n"
        "└ 3 уровень: *5%* от депозитов и дохода\n\n"
        "💡 _Приглашайте друзей и получайте пассивный доход!_"
    )

    # Quick share button
    share_text = (
        "🚀 Присоединяйся к ArbitroPLEX!\n\n"
        "💰 Зарабатывай от 30% до 72% в сутки\n"
        "👥 3-уровневая реферальная программа (5%+5%+5%)\n\n"
        f"Регистрируйся: {referral_link}"
    )
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📤 Поделиться", url=share_url),
            InlineKeyboardButton(text="📋 Копировать", callback_data="copy_ref_link"),
        ],
    ])

    await message.answer(
        text, reply_markup=referral_keyboard(), parse_mode="Markdown"
    )

    # Send share buttons
    await message.answer(
        "⬇️ *Быстрые действия:*",
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )
