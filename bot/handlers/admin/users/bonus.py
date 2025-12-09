"""
Admin User Bonus Management Handler.

Handles admin-initiated bonus credit operations:
- Grant bonus to user
- View user's bonuses
- Cancel active bonus
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

router = Router(name="admin_users_bonus")


class BonusStates(StatesGroup):
    """States for bonus management flow."""

    waiting_amount = State()
    waiting_reason = State()
    waiting_cancel_reason = State()


@router.message(F.text == "🎁 Бонус")
async def show_bonus_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show bonus management menu OR go directly to grant (simplified flow)."""
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

    safe_username = escape_markdown(user.username) if user.username else str(user.telegram_id)
    
    # SIMPLIFIED FLOW: Go directly to grant bonus
    # Show user info and ask for amount immediately
    text = (
        f"🎁 **Начисление бонуса**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Пользователь: `{safe_username}`\n"
        f"🆔 ID: `{user.id}`\n\n"
        f"💰 **Текущий баланс:** `{format_usdt(stats['total_bonus_balance'])} USDT`\n"
        f"✅ **Активных бонусов:** {stats['active_bonuses_count']}\n\n"
        f"💵 **Введите сумму бонуса в USDT:**\n\n"
        f"Например: `100` или `50.5`\n\n"
        f"ℹ️ Бонус будет участвовать в начислении ROI "
        f"с теми же ставками, что и обычные депозиты (до 500%)."
    )
    
    await state.set_state(BonusStates.waiting_amount)

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


# IMPORTANT: This handler only works when user is selected (from user profile)
# For main bonus menu, use bonus_management_v2.py
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

    await state.set_state(BonusStates.waiting_amount)

    await message.answer(
        "💰 **Начисление бонуса**\n\n"
        "Введите сумму бонуса в USDT:\n\n"
        "Например: `100` или `50.5`\n\n"
        "ℹ️ Бонус будет участвовать в начислении ROI "
        "с теми же ставками, что и обычные депозиты (до 500%).",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(BonusStates.waiting_amount)
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
        await state.clear()
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
            "❌ Неверный формат суммы. Введите число, например: `100` или `50.5`",
            parse_mode="Markdown",
        )
        return

    await state.update_data(bonus_amount=str(amount))
    await state.set_state(BonusStates.waiting_reason)

    await message.answer(
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n\n"
        f"📝 Теперь введите причину начисления бонуса:\n\n"
        f"Например: `Компенсация за технические работы` или "
        f"`Бонус за привлечение рефералов`",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(BonusStates.waiting_reason)
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
        await state.clear()
        await message.answer(
            "Операция отменена",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    amount_str = state_data.get("bonus_amount")

    if not user_id or not amount_str:
        await state.clear()
        await message.answer("❌ Ошибка: данные сессии потеряны")
        return

    amount = Decimal(amount_str)
    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer(
            "❌ Причина слишком короткая. Введите более подробное описание.",
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

    safe_username = escape_markdown(user.username) if user and user.username else str(user_id)
    await message.answer(
        f"✅ **Бонус успешно начислен!**\n\n"
        f"👤 Пользователь: `{safe_username}`\n"
        f"💰 Сумма: `{format_usdt(amount)} USDT`\n"
        f"🎯 ROI Cap: `{format_usdt(roi_cap)} USDT` (500%)\n"
        f"📝 Причина: {reason}\n\n"
        f"ℹ️ Бонус начнёт участвовать в начислениях со следующего периода.",
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )

    logger.info(
        f"Admin {admin.telegram_id} granted bonus {amount} USDT "
        f"to user {user_id}: {reason}"
    )


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
    bonuses = await bonus_service.get_user_bonuses(user_id, active_only=False)

    if not bonuses:
        await message.answer(
            "📋 У пользователя нет бонусов",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    text = "📋 **Все бонусы пользователя:**\n\n"

    for bonus in bonuses:
        status_emoji = "✅" if bonus.is_active else ("🏁" if bonus.is_roi_completed else "❌")
        status_text = (
            "Активен" if bonus.is_active
            else ("ROI завершён" if bonus.is_roi_completed else "Отменён")
        )

        progress = bonus.roi_progress_percent
        created = bonus.created_at.strftime("%d.%m.%Y %H:%M")

        text += (
            f"{status_emoji} **ID {bonus.id}**\n"
            f"💰 Сумма: {format_usdt(bonus.amount)} USDT\n"
            f"📊 ROI: {progress:.1f}% ({format_usdt(bonus.roi_paid_amount)}/{format_usdt(bonus.roi_cap_amount)})\n"
            f"📅 Создан: {created}\n"
            f"📝 Причина: {bonus.reason[:50]}{'...' if len(bonus.reason) > 50 else ''}\n"
            f"📋 Статус: {status_text}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )


@router.message(F.text == "❌ Отменить бонус")
async def start_cancel_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start bonus cancellation flow."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    bonus_service = BonusService(session)
    active_bonuses = await bonus_service.get_user_bonuses(user_id, active_only=True)

    if not active_bonuses:
        await message.answer(
            "ℹ️ У пользователя нет активных бонусов для отмены",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    text = "❌ **Отмена бонуса**\n\nВыберите ID бонуса для отмены:\n\n"

    for bonus in active_bonuses:
        progress = bonus.roi_progress_percent
        text += (
            f"• **ID {bonus.id}**: {format_usdt(bonus.amount)} USDT "
            f"(ROI: {progress:.1f}%)\n"
        )

    text += "\nВведите ID бонуса:"

    await state.set_state(BonusStates.waiting_cancel_reason)
    await state.update_data(active_bonus_ids=[b.id for b in active_bonuses])

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(BonusStates.waiting_cancel_reason)
async def process_cancel_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process bonus cancellation."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Операция отменена",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    state_data = await state.get_data()
    active_bonus_ids = state_data.get("active_bonus_ids", [])

    # Parse input: "ID reason" or just ID then ask for reason
    parts = message.text.strip().split(maxsplit=1)

    try:
        bonus_id = int(parts[0])
    except ValueError:
        await message.answer("❌ Неверный формат. Введите ID бонуса (число).")
        return

    if bonus_id not in active_bonus_ids:
        await message.answer(
            f"❌ Бонус ID {bonus_id} не найден среди активных бонусов пользователя."
        )
        return

    # Get reason
    reason = parts[1] if len(parts) > 1 else "Отменён администратором"

    # Cancel bonus
    bonus_service = BonusService(session)
    success, error = await bonus_service.cancel_bonus(
        bonus_id=bonus_id,
        admin_id=admin.id,
        reason=reason,
    )

    if not success:
        await message.answer(f"❌ Ошибка: {error}")
        return

    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ **Бонус ID {bonus_id} отменён**\n\n"
        f"📝 Причина: {reason}\n\n"
        f"ℹ️ ROI начисления по этому бонусу прекращены.",
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )

    logger.info(
        f"Admin {admin.telegram_id} cancelled bonus {bonus_id}: {reason}"
    )


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
