"""
Admin User Bonus View Handler.

Handles bonus viewing and navigation operations:
- List user bonuses
- Navigation back to profile
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.admin import admin_bonus_keyboard
from bot.utils.formatters import format_usdt


router = Router(name="admin_users_bonus_view")


# ============ LIST BONUSES ============


@router.message(F.text == "📋 Список бонусов")
async def list_user_bonuses(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """List all bonuses for selected user."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    bonus_service = BonusService(session)
    bonuses = await bonus_service.get_user_bonuses(
        user_id,
        active_only=False,
    )

    if not bonuses:
        await message.answer(
            "📋 У пользователя нет бонусов",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    text = "📋 **Все бонусы пользователя:**\n\n"

    for bonus in bonuses:
        status_emoji = (
            "✅"
            if bonus.is_active
            else ("🏁" if bonus.is_roi_completed else "❌")
        )
        status_text = (
            "Активен"
            if bonus.is_active
            else ("ROI завершён" if bonus.is_roi_completed else "Отменён")
        )

        progress = bonus.roi_progress_percent
        created = bonus.created_at.strftime("%d.%m.%Y %H:%M")

        reason_short = bonus.reason[:50]
        if len(bonus.reason) > 50:
            reason_short += "..."

        text += (
            f"{status_emoji} **ID {bonus.id}**\n"
            f"💰 Сумма: {format_usdt(bonus.amount)} USDT\n"
            f"📊 ROI: {progress:.1f}% "
            f"({format_usdt(bonus.roi_paid_amount)}/"
            f"{format_usdt(bonus.roi_cap_amount)})\n"
            f"📅 Создан: {created}\n"
            f"📝 Причина: {reason_short}\n"
            f"📋 Статус: {status_text}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )


# ============ NAVIGATION ============


@router.message(F.text == "◀️ Назад к профилю")
async def back_to_profile(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to user profile."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)

    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    from bot.handlers.admin.users.profile import show_user_profile

    await show_user_profile(message, user, state, session)
