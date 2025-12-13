"""
AI Assistant ARIA action flow handlers.

Contains handlers for multi-step ARIA action flows.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny

from .utils import (
    aria_balance_operation_keyboard,
    aria_cancel_inline_keyboard,
    aria_confirm_keyboard,
    aria_level_keyboard,
    aria_suggest_cancel_deposit_keyboard,
    chat_keyboard,
    _build_admin_data,
    AIAssistantStates,
)


router = Router(name="admin_ai_action_flows")


@router.callback_query(
    AIAssistantStates.action_flow,
    F.data.startswith("aria:balance_op:"),
)
async def aria_balance_op_pick(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle balance operation selection."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    op = (callback.data or "").split(":", 2)[2]
    state_data = await state.get_data()
    payload = state_data.get("aria_payload", {})
    payload["operation"] = op
    await state.update_data(aria_payload=payload, aria_step="amount")
    await callback.answer()
    await callback.message.answer(
        "Введите сумму (положительное число), "
        "например: `100`.",
        parse_mode="Markdown",
        reply_markup=aria_cancel_inline_keyboard(),
    )


@router.callback_query(
    AIAssistantStates.action_flow,
    F.data.startswith("aria:level:"),
)
async def aria_level_pick(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle level selection for manual deposit."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    lvl_s = (callback.data or "").split(":", 2)[2]
    try:
        lvl = int(lvl_s)
    except ValueError:
        await callback.answer("Неверный уровень")
        return

    state_data = await state.get_data()
    payload = state_data.get("aria_payload", {})
    payload["level"] = lvl
    await state.update_data(aria_payload=payload, aria_step="amount")
    await callback.answer()
    await callback.message.answer(
        "Введите сумму депозита в USDT, например: `100`.",
        parse_mode="Markdown",
        reply_markup=aria_cancel_inline_keyboard(),
    )


@router.callback_query(
    AIAssistantStates.action_flow,
    F.data.startswith("aria:deposit:"),
)
async def aria_deposit_pick(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle deposit selection for cancellation."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    deposit_id_s = (callback.data or "").split(":", 2)[2]
    try:
        deposit_id = int(deposit_id_s)
    except ValueError:
        await callback.answer("Неверный ID")
        return

    state_data = await state.get_data()
    payload = state_data.get("aria_payload", {})
    payload["deposit_id"] = deposit_id
    await state.update_data(aria_payload=payload, aria_step="reason")
    await callback.answer()
    await callback.message.answer(
        "Укажите причину отмены (минимум 5 символов).",
        reply_markup=aria_cancel_inline_keyboard(),
    )


@router.callback_query(
    AIAssistantStates.action_flow,
    F.data == "aria:confirm:run",
)
async def aria_confirm_run(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Execute confirmed ARIA action."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    action = state_data.get("aria_action")
    payload = state_data.get("aria_payload", {})

    await callback.answer()

    try:
        if action == "cancel_deposit":
            from app.services.ai_deposits_service import (
                AIDepositsService,
            )

            service = AIDepositsService(
                session,
                admin_data=_build_admin_data(admin),
            )
            result = await service.cancel_deposit(
                deposit_id=int(payload["deposit_id"]),
                reason=str(payload["reason"]),
            )
        elif action == "balance":
            from app.services.ai_users import AIUsersService

            service = AIUsersService(
                session,
                admin_data=_build_admin_data(admin),
            )
            result = await service.change_user_balance(
                user_identifier=str(payload["user_identifier"]),
                amount=float(payload["amount"]),
                reason=str(payload["reason"]),
                operation=str(payload["operation"]),
            )
        elif action == "manual_deposit":
            from app.services.ai_deposits_service import (
                AIDepositsService,
            )

            service = AIDepositsService(
                session,
                admin_data=_build_admin_data(admin),
            )
            result = await service.create_manual_deposit(
                user_identifier=str(payload["user_identifier"]),
                level=int(payload["level"]),
                amount=float(payload["amount"]),
                reason=str(payload["reason"]),
            )
        elif action == "bonus":
            from app.services.ai_bonus_service import AIBonusService

            service = AIBonusService(
                session,
                admin_data=_build_admin_data(admin),
            )
            result = await service.grant_bonus(
                user_identifier=str(payload["user_identifier"]),
                amount=float(payload["amount"]),
                reason=str(payload["reason"]),
            )
        else:
            result = {"success": False, "error": "Неизвестное действие"}

        if result.get("success"):
            await callback.message.answer(
                str(result.get("message", "✅ Готово")),
            )
        else:
            err_text = str(result.get("error", "❌ Ошибка"))
            if (
                action == "balance"
                and str(payload.get("operation")) == "subtract"
                and (
                    "недостат" in err_text.lower()
                    or "баланс" in err_text.lower()
                )
            ):
                await callback.message.answer(
                    err_text + "\n\n"
                    "Похоже, нужная сумма находится в "
                    "«Депозиты». Хотите списать депозит?",
                    reply_markup=(
                        aria_suggest_cancel_deposit_keyboard()
                    ),
                )
            else:
                await callback.message.answer(err_text)
    finally:
        await state.set_state(AIAssistantStates.chatting)
        await state.update_data(
            aria_action=None,
            aria_step=None,
            aria_payload={},
        )


@router.message(AIAssistantStates.action_flow)
async def aria_action_flow_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle user input during ARIA action flow."""
    from .actions import _aria_list_confirmed_deposits_for_user

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    text = (message.text or "").strip()
    if not text or text == "🔚 Завершить диалог":
        return

    state_data = await state.get_data()
    action = state_data.get("aria_action")
    step = state_data.get("aria_step")
    payload = state_data.get("aria_payload", {})

    if step == "user":
        if not (text.startswith("@") or text.isdigit()):
            await message.answer(
                "❌ Укажите `@username` или `telegram_id`.",
                parse_mode="Markdown",
            )
            return
        payload["user_identifier"] = text

        if action == "balance":
            await state.update_data(
                aria_payload=payload,
                aria_step="balance_op",
            )
            await message.answer(
                "Выберите операцию:",
                reply_markup=aria_balance_operation_keyboard(),
            )
        elif action == "manual_deposit":
            await state.update_data(
                aria_payload=payload,
                aria_step="level",
            )
            await message.answer(
                "Выберите уровень депозита:",
                reply_markup=aria_level_keyboard(),
            )
        elif action == "bonus":
            await state.update_data(
                aria_payload=payload,
                aria_step="amount",
            )
            await message.answer(
                "Введите сумму бонуса в USDT, например: `100`. ",
                parse_mode="Markdown",
            )
        elif action == "cancel_deposit":
            await _aria_list_confirmed_deposits_for_user(
                message,
                session,
                state,
                text,
                payload,
            )
        else:
            await message.answer("❌ Неизвестный сценарий")
        return

    if step == "balance_op":
        await message.answer(
            "Выберите операцию кнопкой ниже.",
            reply_markup=aria_balance_operation_keyboard(),
        )
        return

    if step == "level":
        await message.answer(
            "Выберите уровень кнопкой ниже.",
            reply_markup=aria_level_keyboard(),
        )
        return

    if step == "amount":
        try:
            amount = float(text.replace(",", "."))
        except ValueError:
            await message.answer(
                "❌ Введите число, например `100`.",
                parse_mode="Markdown",
            )
            return
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной.")
            return
        payload["amount"] = amount
        await state.update_data(
            aria_payload=payload,
            aria_step="reason",
        )
        await message.answer(
            "Укажите причину (минимум 5 символов).",
            reply_markup=aria_cancel_inline_keyboard(),
        )
        return

    if step == "reason":
        if len(text) < 5:
            await message.answer(
                "❌ Причина слишком короткая "
                "(минимум 5 символов).",
            )
            return
        payload["reason"] = text

        if action == "cancel_deposit" and not payload.get("deposit_id"):
            await message.answer(
                "Сначала выберите депозит кнопкой выше.",
            )
            return

        await state.update_data(
            aria_payload=payload,
            aria_step="confirm",
        )
        await message.answer(
            "Подтвердить выполнение?",
            reply_markup=aria_confirm_keyboard("aria:confirm:run"),
        )
        return

    if step == "confirm":
        await message.answer(
            "Нажмите «✅ Подтвердить» или «❌ Отмена».",
            reply_markup=aria_confirm_keyboard("aria:confirm:run"),
        )
