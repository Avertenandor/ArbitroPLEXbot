"""
Referral Promo Materials Module - REPLY AND INLINE KEYBOARDS!

Handles promo materials display including QR code and ready-made texts.
This module contains:
- Handler for viewing and sharing promo materials
- Ready-made promotional texts for different platforms
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message, URLInputFile
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
        "💰 Доход 30-72% в СУТКИ\n"
        "⚡ AI-арбитраж криптовалют 24/7\n"
        "👥 3-уровневая партнёрка (5%+5%+5%)\n"
        "🔒 Прозрачно и автоматически\n\n"
        f"Старт: {referral_link}\n"
        "```"
    )

    promo2 = (
        "📸 *Для Instagram/Stories:*\n"
        "```\n"
        "💎 До 72% прибыли в СУТКИ!\n\n"
        "🤖 AI-арбитраж с ArbitroPLEX\n"
        "📈 Автоматический заработок 24/7\n"
        "💰 Минимум — всего $10\n\n"
        "Ссылка в профиле 👆\n"
        "```"
    )

    promo3 = (
        "🐦 *Короткий текст:*\n"
        f"```\n"
        f"ArbitroPLEX — AI-арбитраж крипты 🤖\n"
        f"30-72% в сутки! Старт от $10\n"
        f"Начать: {referral_link}\n"
        "```"
    )

    promo4 = (
        "🔥 *Для YouTube/TikTok:*\n"
        "```\n"
        "💸 Как я зарабатываю на крипте без риска?\n\n"
        "ArbitroPLEX — бот для AI-арбитража\n"
        "✅ До 72% прибыли в сутки\n"
        "✅ Работает 24/7 автоматически\n"
        "✅ Вывод в любое время\n\n"
        f"Ссылка: {referral_link}\n"
        "```"
    )

    text += promo1 + "\n\n" + promo2 + "\n\n" + promo3 + "\n\n" + promo4 + "\n\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 _Нажмите на текст чтобы скопировать_"
    )

    # QR code URL (generates QR via external service)
    qr_url = (
        f"https://api.qrserver.com/v1/create-qr-code/"
        f"?size=300x300&data={referral_link}"
    )

    # Send promo texts first
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )

    # Send QR code as photo with clickable link below
    qr_caption = (
        f"📱 *Ваш QR-код для приглашения*\n\n"
        f"🔗 Ссылка: {referral_link}\n\n"
        f"_Нажмите на ссылку чтобы скопировать_"
    )

    await message.answer_photo(
        photo=URLInputFile(qr_url, filename="qr_code.png"),
        caption=qr_caption,
        parse_mode="Markdown",
    )
