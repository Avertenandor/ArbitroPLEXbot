"""
Admin User Deposit Void Handler

Allows admins to void (exclude) a confirmed deposit from internal accounting.

Use-case (from production feedback):
- User has funds in "Депозиты" but "Баланс" is 0.
- Admin needs to reverse an incorrectly credited deposit (internal correction).

Implementation notes:
- We do NOT change on-chain data. This operation only changes internal deposit status
  so that it no longer counts toward totals (confirmed deposits only).
- We mark the deposit status as FAILED (there is no CANCELLED status).
"""

from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from app.services.ai_deposits_service import AIDepositsService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import cancel_keyboard
from bot.states.admin_states import AdminStates
from bot.utils.formatters import format_balance


router = Router(name="admin_users_deposit_void")


async def _start_void_deposit_flow(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    deposit_repo = DepositRepository(session)
    deposits = await deposit_repo.find_by(
        user_id=user_id,
        status=TransactionStatus.CONFIRMED.value,
    )

    if not deposits:
        await message.answer("ℹ️ У пользователя нет подтверждённых депозитов.")
        return

    lines: list[str] = [
        "🚫 **Аннулирование депозита**\n",
        "Выберите депозит, который нужно аннулировать (исключить из учёта).\n",
        "⚠️ Это изменит внутренние цифры (Депозиты), но не влияет на блокчейн.\n",
        "\n**Подтверждённые депозиты:**",
    ]

    for d in sorted(deposits, key=lambda x: x.created_at, reverse=True):
        tx_short = f"…{d.tx_hash[-8:]}" if d.tx_hash else "N/A"
        created = d.created_at.strftime("%d.%m.%Y %H:%M")
        roi_paid = getattr(d, "roi_paid_amount", None) or 0
        deposit_line = (
            f"- ID `{d.id}`: `{format_balance(d.amount, decimals=2)} USDT` | "
            f"ROI выплачено: `{format_balance(roi_paid, decimals=2)}` | "
            f"{created} | tx {tx_short}"
        )
        lines.append(deposit_line)

    prompt_text = (
        "\nВведите **ID** депозита (например: `123`) "
        "или нажмите ❌ Отмена."
    )
    lines.append(prompt_text)

    await state.set_state(AdminStates.selecting_deposit_to_void)
    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )


@router.callback_query(F.data == "admin:deposit_void")
async def handle_void_deposit_start_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    await callback.answer()
    if not callback.message:
        return
    await _start_void_deposit_flow(callback.message, state, session, **data)


@router.message(F.text.in_({"🚫 Аннулировать депозит", "➖ Списать депозит"}))
async def handle_void_deposit_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    await _start_void_deposit_flow(message, state, session, **data)


@router.message(AdminStates.selecting_deposit_to_void)
async def handle_void_deposit_select(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    if message.text == "❌ Отмена":
        state_data = await state.get_data()
        user_id = state_data.get("selected_user_id")
        if user_id:
            user_service = UserService(session)
            user = await user_service.get_by_id(user_id)
            if user:
                from bot.handlers.admin.users.profile import show_user_profile

                await show_user_profile(message, user, state, session)
                return
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    try:
        deposit_id = int((message.text or "").strip())
    except ValueError:
        await message.reply("❌ Введите числовой ID депозита.")
        return

    # Lock row to avoid race conditions
    stmt = (
        select(Deposit)
        .where(Deposit.id == deposit_id)
        .where(Deposit.user_id == user_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    deposit = result.scalar_one_or_none()

    if not deposit:
        error_msg = "❌ Депозит не найден для выбранного пользователя."
        await message.reply(error_msg)
        return

    if deposit.status != TransactionStatus.CONFIRMED.value:
        error_msg = (
            "❌ Можно аннулировать только подтверждённые депозиты."
        )
        await message.reply(error_msg)
        return

    await state.update_data(void_deposit_id=deposit.id)
    await state.set_state(AdminStates.confirming_deposit_void)

    confirmation_text = (
        "🚫 **Аннулирование депозита**\n\n"
        f"Депозит: ID `{deposit.id}` "
        f"на сумму `{format_balance(deposit.amount, decimals=2)} USDT`\n\n"
        "Укажите причину аннулирования (минимум 5 символов) "
        "или нажмите ❌ Отмена."
    )
    await message.answer(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminStates.confirming_deposit_void)
async def handle_void_deposit_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    if message.text == "❌ Отмена":
        state_data = await state.get_data()
        user_id = state_data.get("selected_user_id")
        if user_id:
            user_service = UserService(session)
            user = await user_service.get_by_id(user_id)
            if user:
                from bot.handlers.admin.users.profile import show_user_profile

                await show_user_profile(message, user, state, session)
                return
        return

    reason = (message.text or "").strip()
    if len(reason) < 5:
        error_msg = (
            "❌ Укажите причину (минимум 5 символов) "
            "или нажмите ❌ Отмена."
        )
        await message.reply(error_msg)
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    deposit_id = state_data.get("void_deposit_id")

    if not user_id or not deposit_id:
        error_msg = (
            "❌ Контекст операции потерян. "
            "Откройте профиль пользователя заново."
        )
        await message.answer(error_msg)
        return

    # Use the same logic as ARIA tools to keep aggregates consistent
    admin_data = {"ID": admin.telegram_id, "username": admin.username}
    service = AIDepositsService(session, admin_data=admin_data)
    result = await service.cancel_deposit(
        deposit_id=int(deposit_id),
        reason=reason
    )
    if not result.get("success"):
        await message.answer(str(result.get("error", "❌ Ошибка")))
        return

    log_msg = (
        f"Admin {admin.telegram_id} cancelled deposit {deposit_id} "
        f"via profile flow. Reason: {reason}"
    )
    logger.warning(log_msg)
    await message.answer(str(result.get("message", "✅ Депозит отменён")))

    # Show updated profile
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if not user:
        return

    from bot.handlers.admin.users.profile import show_user_profile

    await show_user_profile(message, user, state, session)
