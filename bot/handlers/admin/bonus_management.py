"""
Admin Bonus Management Handler.
Provides direct access to bonus management from admin panel.
"""
from decimal import Decimal, InvalidOperation
from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bonus_service import BonusService
from app.services.user_service import UserService
from bot.handlers.admin.bonus_v2.helpers import get_bonus_status
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny, get_admin_or_deny_callback
from bot.keyboards.reply import get_admin_keyboard_from_data
from bot.utils.formatters import format_balance, format_usdt
from bot.utils.text_utils import escape_markdown

router = Router(name="admin_bonus_management")

class BonusMgmtStates(StatesGroup):
    """States for bonus management."""

    menu = State()
    waiting_user = State()
    waiting_amount = State()
    waiting_reason = State()
    confirm = State()

def bonus_menu_keyboard(can_grant: bool = True) -> ReplyKeyboardMarkup:
    """Bonus management menu keyboard."""
    buttons = []
    if can_grant:
        buttons.append([KeyboardButton(text="➕ Начислить бонус")])
    buttons.extend(
        [
            [KeyboardButton(text="📋 История бонусов")],
            [KeyboardButton(text="🔍 Найти бонусы пользователя")],
            [KeyboardButton(text="◀️ Назад в админку")],
        ]
    )
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def confirm_bonus_keyboard() -> InlineKeyboardMarkup:
    """Confirmation keyboard for bonus grant."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", callback_data="bonus_confirm"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data="bonus_cancel"
                ),
            ]
        ]
    )

def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Cancel keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )

# ============ MAIN MENU ============

@router.message(StateFilter("*"), F.text == "🎁 Бонусы")
async def open_bonus_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Open bonus management menu."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return
    await state.set_state(BonusMgmtStates.menu)
    # Check permissions - moderators can only view
    can_grant = admin.role in ("super_admin", "extended_admin", "admin")
    role_name = {
        "super_admin": "👑 Босс",
        "extended_admin": "⭐ Старший админ",
        "admin": "👤 Админ",
        "moderator": "👁 Модератор (только просмотр)",
    }.get(admin.role, admin.role)
    # Get stats
    bonus_service = BonusService(session)
    stats = await bonus_service.get_global_bonus_stats()
    text = (
        f"🎁 **Управление бонусами**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Ваша роль: {role_name}\n\n"
        f"📊 **Статистика:**\n"
        f"• Всего начислено: "
        f"{format_balance(stats.get('total_granted', 0), decimals=2)} USDT\n"
        f"• Активных бонусов: {stats.get('active_count', 0)}\n"
        f"• За последние 24ч: "
        f"{format_balance(stats.get('last_24h', 0), decimals=2)} USDT\n\n"
        f"Выберите действие:"
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=bonus_menu_keyboard(can_grant),
    )

# ============ GRANT BONUS FLOW ============

@router.message(BonusMgmtStates.menu, F.text == "➕ Начислить бонус")
async def start_grant_bonus(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start bonus granting flow."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return
    # Check permission
    if admin.role not in ("super_admin", "extended_admin", "admin"):
        await message.answer(
            "❌ У вас нет прав на начисление бонусов.\n"
            "Обратитесь к старшему администратору."
        )
        return
    await state.set_state(BonusMgmtStates.waiting_user)
    await message.answer(
        "👤 **Начисление бонуса**\n\n"
        "Введите @username или Telegram ID пользователя:\n\n"
        "_Например: @username или 123456789_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusMgmtStates.waiting_user)
async def process_user_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process user input (username or ID)."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(BonusMgmtStates.menu)
        await message.answer(
            "Отменено.",
            reply_markup=bonus_menu_keyboard(True),
        )
        return
    user_input = message.text.strip()
    user_service = UserService(session)
    # Try to find user
    user = None
    if user_input.startswith("@"):
        username = user_input[1:]
        user = await user_service.get_by_username(username)
    elif user_input.isdigit():
        user = await user_service.get_by_telegram_id(int(user_input))
    else:
        # Try as username without @
        user = await user_service.get_by_username(user_input)
    if not user:
        await message.answer(
            f"❌ Пользователь `{escape_markdown(user_input)}` не найден.\n\n"
            "Попробуйте ещё раз или нажмите «❌ Отмена».",
            parse_mode="Markdown",
        )
        return
    # Save user and show info
    await state.update_data(
        target_user_id=user.id,
        target_username=user.username,
        target_telegram_id=user.telegram_id,
    )
    # Get user's current bonus info
    bonus_service = BonusService(session)
    user_stats = await bonus_service.get_user_bonus_stats(user.id)
    safe_username = escape_markdown(user.username) if user.username else "нет"
    text = (
        f"✅ **Пользователь найден:**\n\n"
        f"👤 Username: @{safe_username}\n"
        f"🆔 Telegram ID: `{user.telegram_id}`\n"
        f"💰 Текущий бонусный баланс: "
        f"`{format_balance(user_stats['total_bonus_balance'], decimals=2)} USDT`\n"
        f"📊 Заработано с бонусов: "
        f"`{format_balance(user_stats['total_bonus_roi_earned'], decimals=2)} USDT`\n\n"
        f"💵 Введите сумму бонуса в USDT:"
    )
    await state.set_state(BonusMgmtStates.waiting_amount)
    await message.answer(text, parse_mode="Markdown", reply_markup=cancel_keyboard())


@router.message(BonusMgmtStates.waiting_amount)
async def process_amount_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process bonus amount input."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(BonusMgmtStates.menu)
        await message.answer("Отменено.", reply_markup=bonus_menu_keyboard(True))
        return
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > 100000:
            raise ValueError("Amount too large")
    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Неверная сумма. "
            "Введите число от 0.01 до 100000:\n\n"
            "_Например: 50 или 100.5_",
            parse_mode="Markdown",
        )
        return
    await state.update_data(amount=str(amount))
    await state.set_state(BonusMgmtStates.waiting_reason)
    await message.answer(
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n\n"
        f"📝 Введите причину начисления бонуса:\n\n"
        f"_Например: Компенсация за технические проблемы_",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(BonusMgmtStates.waiting_reason)
async def process_reason_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process bonus reason and show confirmation."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        await state.set_state(BonusMgmtStates.menu)
        await message.answer("Отменено.", reply_markup=bonus_menu_keyboard(True))
        return
    reason = message.text.strip()
    if len(reason) < 3:
        await message.answer(
            "❌ Причина слишком короткая. Минимум 3 символа."
        )
        return
    if len(reason) > 500:
        await message.answer(
            "❌ Причина слишком длинная. "
            "Максимум 500 символов."
        )
        return
    await state.update_data(reason=reason)
    state_data = await state.get_data()
    amount = Decimal(state_data["amount"])
    roi_cap = amount * 5  # 500% ROI cap
    safe_username = escape_markdown(state_data.get("target_username") or "")
    text = (
        f"🎁 **Подтверждение начисления бонуса**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Получатель: @{safe_username}\n"
        f"🆔 Telegram ID: `{state_data['target_telegram_id']}`\n\n"
        f"💰 Сумма бонуса: **{format_usdt(amount)} USDT**\n"
        f"🎯 ROI Cap (500%): **{format_usdt(roi_cap)} USDT**\n\n"
        f"📝 Причина: _{escape_markdown(reason)}_\n\n"
        f"⚠️ **Подтвердите начисление:**"
    )
    await state.set_state(BonusMgmtStates.confirm)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=confirm_bonus_keyboard(),
    )


@router.callback_query(BonusMgmtStates.confirm, F.data == "bonus_confirm")
async def confirm_grant_bonus(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Confirm and execute bonus grant."""
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
        await callback.message.answer(f"❌ Ошибка: {error}")
        await callback.answer()
        return
    await session.commit()
    safe_username = escape_markdown(state_data.get("target_username") or "")
    roi_cap = amount * 5
    text = (
        f"✅ **Бонус успешно начислен!**\n\n"
        f"👤 Получатель: @{safe_username}\n"
        f"💰 Сумма: **{format_usdt(amount)} USDT**\n"
        f"🎯 ROI Cap: **{format_usdt(roi_cap)} USDT**\n"
        f"📝 Причина: {reason}\n\n"
        f"ℹ️ Бонус начнёт участвовать в начислении ROI "
        f"со следующего расчётного периода."
    )
    await state.set_state(BonusMgmtStates.menu)
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.message.answer(
        "Выберите следующее действие:",
        reply_markup=bonus_menu_keyboard(True),
    )
    logger.info(
        f"Admin {admin.telegram_id} granted bonus {amount} USDT "
        f"to user {user_id} ({state_data.get('target_username')}): {reason}"
    )
    await callback.answer("✅ Бонус начислен!")

@router.callback_query(BonusMgmtStates.confirm, F.data == "bonus_cancel")
async def cancel_grant_bonus(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Cancel bonus grant."""
    await state.set_state(BonusMgmtStates.menu)
    await callback.message.edit_text("❌ Начисление бонуса отменено.")
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=bonus_menu_keyboard(True),
    )
    await callback.answer()

# ============ BONUS HISTORY ============

@router.message(BonusMgmtStates.menu, F.text == "📋 История бонусов")
async def show_bonus_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show recent bonus history."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return
    bonus_service = BonusService(session)
    recent = await bonus_service.get_recent_bonuses(limit=15)
    if not recent:
        await message.answer(
            "📋 **История бонусов пуста.**\n\n"
            "Ещё не было начислено ни одного бонуса.",
            parse_mode="Markdown",
        )
        return
    text = "📋 **Последние бонусы:**\n\n"
    for b in recent:
        status = "🟢" if get_bonus_status(b) == "active" else "⚪"
        admin_name = b.admin.username if b.admin else "система"
        user_name = b.user.username if b.user else f"ID:{b.user_id}"
        safe_user = escape_markdown(user_name) if user_name else str(b.user_id)
        safe_admin = escape_markdown(admin_name) if admin_name else "система"
        text += (
            f"{status} **{format_usdt(b.amount)} USDT** → @{safe_user}\n"
            f"   _{b.reason[:30]}..._ | @{safe_admin}\n\n"
        )
    await message.answer(text, parse_mode="Markdown")

# ============ SEARCH USER BONUSES ============

@router.message(
    BonusMgmtStates.menu, F.text == "🔍 Найти бонусы пользователя"
)
async def start_search_user_bonuses(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start search for user's bonuses."""
    await state.set_state(BonusMgmtStates.waiting_user)
    await state.update_data(search_mode=True)
    await message.answer(
        "🔍 **Поиск бонусов пользователя**\n\n"
        "Введите @username или Telegram ID:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

# ============ BACK TO ADMIN ============

@router.message(BonusMgmtStates.menu, F.text == "◀️ Назад в админку")
async def back_to_admin(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to admin panel."""
    from bot.utils.admin_utils import clear_state_preserve_admin_token
    await clear_state_preserve_admin_token(state)
    await message.answer(
        "👑 Возвращаюсь в админ-панель...",
        reply_markup=get_admin_keyboard_from_data(data),
    )

@router.message(BonusMgmtStates.waiting_user, F.text == "❌ Отмена")
@router.message(BonusMgmtStates.waiting_amount, F.text == "❌ Отмена")
@router.message(BonusMgmtStates.waiting_reason, F.text == "❌ Отмена")
async def handle_cancel(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle cancel at any step."""
    await state.set_state(BonusMgmtStates.menu)
    await message.answer(
        "Отменено. Выберите действие:",
        reply_markup=bonus_menu_keyboard(True),
    )
