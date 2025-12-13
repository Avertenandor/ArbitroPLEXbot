"""
Admin User Balance Management Handler
Handles user balance adjustments (credit/debit)
"""

from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.admin_log_service import AdminLogService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import cancel_keyboard
from bot.states.admin_states import AdminStates


router = Router(name="admin_users_balance")


def _deposit_void_inline_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="➖ Списать депозит", callback_data="admin:deposit_void")
    return kb.as_markup()


@router.message(F.text == "💳 Изменить баланс")
async def handle_profile_balance(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start balance change flow"""
    # Разрешаем изменение баланса всем администраторам (любой роли),
    # а не только extended/super admin.
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    await state.set_state(AdminStates.changing_user_balance)

    await message.answer(
        "💳 **Изменение баланса**\n\n"
        "Введите сумму для начисления (положительное число) "
        "или списания (отрицательное число).\n\n"
        "Пример: `100` (начислить) или `-50` (списать)",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminStates.changing_user_balance)
async def process_balance_change(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process balance change input"""
    if message.text == "❌ Отмена":
        state_data = await state.get_data()
        user_id = state_data.get("selected_user_id")
        if user_id:
            user_service = UserService(session)
            user = await user_service.get_by_id(user_id)
            if user:
                # Import here to avoid circular dependency
                from bot.handlers.admin.users.profile import show_user_profile

                await show_user_profile(message, user, state, session)
                return
        # Import here to avoid circular dependency
        from bot.handlers.admin.users.menu import handle_admin_users_menu

        await handle_admin_users_menu(message, state, **data)
        return

    try:
        amount = Decimal(message.text.replace(",", "."))
        if amount == 0:
            raise ValueError("Amount cannot be zero")
    except Exception:
        await message.reply("❌ Введите корректное число (например: 100 или -50)")
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        # Import here to avoid circular dependency
        from bot.handlers.admin.users.menu import handle_admin_users_menu

        await handle_admin_users_menu(message, state, **data)
        return

    user_service = UserService(session)

    # R9-2: Get current balance with lock to prevent race conditions
    stmt = select(User).where(User.id == user_id).with_for_update()
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    old_balance = user.balance or Decimal("0")
    new_balance = old_balance + amount

    if new_balance < 0:
        await message.reply(
            f"❌ Нельзя списать больше, чем есть на балансе.\nТекущий баланс: {old_balance}\n\n"
            "Если нужная сумма находится в разделе «Депозиты», используйте списание депозита.",
            reply_markup=_deposit_void_inline_keyboard(),
        )
        return

    # R9-2: Atomic balance update to prevent race conditions
    stmt = update(User).where(User.id == user_id).values(balance=User.balance + amount)
    await session.execute(stmt)
    await session.commit()

    admin = data.get("admin")
    admin_id = admin.id if admin else None

    # Security log (simplified usage)
    log_msg = (
        f"Admin {admin_id} changed balance for user {user_id} "
        f"by {amount}. New: {new_balance}"
    )
    logger.warning(log_msg)

    admin_log = AdminLogService(session)
    action = "Начисление" if amount > 0 else "Списание"
    await admin_log.log_action(
        admin_id=admin_id,
        action=f"balance_change_{'credit' if amount > 0 else 'debit'}",
        entity_type="user",
        entity_id=user_id,
        details={
            "amount": float(amount),
            "old_balance": float(old_balance),
            "new_balance": float(new_balance)
        },
        ip_address=None,
    )

    await message.answer(
        f"✅ Баланс успешно изменен.\n"
        f"{action}: {amount} USDT\n"
        f"Новый баланс: {new_balance} USDT"
    )

    # Reload user to show updated profile
    user = await user_service.get_by_id(user_id)
    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile

    await show_user_profile(message, user, state, session)
