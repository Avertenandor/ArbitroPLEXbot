"""
Referral Leaderboard Module - REPLY KEYBOARDS ONLY!

Handles top partners leaderboard display.
This module contains:
- Handler for viewing top partners (by referrals and earnings)
- Platform-wide referral statistics
"""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.referral_service import ReferralService
from bot.keyboards.reply import referral_keyboard
from bot.utils.formatters import format_usdt

router = Router(name="referral_leaderboard")


@router.message(F.text == "🏆 ТОП партнёров")
async def handle_top_partners(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Show public leaderboard of top partners."""
    referral_service = ReferralService(session)

    # Get leaderboard
    leaderboard = await referral_service.get_referral_leaderboard(limit=10)

    # Get platform stats
    platform_stats = await referral_service.get_platform_referral_stats()

    text = "🏆 *ТОП-10 партнёров ArbitroPLEX*\n\n"

    # Platform stats header
    total_earned = platform_stats.get('total_earnings', 0)
    total_refs = platform_stats.get('total_referrals', 0)
    text += f"📊 _Всего заработано партнёрами: {format_usdt(total_earned)} USDT_\n"
    text += f"👥 _Всего реферальных связей: {total_refs}_\n\n"

    # By referrals
    text += "📈 *По количеству рефералов:*\n"
    for entry in leaderboard["by_referrals"][:5]:
        rank = entry["rank"]
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        username = entry["username"] or f"ID:{entry['telegram_id']}"
        username = username.replace("_", "\\_").replace("*", "\\*")[:15]
        count = entry["referral_count"]
        text += f"{medal} @{username} — *{count}* реф.\n"

    text += "\n💰 *По заработку:*\n"
    for entry in leaderboard["by_earnings"][:5]:
        rank = entry["rank"]
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        username = entry["username"] or f"ID:{entry['telegram_id']}"
        username = username.replace("_", "\\_").replace("*", "\\*")[:15]
        earned = entry["total_earnings"]
        text += f"{medal} @{username} — *{format_usdt(earned)}* USDT\n"

    # User's position
    user_pos = await referral_service.get_user_leaderboard_position(user.id)
    if user_pos.get("referral_rank"):
        text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📍 *Ваша позиция:*\n"
        text += f"По рефералам: #{user_pos['referral_rank']}\n"
        text += f"По заработку: #{user_pos['earnings_rank']}\n"

    text += "\n💡 _Приглашайте друзей и поднимайтесь в рейтинге!_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_keyboard(),
    )
