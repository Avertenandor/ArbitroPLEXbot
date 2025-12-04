"""
Admin Referral Statistics Handler.

Shows platform-wide referral statistics for admins.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.referral_service import ReferralService
from bot.keyboards.admin_keyboards import admin_keyboard
from bot.utils.formatters import format_usdt

router = Router(name="admin_referral_stats")


@router.message(StateFilter("*"), F.text == "📊 Реферальная статистика")
async def handle_admin_referral_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show platform-wide referral statistics."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Доступ запрещён")
        return

    referral_service = ReferralService(session)

    # Get platform stats
    stats = await referral_service.get_platform_referral_stats()

    # Get leaderboard
    leaderboard = await referral_service.get_referral_leaderboard(limit=5)

    text = (
        "📊 **Реферальная статистика платформы**\n\n"
        f"👥 Всего реферальных связей: **{stats['total_referrals']}**\n\n"
        "**По уровням:**\n"
    )

    for level in [1, 2, 3]:
        level_data = stats['by_level'].get(level, {"count": 0, "earnings": 0})
        text += (
            f"• Уровень {level}: {level_data['count']} связей, "
            f"{format_usdt(level_data['earnings'])} USDT\n"
        )

    text += (
        f"\n**Финансы:**\n"
        f"💰 Всего начислено: **{format_usdt(stats['total_earnings'])} USDT**\n"
        f"✅ Выплачено: **{format_usdt(stats['paid_earnings'])} USDT**\n"
        f"⏳ Ожидает: **{format_usdt(stats['pending_earnings'])} USDT**\n"
    )

    # Top referrers
    if leaderboard.get("by_referrals"):
        text += "\n🏆 **Топ-5 по рефералам:**\n"
        for entry in leaderboard["by_referrals"][:5]:
            username = entry.get("username") or f"ID:{entry['telegram_id']}"
            text += (
                f"{entry['rank']}. @{username} - "
                f"{entry['referral_count']} реф.\n"
            )

    # Top earners
    if leaderboard.get("by_earnings"):
        text += "\n💰 **Топ-5 по заработку:**\n"
        for entry in leaderboard["by_earnings"][:5]:
            username = entry.get("username") or f"ID:{entry['telegram_id']}"
            text += (
                f"{entry['rank']}. @{username} - "
                f"{format_usdt(entry['total_earnings'])} USDT\n"
            )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(),
    )
