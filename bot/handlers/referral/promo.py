"""
Referral Promo Materials Module - REPLY AND INLINE KEYBOARDS!

Handles promo materials display including QR code and ready-made texts.
This module contains:
- Handler for viewing and sharing promo materials
- Ready-made promotional texts for different platforms
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from bot.keyboards.reply import referral_keyboard

router = Router(name="referral_promo")


@router.message(F.text == "📢 Промо-материалы")
async def handle_promo_materials(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Show promo materials including QR code and ready texts."""
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

    text = (
        "📢 *Промо-материалы*\n\n"
        "Используйте готовые тексты для привлечения партнёров:\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Ready-made texts
    promo1 = (
        "📱 *Для Telegram/WhatsApp:*\n"
        "```\n"
        "🚀 Зарабатывай с ArbitroPLEX!\n\n"
        "💰 Доход 0.8-1.2% в ДЕНЬ\n"
        "👥 3-уровневая партнёрка (5%+5%+5%)\n"
        "🔒 Безопасно и прозрачно\n\n"
        f"Регистрируйся: {referral_link}\n"
        "```"
    )

    promo2 = (
        "📸 *Для Instagram/Stories:*\n"
        "```\n"
        "💎 Пассивный доход каждый день!\n\n"
        "Арбитраж криптовалют с ArbitroPLEX\n"
        "До 36% в месяц 📈\n\n"
        "Ссылка в профиле 👆\n"
        "```"
    )

    promo3 = (
        "🐦 *Короткий текст:*\n"
        f"```\n"
        f"ArbitroPLEX — зарабатывай на крипте!\n"
        f"Регистрация: {referral_link}\n"
        "```"
    )

    text += promo1 + "\n\n" + promo2 + "\n\n" + promo3 + "\n\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 *Ваша ссылка:*\n`{referral_link}`\n\n"
        "💡 _Нажмите на текст чтобы скопировать_"
    )

    # QR code button (generates QR via external service)
    qr_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={referral_link}"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📱 Получить QR-код",
                url=qr_url,
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Копировать ссылку",
                callback_data="copy_ref_link",
            ),
        ],
    ])

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )

    await message.answer(
        "⬇️ *Дополнительно:*",
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )
