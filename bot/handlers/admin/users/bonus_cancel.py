"""
Admin User Bonus Cancel Handler.

Handles bonus cancellation operations:
- Cancel bonus flow (select, reason, confirm)
"""

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
    from aiogram.types import ReplyKeyboardMarkup


router = Router(name="admin_users_bonus_cancel")


# ============ CANCEL REASON TEMPLATES ============

CANCEL_REASON_TEMPLATES = [
    ("🚫 Ошибка начисления", "Ошибочное начисление бонуса"),
    ("👤 По запросу клиента", "Отмена по запросу пользователя"),
    (
        "⚠️ Нарушение правил",
        "Нарушение правил использования платформы",
    ),
    ("🔄 Дубликат", "Дублирующее начисление"),
    ("📋 Тех. причины", "Технические причины"),
    ("✏️ Другое", None),  # Custom input
]


def cancel_reason_keyboard() -> "ReplyKeyboardMarkup":
    """Keyboard for selecting cancel reason."""
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

    buttons = []
    for emoji_name, _ in CANCEL_REASON_TEMPLATES:
        buttons.append([KeyboardButton(text=emoji_name)])
    buttons.append([KeyboardButton(text="◀️ Назад")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


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


# ============ CANCEL BONUS FLOW ============


@router.message(F.text == "❌ Отменить бонус")
async def start_cancel_bonus(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Step 1: Show list of active bonuses to cancel.

    Displays all active bonuses with detailed info for selection.
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
    safe_username = (
        escape_markdown(user.username)
        if user and user.username
        else str(user_id)
    )

    bonus_service = BonusService(session)
    active_bonuses = await bonus_service.get_user_bonuses(
        user_id,
        active_only=True,
    )

    if not active_bonuses:
        await message.answer(
            f"ℹ️ **Нет активных бонусов**\n\n"
            f"У пользователя @{safe_username} "
            f"нет активных бонусов для отмены.",
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
        created = (
            bonus.created_at.strftime("%d.%m.%Y")
            if bonus.created_at
            else "н/д"
        )
        reason_short = (bonus.reason or "")[:30]
        if len(bonus.reason or "") > 30:
            reason_short += "..."

        text += (
            f"🔹 **ID {bonus.id}**\n"
            f"   💰 Сумма: `{format_usdt(bonus.amount)} USDT`\n"
            f"   📊 ROI: {progress:.1f}% "
            f"(выплачено: `{format_usdt(bonus.roi_paid_amount)}`)\n"
            f"   🎯 Осталось до кепа: "
            f"`{format_usdt(remaining)} USDT`\n"
            f"   📅 Дата: {created}\n"
            f"   📝 _{reason_short}_\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **Введите ID бонуса для отмены:**\n\n"
        "_При отмене бонус становится неактивным, "
        "ROI начисления прекращаются._"
    )

    from bot.handlers.admin.users.bonus import UserBonusStates

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
            "❌ **Неверный формат**\n\n"
            "Введите только число — ID бонуса из списка выше.",
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

    from bot.handlers.admin.users.bonus import UserBonusStates

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
                    "✏️ **Введите причину отмены:**\n\n"
                    "_Опишите причину отмены своими словами._",
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
                "❌ Причина слишком короткая. "
                "Введите минимум 3 символа.",
            )
            return

    # Save reason and show confirmation
    await state.update_data(cancel_reason=reason)

    from bot.handlers.admin.users.bonus import UserBonusStates

    await state.set_state(UserBonusStates.cancel_confirm)

    # Get user info for confirmation
    user_id = state_data.get("selected_user_id")
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    safe_username = (
        escape_markdown(user.username)
        if user and user.username
        else str(user_id)
    )

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

        from bot.handlers.admin.users.bonus import UserBonusStates

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
    safe_username = (
        escape_markdown(user.username)
        if user and user.username
        else str(user_id)
    )

    admin_username = escape_markdown(
        admin.username or str(admin.telegram_id)
    )

    await message.answer(
        f"✅ **Бонус успешно отменён!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔹 **ID:** {bonus_id}\n"
        f"👤 **Пользователь:** @{safe_username}\n"
        f"💰 **Сумма:** `{format_usdt(bonus_amount)} USDT`\n"
        f"📝 **Причина:** _{reason}_\n"
        f"👤 **Отменил:** @{admin_username}\n\n"
        f"ℹ️ _ROI начисления по этому бонусу прекращены._",
        parse_mode="Markdown",
        reply_markup=admin_bonus_keyboard(),
    )

    logger.info(
        f"Admin {admin.telegram_id} (@{admin.username}) "
        f"cancelled bonus {bonus_id} "
        f"({bonus_amount} USDT) for user {user_id}: {reason}"
    )
