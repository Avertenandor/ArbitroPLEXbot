"""
Admin User Bonus Management Handler.

Handles admin-initiated bonus credit operations:
- Grant bonus to user
- View user's bonuses
- Cancel active bonus
"""

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from aiogram.types import ReplyKeyboardMarkup


class UserBonusStates(StatesGroup):
    """States for user profile bonus management flow.

    Note: Named UserBonusStates to avoid conflict with
    bot.handlers.admin.bonus_v2.states.BonusStates which handles
    the main bonus management menu workflow.
    """

    waiting_amount = State()
    waiting_reason = State()
    # Cancel bonus flow states
    cancel_select_bonus = State()  # Step 1: Select bonus ID
    cancel_select_reason = State()  # Step 2: Select/enter reason
    cancel_confirm = State()  # Step 3: Confirm cancellation


# ============ CANCEL REASON TEMPLATES ============

CANCEL_REASON_TEMPLATES = [
    ("🚫 Ошибка начисления", "Ошибочное начисление бонуса"),
    ("👤 По запросу клиента", "Отмена по запросу пользователя"),
    ("⚠️ Нарушение правил", "Нарушение правил использования платформы"),
    ("🔄 Дубликат", "Дублирующее начисление"),
    ("📋 Тех. причины", "Технические причины"),
    ("✏️ Другое", None),  # Custom input
]


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


@router.message(UserBonusStates.waiting_amount)
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
        await state.set_state(None)  # Keep selected_user_id for navigation
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
    await state.set_state(UserBonusStates.waiting_reason)

    await message.answer(
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n\n"
        f"📝 Теперь введите причину начисления бонуса:\n\n"
        f"Например: `Компенсация за технические работы` или "
        f"`Бонус за привлечение рефералов`",
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(UserBonusStates.waiting_reason)
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
        await state.set_state(None)  # Keep selected_user_id for navigation
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

    logger.info(f"Admin {admin.telegram_id} granted bonus {amount} USDT to user {user_id}: {reason}")


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
        status_text = "Активен" if bonus.is_active else ("ROI завершён" if bonus.is_roi_completed else "Отменён")

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


# ============ CANCEL BONUS FLOW ============


def cancel_reason_keyboard() -> "ReplyKeyboardMarkup":
    """Keyboard for selecting cancel reason."""
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    buttons = []
    for emoji_name, _ in CANCEL_REASON_TEMPLATES:
        buttons.append([KeyboardButton(text=emoji_name)])
    buttons.append([KeyboardButton(text="◀️ Назад")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def cancel_confirm_keyboard() -> "ReplyKeyboardMarkup":
    """Keyboard for confirming cancellation."""
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить отмену")],
            [KeyboardButton(text="◀️ Назад")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "❌ Отменить бонус")
async def start_cancel_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Step 1: Show list of active bonuses to cancel.

    Displays all active bonuses with detailed info for easy selection.
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    # Get user info
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    safe_username = escape_markdown(user.username) if user and user.username else str(user_id)

    bonus_service = BonusService(session)
    active_bonuses = await bonus_service.get_user_bonuses(user_id, active_only=True)

    if not active_bonuses:
        await message.answer(
            f"ℹ️ **Нет активных бонусов**\n\nУ пользователя @{safe_username} нет активных бонусов для отмены.",
            parse_mode="Markdown",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    # Build detailed list
    text = (
        f"🚫 **Отмена бонуса**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Пользователь: @{safe_username}\n\n"
        f"📋 **Активные бонусы ({len(active_bonuses)}):**\n\n"
    )

    for bonus in active_bonuses:
        progress = bonus.roi_progress_percent
        remaining = bonus.roi_remaining
        created = bonus.created_at.strftime("%d.%m.%Y") if bonus.created_at else "н/д"
        reason_short = (bonus.reason or "")[:30]
        if len(bonus.reason or "") > 30:
            reason_short += "..."

        text += (
            f"🔹 **ID {bonus.id}**\n"
            f"   💰 Сумма: `{format_usdt(bonus.amount)} USDT`\n"
            f"   📊 ROI: {progress:.1f}% (выплачено: `{format_usdt(bonus.roi_paid_amount)}`)\n"
            f"   🎯 Осталось до кепа: `{format_usdt(remaining)} USDT`\n"
            f"   📅 Дата: {created}\n"
            f"   📝 _{reason_short}_\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **Введите ID бонуса для отмены:**\n\n"
        "_При отмене бонус становится неактивным, ROI начисления прекращаются._"
    )

    await state.set_state(UserBonusStates.cancel_select_bonus)
    await state.update_data(
        active_bonus_ids=[b.id for b in active_bonuses],
        bonuses_info={
            b.id: {
                "amount": str(b.amount),
                "roi_paid": str(b.roi_paid_amount),
                "progress": b.roi_progress_percent,
            }
            for b in active_bonuses
        },
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_cancel_keyboard(),
    )


@router.message(UserBonusStates.cancel_select_bonus)
async def process_cancel_select_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Step 2: Validate selected bonus ID and ask for reason.
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(None)
        await message.answer(
            "🚫 Отмена бонуса прервана.",
            reply_markup=admin_bonus_keyboard(),
        )
        return

    state_data = await state.get_data()
    active_bonus_ids = state_data.get("active_bonus_ids", [])
    bonuses_info = state_data.get("bonuses_info", {})

    # Parse bonus ID
    try:
        bonus_id = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ **Неверный формат**\n\nВведите только число — ID бонуса из списка выше.",
            parse_mode="Markdown",
        )
        return

    if bonus_id not in active_bonus_ids:
        await message.answer(
            f"❌ **Бонус ID {bonus_id} не найден**\n\n"
            f"Выберите ID из списка активных бонусов:\n"
            f"{', '.join(str(bid) for bid in active_bonus_ids)}",
            parse_mode="Markdown",
        )
        return

    # Save selected bonus and show reason selection
    bonus_info = bonuses_info.get(bonus_id, {})
    await state.update_data(
        cancel_bonus_id=bonus_id,
        cancel_bonus_amount=bonus_info.get("amount", "0"),
    )
    await state.set_state(UserBonusStates.cancel_select_reason)

    text = (
        f"📝 **Шаг 2 из 3: Причина отмены**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔹 Отменяется бонус **ID {bonus_id}**\n"
        f"💰 Сумма: `{format_usdt(bonus_info.get('amount', 0))} USDT`\n\n"
        f"Выберите причину отмены или введите свою:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_reason_keyboard(),
    )


@router.message(UserBonusStates.cancel_select_reason)
async def process_cancel_select_reason(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Step 3: Process reason and show confirmation.
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "◀️ Назад":
        # Go back to bonus selection
        await start_cancel_bonus(message, state, session, **data)
        return

    state_data = await state.get_data()
    bonus_id = state_data.get("cancel_bonus_id")
    bonus_amount = state_data.get("cancel_bonus_amount", "0")

    # Check if it's a template or custom reason
    reason = None
    for emoji_name, template_reason in CANCEL_REASON_TEMPLATES:
        if message.text == emoji_name:
            if template_reason:
                reason = template_reason
            else:
                # "Другое" selected - ask for custom reason
                await message.answer(
                    "✏️ **Введите причину отмены:**\n\n_Опишите причину отмены своими словами._",
                    parse_mode="Markdown",
                    reply_markup=admin_cancel_keyboard(),
                )
                return
            break

    # If not a template, use as custom reason
    if not reason:
        reason = message.text.strip()

        if len(reason) < 3:
            await message.answer(
                "❌ Причина слишком короткая. Введите минимум 3 символа.",
            )
            return

    # Save reason and show confirmation
    await state.update_data(cancel_reason=reason)
    await state.set_state(UserBonusStates.cancel_confirm)

    # Get user info for confirmation
    user_id = state_data.get("selected_user_id")
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    safe_username = escape_markdown(user.username) if user and user.username else str(user_id)

    text = (
        f"⚠️ **Подтверждение отмены бонуса**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Вы собираетесь отменить бонус:\n\n"
        f"🔹 **ID:** {bonus_id}\n"
        f"👤 **Пользователь:** @{safe_username}\n"
        f"💰 **Сумма:** `{format_usdt(bonus_amount)} USDT`\n"
        f"📝 **Причина:** _{reason}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ **Внимание!**\n"
        f"• Бонус станет неактивным\n"
        f"• ROI начисления прекратятся\n"
        f"• Сумма бонуса вычтется из бонусного баланса\n\n"
        f"**Подтвердить отмену?**"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_confirm_keyboard(),
    )


@router.message(UserBonusStates.cancel_confirm)
async def process_cancel_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Final step: Execute cancellation or go back.
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "◀️ Назад":
        # Go back to reason selection
        state_data = await state.get_data()
        bonus_id = state_data.get("cancel_bonus_id")
        bonus_amount = state_data.get("cancel_bonus_amount", "0")

        await state.set_state(UserBonusStates.cancel_select_reason)

        text = (
            f"📝 **Шаг 2 из 3: Причина отмены**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔹 Отменяется бонус **ID {bonus_id}**\n"
            f"💰 Сумма: `{format_usdt(bonus_amount)} USDT`\n\n"
            f"Выберите причину отмены или введите свою:"
        )

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=cancel_reason_keyboard(),
        )
        return

    if message.text != "✅ Подтвердить отмену":
        await message.answer(
            "⚠️ Нажмите **✅ Подтвердить отмену** или **◀️ Назад**",
            parse_mode="Markdown",
        )
        return

    # Execute cancellation
    state_data = await state.get_data()
    bonus_id = state_data.get("cancel_bonus_id")
    reason = state_data.get("cancel_reason", "Отменён администратором")
    bonus_amount = state_data.get("cancel_bonus_amount", "0")

    bonus_service = BonusService(session)
    success, error = await bonus_service.cancel_bonus(
        bonus_id=bonus_id,
        admin_id=admin.id,
        reason=reason,
    )

    if not success:
        await message.answer(
            f"❌ **Ошибка отмены**\n\n{error}",
            parse_mode="Markdown",
            reply_markup=admin_bonus_keyboard(),
        )
        await state.set_state(None)
        return

    await session.commit()
    await state.set_state(None)

    # Get user info for log
    user_id = state_data.get("selected_user_id")
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    safe_username = escape_markdown(user.username) if user and user.username else str(user_id)

    await message.answer(
        f"✅ **Бонус успешно отменён!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔹 **ID:** {bonus_id}\n"
        f"👤 **Пользователь:** @{safe_username}\n"
        f"💰 **Сумма:** `{format_usdt(bonus_amount)} USDT`\n"
        f"📝 **Причина:** _{reason}_\n"
        f"👤 **Отменил:** @{escape_markdown(admin.username or str(admin.telegram_id))}\n\n"
        f"ℹ️ _ROI начисления по этому бонусу прекращены._",
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )

    logger.info(
        f"Admin {admin.telegram_id} (@{admin.username}) cancelled bonus {bonus_id} "
        f"({bonus_amount} USDT) for user {user_id}: {reason}"
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
