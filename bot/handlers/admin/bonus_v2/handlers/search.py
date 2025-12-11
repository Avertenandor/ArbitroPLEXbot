"""
Search User Handlers for Bonus Management V2.

Extracted from bonus_management_v2.py lines 865-941.
Handles searching for users and displaying their bonus statistics.

Handlers:
    - start_search_user: Initiate user search flow (prompt for input)
    - process_search_user: Process search input and display user bonus stats

Improvements over original:
    - Added ID:X format support for internal user IDs
    - Consistent error messages matching grant flow
    - Added logging for user not found scenarios
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

from ..helpers import format_user_display
from ..keyboards import bonus_main_menu_keyboard, cancel_keyboard
from ..states import BonusStates


router = Router(name="bonus_search")


# ============ SEARCH USER ============


@router.message(BonusStates.menu, F.text == "🔍 Найти пользователя")
async def start_search_user(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать поиск бонусов пользователя."""
    await state.set_state(BonusStates.search_user)

    await message.answer(
        "🔍 **Поиск бонусов пользователя**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Введите данные пользователя:\n"
        "• `@username` — по юзернейму\n"
        "• `123456789` — по Telegram ID\n"
        "• `ID:42` — по внутреннему ID\n\n"
        "_Или нажмите «Отмена» для возврата_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusStates.search_user, F.text != "❌ Отмена")
async def process_search_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Показать бонусы найденного пользователя."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_input = message.text.strip()
    user_service = UserService(session)
    user = None

    # Поиск по разным форматам
    if user_input.startswith("@"):
        user = await user_service.get_by_username(user_input[1:])
    elif user_input.upper().startswith("ID:"):
        # IMPROVEMENT: Added ID:X format support (missing in original)
        try:
            user_id = int(user_input[3:])
            user = await user_service.get_by_id(user_id)
        except ValueError:
            pass
    elif user_input.isdigit():
        user = await user_service.get_by_telegram_id(int(user_input))
    else:
        user = await user_service.get_by_username(user_input)

    if not user:
        # IMPROVEMENT: Added logging for user not found
        logger.warning(f"User search failed for admin {admin.username}: '{user_input}' not found")

        # IMPROVEMENT: Using consistent error message format (same as grant flow)
        await message.answer(
            f"❌ **Пользователь не найден**\n\n"
            f"Не удалось найти: `{escape_markdown(user_input)}`\n\n"
            f"Попробуйте другой формат:\n"
            f"• @username\n"
            f"• Telegram ID (число)\n"
            f"• ID:42 (внутренний ID)",
            parse_mode="Markdown",
        )
        return

    bonus_service = BonusService(session)
    user_stats = await bonus_service.get_user_bonus_stats(user.id)

    safe_username = escape_markdown(user.username) if user.username else str(user.telegram_id)

    text = (
        f"👤 **Бонусы пользователя @{safe_username}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Бонусный баланс: **{format_usdt(user_stats['total_bonus_balance'])} USDT**\n"
        f"📈 Заработано ROI: **{format_usdt(user_stats['total_bonus_roi_earned'])} USDT**\n"
        f"🟢 Активных: **{user_stats['active_bonuses_count']}**\n"
        f"📋 Всего: **{user_stats['total_bonuses_count']}**\n\n"
    )

    if user_stats.get("active_bonuses"):
        text += "**Активные бонусы:**\n"
        for bonus in user_stats["active_bonuses"][:5]:
            progress = bonus.roi_progress_percent if hasattr(bonus, "roi_progress_percent") else 0
            text += f"• ID `{bonus.id}`: {format_usdt(bonus.amount)} USDT (ROI: {progress:.0f}%)\n"

    await state.set_state(BonusStates.menu)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )
