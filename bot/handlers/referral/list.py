"""
Referral List Module - REPLY KEYBOARDS ONLY!

Handles viewing and navigating through referral lists by level and page.
This module contains:
- Helper function to show paginated referral lists
- Handler for viewing all referrals
- Handler for level selection
- Handler for pagination navigation
"""

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.referral_service import ReferralService
from bot.keyboards.reply import referral_keyboard, referral_list_keyboard
from bot.utils.constants import REFERRAL_RATES
from bot.utils.formatters import format_usdt


router = Router(name="referral_list")


async def _show_referral_list(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    level: int = 1,
    page: int = 1,
) -> None:
    """
    Show referral list for specific level and page.

    R4-3: Shows detailed list with dates and earnings.
    R4-4: Supports pagination.

    Args:
        message: Telegram message
        session: Database session
        user: Current user
        state: FSM context
        level: Referral level (1-3)
        page: Page number
    """
    referral_service = ReferralService(session)

    # Get referrals for the level
    result = await referral_service.get_referrals_by_level(
        user.id, level=level, page=page, limit=10
    )

    referrals = result["referrals"]
    total = result["total"]
    total_pages = result["pages"]

    # Save to FSM for navigation
    await state.update_data(
        referral_level=level,
        referral_page=page,
    )

    # Build message text
    text = f"👥 *Мои рефералы - Уровень {level}*\n\n"

    if not referrals:
        text += f"На уровне {level} у вас пока нет рефералов."
    else:
        text += f"*Всего рефералов уровня {level}: {total}*\n\n"

        for idx, ref in enumerate(referrals, start=1):
            ref_user = ref["user"]
            earned = ref["earned"]
            joined_at = ref["joined_at"]

            username = ref_user.username or "без username"
            # Escape Markdown chars in username
            username = (
                username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            date_str = joined_at.strftime("%d.%m.%Y")

            text += (
                f"*{idx + (page - 1) * 10}.* @{username}\n"
                f"📅 Дата регистрации: {date_str}\n"
                f"💰 Заработано: *{format_usdt(earned)} USDT*\n\n"
            )

        if total_pages > 1:
            text += f"*Страница {page} из {total_pages}*\n\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=referral_list_keyboard(
            level=level,
            page=page,
            total_pages=total_pages,
        ),
    )


@router.message(F.text == "👥 Мои рефералы")
async def handle_my_referrals(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """
    Show user's referrals list.

    R4-2: Checks if user has any referrals, shows message if none.
    R4-3: Shows detailed list by levels.
    """
    referral_service = ReferralService(session)

    # R4-2: Check if user has any referrals across all levels
    total_referrals = 0
    for level in [1, 2, 3]:
        result = await referral_service.get_referrals_by_level(
            user.id, level=level, page=1, limit=1
        )
        total_referrals += result["total"]

    # R4-2: If no referrals at all, show message
    if total_referrals == 0:
        text = (
            "👥 *Мои рефералы*\n\n"
            "У вас пока нет рефералов.\n\n"
            "Приглашайте друзей и получайте бонусы с *3-х уровней*!\n"
            f"• Уровень 1: *{int(REFERRAL_RATES[1] * 100)}%* "
            "от депозитов и дохода\n"
            f"• Уровень 2: *{int(REFERRAL_RATES[2] * 100)}%* "
            "от депозитов и дохода\n"
            f"• Уровень 3: *{int(REFERRAL_RATES[3] * 100)}%* "
            "от депозитов и дохода\n\n"
            "Вашу реферальную ссылку можно найти в разделе "
            "\"📊 Статистика рефералов\"."
        )
        await message.answer(
            text, parse_mode="Markdown", reply_markup=referral_keyboard()
        )
        return

    # R4-3: Show detailed list for Level 1 by default
    await _show_referral_list(message, session, user, state, level=1, page=1)


@router.message(F.text.regexp(r"^📊 Уровень (\d+)$"))
async def handle_referral_level_selection(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Handle referral level selection button."""
    match = re.match(r"^📊 Уровень (\d+)$", message.text, re.UNICODE)
    if not match:
        return

    level = int(match.group(1))
    if level not in [1, 2, 3]:
        await message.answer("❌ Неверный уровень рефералов.")
        return

    await _show_referral_list(
        message, session, user, state, level=level, page=1
    )


@router.message(F.text.in_(["⬅ Предыдущая страница", "➡ Следующая страница"]))
async def handle_referral_pagination(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Handle referral list pagination."""
    data = await state.get_data()
    level = data.get("referral_level", 1)
    current_page = data.get("referral_page", 1)

    if message.text == "⬅ Предыдущая страница":
        page = max(1, current_page - 1)
    else:
        page = current_page + 1

    await _show_referral_list(
        message, session, user, state, level=level, page=page
    )
