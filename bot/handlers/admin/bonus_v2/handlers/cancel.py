"""
Bonus Cancellation Handlers.

CANCEL BONUS workflow - extracted from bonus_management_v2.py (lines 1005-1192, 1259-1284)

Handlers:
1. start_cancel_bonus - Shows active bonuses list (super_admin only)
2. confirm_cancel_bonus - Callback to confirm and ask for reason
3. execute_cancel_bonus - Execute cancellation with logging
4. cancel_cancel_bonus - Cancel the cancel flow
5. callback_start_cancel - Start cancel from bonus details view

Permissions:
- super_admin: Can cancel any bonus
- extended_admin: Can only cancel own bonuses (not implemented in this handler)
- admin/moderator: No cancel permissions
"""

from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from bot.handlers.admin.utils.admin_checks import (
    get_admin_or_deny,
    get_admin_or_deny_callback,
)
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown

from ..constants import BONUS_CANCEL_LIST_LIMIT, BONUS_FETCH_LIMIT
from ..helpers import get_bonus_status
from ..keyboards import bonus_main_menu_keyboard, cancel_keyboard
from ..states import BonusStates

if TYPE_CHECKING:
    from app.models.bonus_credit import BonusCredit

router = Router(name="bonus_cancel")


# ============ CANCEL BONUS (SUPER ADMIN ONLY) ============


@router.message(BonusStates.menu, F.text == "⚠️ Отмена бонусов")
async def start_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать процесс отмены бонуса (только супер-админ)."""
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    # Показать активные бонусы для отмены
    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=BONUS_CANCEL_LIST_LIMIT)
    active_bonuses = [b for b in recent if get_bonus_status(b) == "active"]

    if not active_bonuses:
        await message.answer(
            "⚠️ **Отмена бонусов**\n\nНет активных бонусов для отмены.",
            parse_mode="Markdown",
        )
        return

    text = "⚠️ **Отмена бонусов**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**Активные бонусы:**\n\n"

    buttons = []
    for b in active_bonuses[:10]:
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name)
        progress = b.roi_progress_percent if hasattr(b, "roi_progress_percent") else 0

        text += (
            f"🟢 **ID {b.id}:** {format_usdt(b.amount)} USDT → @{safe_user}\n"
            f"   ROI: {progress:.0f}% | _{(b.reason or '')[:20]}..._\n\n"
        )

        button_text = (
            f"❌ Отменить #{b.id} ({format_usdt(b.amount)})"
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"bonus_do_cancel:{b.id}"
                )
            ]
        )

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="bonus_back_to_menu")])

    text += "\n⚠️ _Выберите бонус для отмены:_"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("bonus_do_cancel:"))
async def confirm_cancel_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Подтвердить отмену бонуса."""
    admin = await get_admin_or_deny_callback(callback, session, require_super=True, **data)
    if not admin:
        return

    bonus_id = int(callback.data.split(":")[1])

    bonus_service = BonusService(session)
    bonuses = await bonus_service.get_recent_bonuses(limit=BONUS_FETCH_LIMIT)
    bonus = next((b for b in bonuses if b.id == bonus_id), None)

    if not bonus:
        await state.set_state(BonusStates.menu)  # Fix: Reset state when bonus not found
        await callback.answer("❌ Бонус не найден", show_alert=True)
        return

    if get_bonus_status(bonus) != "active":
        await callback.answer("❌ Бонус уже неактивен", show_alert=True)
        return

    await state.update_data(cancel_bonus_id=bonus_id)
    await state.set_state(BonusStates.cancel_reason)

    user_name = bonus.user.username if bonus.user else f"ID:{bonus.user_id}"
    safe_user = escape_markdown(user_name)

    safe_reason = escape_markdown(bonus.reason or 'не указана')
    await callback.message.edit_text(
        f"⚠️ **Отмена бонуса #{bonus_id}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Получатель: @{safe_user}\n"
        f"💰 Сумма: **{format_usdt(bonus.amount)} USDT**\n"
        f"📝 Причина начисления: _{safe_reason}_\n\n"
        f"⚠️ **Введите причину отмены:**",
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите причину отмены бонуса:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(BonusStates.cancel_reason, F.text != "❌ Отмена")
async def execute_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Выполнить отмену бонуса."""
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    cancel_reason = message.text.strip()
    if len(cancel_reason) < 5:
        await message.answer("❌ Причина слишком короткая. Минимум 5 символов.")
        return

    state_data = await state.get_data()
    bonus_id = state_data.get("cancel_bonus_id")

    if not bonus_id:
        await message.answer("❌ ID бонуса не найден. Попробуйте заново.")
        await state.set_state(BonusStates.menu)
        return

    bonus_service = BonusService(session)
    success, error = await bonus_service.cancel_bonus(
        bonus_id=bonus_id,
        admin_id=admin.id,
        reason=cancel_reason,
    )

    if not success:
        logger.error(f"[BONUS] Cancel failed: bonus_id={bonus_id}, error={error}")
        await message.answer(f"❌ **Ошибка:** {error}", parse_mode="Markdown")
        await state.set_state(BonusStates.menu)
        await message.answer(
            "Выберите действие:",
            reply_markup=bonus_main_menu_keyboard(admin.role),
        )
        return

    await session.commit()

    await state.set_state(BonusStates.menu)
    admin_name = escape_markdown(
        admin.username or str(admin.telegram_id)
    )
    await message.answer(
        f"✅ **Бонус #{bonus_id} успешно отменён!**\n\n"
        f"📝 Причина: {cancel_reason}\n"
        f"👤 Отменил: @{admin_name}",
        parse_mode="Markdown",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )

    logger.info(
        f"Super admin {admin.telegram_id} "
        f"cancelled bonus {bonus_id}: {cancel_reason}"
    )


@router.message(BonusStates.cancel_reason, F.text == "❌ Отмена")
async def cancel_cancel_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Отменить процесс отмены бонуса."""
    admin = await get_admin_or_deny(message, session, **data)
    role = admin.role if admin else "super_admin"

    await state.set_state(BonusStates.menu)
    await message.answer(
        "❌ Отмена бонуса прервана.",
        reply_markup=bonus_main_menu_keyboard(role),
    )


@router.callback_query(F.data.startswith("bonus_cancel:"))
async def callback_start_cancel(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать отмену бонуса через callback."""
    admin = await get_admin_or_deny_callback(callback, session, require_super=True, **data)
    if not admin:
        return

    bonus_id = int(callback.data.split(":")[1])
    await state.update_data(cancel_bonus_id=bonus_id)
    await state.set_state(BonusStates.cancel_reason)

    await callback.message.edit_text(
        f"⚠️ **Отмена бонуса #{bonus_id}**\n\nВведите причину отмены:",
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите причину отмены:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()
