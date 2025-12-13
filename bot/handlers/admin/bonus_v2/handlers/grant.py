"""
Grant Bonus Handler.

Workflow for granting bonuses to users with validation and confirmation.
Supports multiple user lookup formats (@username, telegram_id, ID:X).
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import (
    get_admin_or_deny,
    get_admin_or_deny_callback,
)
from bot.utils.formatters import format_balance, format_usdt
from bot.utils.text_utils import escape_markdown

from ..constants import BONUS_REASON_TEMPLATES
from ..helpers import get_role_permissions
from ..keyboards import (
    amount_quick_select_keyboard,
    bonus_main_menu_keyboard,
    cancel_keyboard,
    confirm_bonus_keyboard,
    reason_templates_keyboard,
)
from ..messages import BonusMessages
from ..states import BonusStates

router = Router(name="bonus_grant")


# ============ GRANT BONUS FLOW ============


@router.message(BonusStates.menu, F.text == "➕ Начислить бонус")
async def start_grant_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Начать процесс начисления бонуса."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    permissions = get_role_permissions(admin.role)
    if not permissions["can_grant"]:
        await message.answer(
            "❌ **Недостаточно прав**\n\nНачисление бонусов доступно только администраторам.",
            parse_mode="Markdown",
        )
        return

    await state.set_state(BonusStates.grant_user)
    await state.update_data(admin_role=admin.role)

    await message.answer(
        "➕ **Начисление бонуса**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Шаг 1 из 4:** Укажите получателя\n\n"
        "Введите данные пользователя:\n"
        "• `@username` — по юзернейму\n"
        "• `123456789` — по Telegram ID\n"
        "• `ID:42` — по внутреннему ID\n\n"
        "_Или нажмите «Отмена» для возврата_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusStates.grant_user, F.text != "❌ Отмена")
async def process_grant_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать ввод пользователя."""
    logger.info(f"process_grant_user called with text: {message.text}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning("process_grant_user: admin check failed")
        return

    user_input = message.text.strip() if message.text else ""
    logger.info(f"process_grant_user: user_input='{user_input}'")

    user_service = UserService(session)
    user = None

    # Поиск по разным форматам
    if user_input.startswith("@"):
        user = await user_service.get_by_username(user_input[1:])
    elif user_input.upper().startswith("ID:"):
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

    # Получаем статистику пользователя
    bonus_service = BonusService(session)
    user_stats = await bonus_service.get_user_bonus_stats(user.id)

    safe_username = escape_markdown(user.username) if user.username else "не указан"

    await state.update_data(
        target_user_id=user.id,
        target_username=user.username or str(user.telegram_id),
        target_telegram_id=user.telegram_id,
    )

    bonus_balance_str = format_balance(
        user_stats['total_bonus_balance'], decimals=2
    )
    roi_earned_str = format_balance(
        user_stats['total_bonus_roi_earned'], decimals=2
    )
    text = (
        f"✅ **Пользователь найден**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Username: @{safe_username}\n"
        f"🆔 Telegram ID: `{user.telegram_id}`\n"
        f"📊 Внутренний ID: `{user.id}`\n\n"
        f"💰 **Бонусный баланс:** {bonus_balance_str} USDT\n"
        f"📈 **Заработано ROI:** {roi_earned_str} USDT\n"
        f"🟢 **Активных бонусов:** {user_stats['active_bonuses_count']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Шаг 2 из 4:** Выберите сумму бонуса"
    )

    await state.set_state(BonusStates.grant_amount)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=amount_quick_select_keyboard(),
    )


@router.message(BonusStates.grant_amount, F.text != "❌ Отмена")
async def process_grant_amount(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать выбор/ввод суммы."""
    logger.info(f"process_grant_amount called with text: {message.text}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning("process_grant_amount: admin check failed")
        return

    text_input = message.text.strip() if message.text else ""
    logger.info(f"process_grant_amount: text_input='{text_input}'")

    # Обработка быстрого выбора
    if text_input == "💵 Ввести сумму вручную":
        await message.answer(
            "💵 **Ввод суммы вручную**\n\n"
            "Введите сумму бонуса в USDT:\n"
            "• Минимум: 1 USDT\n"
            "• Максимум: 100,000 USDT\n\n"
            "_Например: `150` или `75.50`_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        return

    # Парсим сумму
    amount_str = text_input.replace("USDT", "").replace(",", ".").strip()
    logger.info(f"process_grant_amount: amount_str='{amount_str}'")

    try:
        amount = Decimal(amount_str)
        if amount < 1:
            raise ValueError("Minimum 1 USDT")
        if amount > 100000:
            raise ValueError("Maximum 100000 USDT")
    except (InvalidOperation, ValueError) as e:
        logger.warning(f"process_grant_amount: invalid amount '{amount_str}': {e}")
        await message.answer(
            "❌ **Неверная сумма**\n\nВведите число от 1 до 100,000\n_Например: `100` или `50.5`_",
            parse_mode="Markdown",
        )
        return

    logger.info(f"process_grant_amount: amount={amount}")
    await state.update_data(amount=str(amount))

    roi_cap = amount * 5  # 500%

    await state.set_state(BonusStates.grant_reason)
    await message.answer(
        f"💰 **Сумма:** {format_usdt(amount)} USDT\n"
        f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Шаг 3 из 4:** Выберите причину начисления\n\n"
        f"_Нажмите на шаблон или введите свою причину:_",
        parse_mode="Markdown",
        reply_markup=reason_templates_keyboard(),
    )


@router.callback_query(BonusStates.grant_reason, F.data.startswith("bonus_reason:"))
async def process_reason_template(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать выбор шаблона причины."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    reason_data = callback.data.split(":", 1)[1]

    if reason_data == "custom":
        await callback.message.answer(
            "📝 **Введите причину вручную:**\n\n_Минимум 5 символов, максимум 200_",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        await callback.answer()
        return

    # Get reason text from index
    try:
        reason_idx = int(reason_data)
        if 0 <= reason_idx < len(BONUS_REASON_TEMPLATES):
            _, reason_text = BONUS_REASON_TEMPLATES[reason_idx]
            if reason_text:
                await state.update_data(reason=reason_text)
                await show_grant_confirmation(callback.message, state, admin)
                await callback.answer()
                return
    except ValueError:
        pass

    # Fallback: use raw data as reason (backward compatibility)
    await state.update_data(reason=reason_data)
    await show_grant_confirmation(callback.message, state, admin)
    await callback.answer()


@router.message(BonusStates.grant_reason, F.text != "❌ Отмена")
async def process_custom_reason(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать ввод причины вручную."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    reason = message.text.strip()

    if len(reason) < 5:
        await message.answer("❌ Причина слишком короткая. Минимум 5 символов.")
        return

    if len(reason) > 200:
        await message.answer("❌ Причина слишком длинная. Максимум 200 символов.")
        return

    await state.update_data(reason=reason)
    await show_grant_confirmation(message, state, admin)


async def show_grant_confirmation(target, state: FSMContext, admin) -> None:
    """Показать подтверждение начисления."""
    state_data = await state.get_data()

    amount = Decimal(state_data["amount"])
    roi_cap = amount * 5
    safe_username = escape_markdown(
        state_data.get("target_username", "")
    )
    safe_reason = escape_markdown(state_data['reason'])
    safe_admin = escape_markdown(
        admin.username or str(admin.telegram_id)
    )

    text = (
        f"🎁 **Подтверждение начисления**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Шаг 4 из 4:** Проверьте данные\n\n"
        f"👤 **Получатель:** @{safe_username}\n"
        f"🆔 **Telegram ID:** "
        f"`{state_data['target_telegram_id']}`\n\n"
        f"💰 **Сумма бонуса:** {format_usdt(amount)} USDT\n"
        f"🎯 **ROI Cap (500%):** {format_usdt(roi_cap)} USDT\n\n"
        f"📝 **Причина:** _{safe_reason}_\n\n"
        f"👤 **Админ:** @{safe_admin}\n\n"
        f"⚠️ **Подтвердите начисление бонуса**"
    )

    await state.set_state(BonusStates.grant_confirm)

    # Check if target is a callback message that can be edited
    # For regular messages, always use answer()
    keyboard = confirm_bonus_keyboard()
    if hasattr(target, "message") and target.message:
        # This is a CallbackQuery - edit the message
        await target.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    elif (
        hasattr(target, "edit_text")
        and target.from_user
        and target.from_user.is_bot
    ):
        # This is a bot message - can be edited
        await target.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        # Regular user message - send new message
        await target.answer(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_do_grant")
async def execute_grant_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Выполнить начисление бонуса."""
    admin = await get_admin_or_deny_callback(callback, session, **data)
    if not admin:
        return

    state_data = await state.get_data()

    user_id = state_data["target_user_id"]
    amount = Decimal(state_data["amount"])
    reason = state_data["reason"]

    bonus_service = BonusService(session)
    bonus, error = await bonus_service.grant_bonus(
        user_id=user_id,
        amount=amount,
        reason=reason,
        admin_id=admin.id,
    )

    if error:
        logger.error(
            f"Failed to grant bonus: user_id={user_id}, "
            f"amount={amount}, reason={reason}, "
            f"admin_id={admin.id}, error={error}"
        )
        safe_error = escape_markdown(str(error))
        await callback.message.edit_text(
            f"❌ **Ошибка:** {safe_error}",
            parse_mode="Markdown"
        )
        await callback.answer("Ошибка!", show_alert=True)
        return

    await session.commit()

    safe_username = escape_markdown(
        state_data.get("target_username", "")
    )
    roi_cap = amount * 5
    safe_reason = escape_markdown(reason)

    bonus_info = (
        f"ℹ️ _Бонус начнёт участвовать в начислении ROI "
        f"со следующего расчётного периода._"
    )
    text = (
        f"✅ **Бонус успешно начислен!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Получатель: @{safe_username}\n"
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
        f"🎯 ROI Cap: **{format_usdt(roi_cap)} USDT**\n"
        f"📝 Причина: {safe_reason}\n\n"
        f"🆔 ID бонуса: `{bonus.id}`\n\n"
        f"{bonus_info}"
    )

    await state.set_state(BonusStates.menu)
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer(
        "Выберите следующее действие:",
        reply_markup=bonus_main_menu_keyboard(admin.role),
    )

    logger.info(
        f"Admin {admin.telegram_id} (@{admin.username}) "
        f"granted bonus {amount} USDT "
        f"to user {user_id}: {reason}"
    )

    await callback.answer("✅ Бонус начислен!")


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_edit")
async def edit_grant_data(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Вернуться к редактированию."""
    await state.set_state(BonusStates.grant_user)
    edit_msg = (
        "✏️ **Редактирование**\n\n"
        "Начните заново — введите @username или "
        "Telegram ID пользователя:"
    )
    await callback.message.edit_text(
        edit_msg,
        parse_mode="Markdown",
    )
    await callback.message.answer(
        "Введите данные пользователя:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(BonusStates.grant_confirm, F.data == "bonus_cancel_grant")
async def cancel_grant(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Отменить начисление."""
    admin_role = (await state.get_data()).get("admin_role", "admin")
    await state.set_state(BonusStates.menu)
    await callback.message.edit_text("❌ Начисление бонуса отменено.")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=bonus_main_menu_keyboard(admin_role),
    )
    await callback.answer()


# ============ CANCEL HANDLERS ============


@router.message(BonusStates.grant_user, F.text == "❌ Отмена")
@router.message(BonusStates.grant_amount, F.text == "❌ Отмена")
@router.message(BonusStates.grant_reason, F.text == "❌ Отмена")
async def handle_cancel(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Обработать отмену на любом шаге."""
    admin = await get_admin_or_deny(message, session, **data)
    role = admin.role if admin else "admin"

    await state.set_state(BonusStates.menu)
    await message.answer(
        "❌ Операция отменена.",
        reply_markup=bonus_main_menu_keyboard(role),
    )
