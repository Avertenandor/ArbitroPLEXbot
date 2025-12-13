"""
Admin User Bonus Grant Handler.

Handles bonus granting operations:
- Start bonus grant flow
- Process bonus amount
- Process bonus reason
- Create bonus
"""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.admin import (
    admin_bonus_keyboard,
    admin_cancel_keyboard,
)
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

if TYPE_CHECKING:
    from bot.handlers.admin.users.bonus import UserBonusStates


router = Router(name="admin_users_bonus_grant")


@router.message(F.text == "🎁 Бонус")
async def show_bonus_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show bonus management menu OR go directly to grant."""
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

    bonus_service = BonusService(session)
    stats = await bonus_service.get_user_bonus_stats(user_id)

    safe_username = (
        escape_markdown(user.username)
        if user.username
        else str(user.telegram_id)
    )

    # SIMPLIFIED FLOW: Go directly to grant bonus
    # Show user info and ask for amount immediately
    text = (
        f"🎁 **Начисление бонуса**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Пользователь: `{safe_username}`\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"💰 **Текущий баланс:** "
        f"`{format_usdt(stats['total_bonus_balance'])} USDT`\n"
        f"✅ **Активных бонусов:** {stats['active_bonuses_count']}\n\n"
        f"💵 **Введите сумму бонуса в USDT:**\n\n"
        f"Например: `100` или `50.5`\n\n"
        f"ℹ️ Бонус будет участвовать в начислении ROI "
        f"с теми же ставками, что и обычные депозиты (до 500%)."
    )

    # Import state class to set state
    from bot.handlers.admin.users.bonus import UserBonusStates

    await state.set_state(UserBonusStates.waiting_amount)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


# Custom filter to check if user is selected in profile context
async def has_selected_user(message: Message, state: FSMContext) -> bool:
    """Filter: only handle if selected_user_id is in state."""
    state_data = await state.get_data()
    return state_data.get("selected_user_id") is not None


# IMPORTANT: This handler only works when user is selected
@router.message(F.text == "➕ Начислить бонус", has_selected_user)
async def start_grant_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start bonus granting flow (from user profile context only)."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from bot.handlers.admin.users.bonus import UserBonusStates

    await state.set_state(UserBonusStates.waiting_amount)

    await message.answer(
        "💰 **Начисление бонуса**\n\n"
        "Введите сумму бонуса в USDT:\n\n"
        "Например: `100` или `50.5`\n\n"
        "ℹ️ Бонус будет участвовать в начислении ROI "
        "с теми же ставками, что и обычные депозиты (до 500%).",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


async def process_bonus_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process entered bonus amount."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(None)  # Keep selected_user_id
        await message.answer(
            "Операция отменена",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    # Parse amount
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Неверный формат суммы. "
            "Введите число, например: `100` или `50.5`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(bonus_amount=str(amount))

    from bot.handlers.admin.users.bonus import UserBonusStates

    await state.set_state(UserBonusStates.waiting_reason)

    await message.answer(
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n\n"
        f"📝 Теперь введите причину начисления бонуса:\n\n"
        f"Например: `Компенсация за технические работы` или "
        f"`Бонус за привлечение рефералов`",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


async def process_bonus_reason(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process bonus reason and create bonus."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(None)  # Keep selected_user_id
        await message.answer(
            "Операция отменена",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    amount_str = state_data.get("bonus_amount")

    if not user_id or not amount_str:
        await state.set_state(None)
        await message.answer(
            "❌ Ошибка: данные сессии потеряны",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    amount = Decimal(amount_str)
    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer(
            "❌ Причина слишком короткая. "
            "Введите более подробное описание.",
        )
        return

    # Grant bonus
    bonus_service = BonusService(session)
    bonus, error = await bonus_service.grant_bonus(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_id=admin.id,
    )

    if error:
        await message.answer(f"❌ Ошибка: {error}")
        return

    await session.commit()

    # Keep selected_user_id for navigation but clear bonus state
    await state.set_state(None)

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)

    roi_cap = bonus.roi_cap_amount if bonus else amount * Decimal("5")

    safe_username = (
        escape_markdown(user.username)
        if user and user.username
        else str(user_id)
    )
    await message.answer(
        f"✅ **Бонус успешно начислен!**\n\n"
        f"👤 Пользователь: `{safe_username}`\n"
        f"💰 Сумма: `{format_usdt(amount)} USDT`\n"
        f"🎯 ROI Cap: `{format_usdt(roi_cap)} USDT` (500%)\n"
        f"📝 Причина: {reason}\n\n"
        f"ℹ️ Бонус начнёт участвовать в начислениях "
        f"со следующего периода.",
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )

    logger.info(
        f"Admin {admin.telegram_id} granted bonus {amount} USDT "
        f"to user {user_id}: {reason}"
    )
