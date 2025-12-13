"""
Admin User Referral Info Handler
Displays referral statistics for a selected user
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.referral_service import ReferralService
from bot.utils.formatters import format_balance


router = Router(name="admin_users_referrals")


@router.message(F.text == "👥 Рефералы")
async def handle_profile_referrals(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Show referrals info"""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        return

    service = ReferralService(session)
    stats = await service.get_referral_stats(user_id)

    text = (
        "👥 **Реферальная статистика**\n\n"
        f"Level 1: **{stats['level_1_count']}** партнёров\n"
        f"Level 2: **{stats['level_2_count']}** партнёров\n"
        f"Level 3: **{stats['level_3_count']}** партнёров\n\n"
        f"💰 Всего заработано: **{format_balance(stats['total_earned'], decimals=2)} USDT**"
    )

    await message.answer(text, parse_mode="Markdown")
