"""
Referral Statistics Module - REPLY KEYBOARDS ONLY!

Handles referral statistics and earnings display.
This module contains:
- Handler for viewing earnings with pending/paid breakdown
- Handler for comprehensive referral statistics with link sharing
- Analytics handler for detailed performance metrics
"""

from typing import Any
from urllib.parse import quote

from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from bot.keyboards.reply import referral_keyboard
from bot.utils.constants import REFERRAL_RATES
from bot.utils.formatters import format_usdt

router = Router(name="referral_stats")


@router.message(F.text == "💰 Мой заработок")
async def handle_my_earnings(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show user's referral earnings."""
    referral_service = ReferralService(session)

    # Get referral stats
    stats = await referral_service.get_referral_stats(user.id)

    # R4-6: Check for zero earnings
    total_earned = stats.get('total_earned', 0)
    if total_earned == 0:
        text = (
            "💰 *Мой заработок*\n\n"
            "У вас пока нет реферальных начислений.\n\n"
            "💡 *Совет:* Начните строить свою команду! "
            "Ссылку можно найти в разделе "
            "\"📊 Статистика рефералов\"."
        )
        await message.answer(
            text, parse_mode="Markdown", reply_markup=referral_keyboard()
        )
        return

    # Get pending earnings
    result = await referral_service.get_pending_earnings(
        user.id, page=1, limit=10
    )
    earnings = result["earnings"]
    total_amount = result["total_amount"]

    text = (
        f"💰 *Мой заработок*\n\n"
        f"*Доходы:*\n"
        f"💵 Всего заработано: *{format_usdt(stats['total_earned'])} USDT*\n"
        f"⏳ Ожидает выплаты: "
        f"*{format_usdt(stats['pending_earnings'])} USDT*\n"
        f"✅ Выплачено: *{format_usdt(stats['paid_earnings'])} USDT*\n\n"
    )

    if earnings:
        text += "*Последние выплаты:*\n"
        for earning in earnings[:5]:
            date = earning["created_at"].strftime("%d.%m.%Y")
            emoji = "✅" if earning["paid"] else "⏳"
            status = 'Выплачено' if earning['paid'] else 'Ожидает'
            text += (
                f"{emoji} {format_usdt(earning['amount'])} USDT\n"
                f"   Дата: {date}\n"
                f"   Статус: {status}\n\n"
            )

        if total_amount > 0:
            text += f"💰 Всего ожидает: *{format_usdt(total_amount)} USDT*\n"
    else:
        text += "У вас пока нет ожидающих выплат."

    await message.answer(
        text, parse_mode="Markdown", reply_markup=referral_keyboard()
    )


@router.message(F.text == "📊 Статистика рефералов")
async def handle_referral_stats(
    message: Message,
    session: AsyncSession,
    user: User,
    **data: Any,
) -> None:
    """Show comprehensive referral statistics."""
    from aiogram import Bot

    from app.config.settings import settings

    referral_service = ReferralService(session)
    user_service = UserService(session)

    # Get referral stats
    stats = await referral_service.get_referral_stats(user.id)

    # Get today's earnings
    daily_stats = await referral_service.get_daily_earnings_stats(user.id, days=1)
    today_earned = daily_stats.get("today_earned", 0)

    # Get bot info for referral link
    bot_username = settings.telegram_bot_username
    # Fallback: get from bot if not in settings
    if not bot_username:
        bot: Bot = data.get("bot")
        if bot:
            bot_info = await bot.get_me()
            bot_username = bot_info.username

    # Generate referral link (method now handles referral_code internally)
    referral_link = user_service.generate_referral_link(user, bot_username)

    # Get user position in leaderboard
    user_position = await referral_service.get_user_leaderboard_position(
        user.id
    )

    text = (
        f"📊 *Статистика рефералов*\n\n"
        f"*Ваша реферальная ссылка:*\n"
        f"`{referral_link}`\n\n"
        f"*Статистика:*\n"
        f"👥 Прямые партнеры: *{stats['direct_referrals']}*\n"
        f"👥 Уровень 2: *{stats['level2_referrals']}*\n"
        f"👥 Уровень 3: *{stats['level3_referrals']}*\n\n"
        f"*Доходы:*\n"
        f"🌟 *Сегодня: {format_usdt(today_earned)} USDT*\n"
        f"💵 Всего заработано: *{format_usdt(stats['total_earned'])} USDT*\n"
        f"⏳ Ожидает выплаты: "
        f"*{format_usdt(stats['pending_earnings'])} USDT*\n"
        f"✅ Выплачено: *{format_usdt(stats['paid_earnings'])} USDT*\n\n"
    )

    # Add leaderboard position if available
    referral_rank = user_position.get("referral_rank")
    earnings_rank = user_position.get("earnings_rank")
    total_users = user_position.get("total_users", 0)

    if referral_rank or earnings_rank:
        text += "*Ваша позиция в рейтинге:*\n"
        if referral_rank:
            text += f"📊 По рефералам: *{referral_rank}* из {total_users}\n"
        if earnings_rank:
            text += f"💰 По заработку: *{earnings_rank}* из {total_users}\n"
        text += "\n"

    text += (
        f"*Комиссии (от депозитов и дохода):*\n"
        f"• Уровень 1: *{int(REFERRAL_RATES[1] * 100)}%* "
        f"от прямых партнеров\n"
        f"• Уровень 2: *{int(REFERRAL_RATES[2] * 100)}%* "
        f"от партнеров 2-го уровня\n"
        f"• Уровень 3: *{int(REFERRAL_RATES[3] * 100)}%* "
        f"от партнеров 3-го уровня\n\n"
        f"💡 Приглашайте больше друзей и увеличивайте доход!"
    )

    # Create inline keyboard with share button
    share_text = (
        "🚀 Присоединяйся к ArbitroPLEX!\n\n"
        "💰 Зарабатывай от 0.8% до 1.2% в день\n"
        "👥 3-уровневая реферальная программа\n\n"
        f"Регистрируйся по ссылке: {referral_link}"
    )
    share_url = (
        f"https://t.me/share/url?url={quote(referral_link)}"
        f"&text={quote(share_text)}"
    )

    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Поделиться ссылкой",
                url=share_url,
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Копировать ссылку",
                callback_data="copy_ref_link",
            )
        ],
    ])

    await message.answer(
        text, parse_mode="Markdown", reply_markup=referral_keyboard()
    )

    # Send inline keyboard separately for share functionality
    await message.answer(
        "📤 *Поделитесь своей ссылкой:*",
        parse_mode="Markdown",
        reply_markup=inline_kb,
    )


@router.message(F.text == "📈 Аналитика")
async def handle_referral_analytics(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show detailed referral analytics."""
    referral_service = ReferralService(session)

    # Get all analytics data
    daily_stats = await referral_service.get_daily_earnings_stats(user.id, days=7)
    conversion_stats = await referral_service.get_referral_conversion_stats(user.id)
    activity_stats = await referral_service.get_referral_activity_stats(user.id)

    # Build text
    text = "📈 *Аналитика партнёрской программы*\n\n"

    # === Daily earnings chart ===
    text += "📊 *Заработок за последние 7 дней:*\n"

    if daily_stats["daily_stats"]:
        # Simple ASCII bar chart
        max_amount = max(
            (d["amount"] for d in daily_stats["daily_stats"]),
            default=0
        )

        for day_stat in daily_stats["daily_stats"][:7]:
            date_str = day_stat["date"].strftime("%d.%m")
            amount = day_stat["amount"]
            count = day_stat["count"]

            # Create bar
            if max_amount > 0:
                bar_len = int((float(amount) / float(max_amount)) * 8)
            else:
                bar_len = 0
            bar = "█" * bar_len + "░" * (8 - bar_len)

            text += f"`{date_str}` {bar} *{format_usdt(amount)}* ({count})\n"

        text += (
            f"\n💰 Итого за период: *{format_usdt(daily_stats['total_period'])} USDT*\n"
            f"📅 Сегодня: *{format_usdt(daily_stats['today_earned'])} USDT*\n"
            f"📊 В среднем/день: *{format_usdt(daily_stats['average_daily'])} USDT*\n"
        )
    else:
        text += "_Нет данных за этот период_\n"

    text += "\n"

    # === Conversion stats ===
    text += "🎯 *Конверсия рефералов:*\n"
    text += f"👥 Всего прямых рефералов: *{conversion_stats['total_referrals']}*\n"
    text += (
        f"✅ С депозитами: *{conversion_stats['referrals_with_deposits']}* "
        f"({conversion_stats['conversion_rate']:.1f}%)\n"
    )
    if conversion_stats['deposit_count'] > 0:
        total_dep = format_usdt(conversion_stats['total_deposits_amount'])
        avg_dep = format_usdt(conversion_stats['average_deposit'])
        text += (
            f"💵 Общий объём депозитов: *{total_dep} USDT*\n"
            f"📊 Средний депозит: *{avg_dep} USDT*\n"
        )
    text += "\n"

    # === Activity stats ===
    text += "🔥 *Активность рефералов (30 дней):*\n"
    text += f"🟢 Активных: *{activity_stats['active_referrals']}*\n"
    text += f"🔴 Неактивных: *{activity_stats['inactive_referrals']}*\n"
    text += f"📊 Активность: *{activity_stats['activity_rate']:.1f}%*\n\n"

    # By level breakdown
    text += "*По уровням:*\n"
    for level in [1, 2, 3]:
        level_data = activity_stats["by_level"].get(level, {"total": 0, "active": 0})
        total = level_data["total"]
        active = level_data["active"]
        text += f"   Ур.{level}: {active}/{total} активных\n"

    text += (
        "\n💡 *Совет:* Приглашайте активных пользователей - "
        "они приносят больше дохода!"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )
