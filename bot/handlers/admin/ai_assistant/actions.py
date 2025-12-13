"""
AI Assistant ARIA action handlers.

Contains handlers for ARIA admin actions (balance, deposits, etc).
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny

from .utils import (
    aria_actions_inline_keyboard,
    aria_cancel_inline_keyboard,
    aria_deposits_pick_keyboard,
    chat_keyboard,
    AIAssistantStates,
)


router = Router(name="admin_ai_actions")


@router.message(AIAssistantStates.chatting, CommandStart())
@router.message(AIAssistantStates.action_flow, CommandStart())
async def exit_aria_on_start(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Allow /start command to exit ARIA chat state."""
    logger.info(
        f"ARIA: User {message.from_user.id} used /start "
        "to exit ARIA chat",
    )
    await state.clear()

    from bot.handlers.start.registration.handlers import cmd_start

    session = data.get("session")
    if session:
        await cmd_start(message, session, state, **data)


@router.message(
    AIAssistantStates.chatting,
    F.text.in_(
        [
            "📊 Главное меню",
            "◀️ Главное меню",
            "🏠 Главное меню",
        ],
    ),
)
@router.message(
    AIAssistantStates.action_flow,
    F.text.in_(
        [
            "📊 Главное меню",
            "◀️ Главное меню",
            "🏠 Главное меню",
        ],
    ),
)
async def exit_aria_on_main_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Allow main menu button to exit ARIA chat state."""
    logger.info(
        f"ARIA: User {message.from_user.id} used main menu "
        "button to exit ARIA chat",
    )
    await state.clear()
    from bot.handlers.menu.core import show_main_menu

    await show_main_menu(message, session, state, **data)


async def _aria_list_confirmed_deposits_for_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user_identifier: str,
    payload: dict[str, Any],
) -> None:
    """List confirmed deposits for user during cancel flow."""
    from app.models.enums import TransactionStatus
    from app.repositories.deposit_repository import DepositRepository
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    dep_repo = DepositRepository(session)

    if user_identifier.startswith("@"):
        user = await user_repo.get_by_username(user_identifier[1:])
    else:
        user = await user_repo.get_by_telegram_id(int(user_identifier))

    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    deps = await dep_repo.find_by(
        user_id=user.id,
        status=TransactionStatus.CONFIRMED.value,
    )
    if not deps:
        await message.answer(
            "ℹ️ У пользователя нет подтверждённых "
            "депозитов.",
        )
        await state.set_state(AIAssistantStates.chatting)
        return

    deposit_rows = [
        (d.id, float(d.amount))
        for d in sorted(deps, key=lambda x: x.created_at, reverse=True)
    ]
    payload["user_identifier"] = user_identifier
    await state.update_data(
        aria_action="cancel_deposit",
        aria_payload=payload,
        aria_step="deposit_pick",
    )
    await message.answer(
        "Выберите депозит для отмены:",
        reply_markup=aria_deposits_pick_keyboard(deposit_rows),
    )


@router.callback_query(
    StateFilter("*"),
    F.data == "aria:suggest:cancel_deposit",
)
async def aria_suggest_cancel_deposit(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Suggest cancel deposit action."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return
    await callback.answer()
    if not callback.message:
        return

    state_data = await state.get_data()
    payload = state_data.get("aria_payload", {})
    user_identifier = str(payload.get("user_identifier") or "").strip()
    if not user_identifier:
        await state.set_state(AIAssistantStates.action_flow)
        await state.update_data(
            aria_action="cancel_deposit",
            aria_step="user",
            aria_payload={},
        )
        await callback.message.answer(
            "🚫 Отмена депозита\n\n"
            "Укажи пользователя: `@username` или `telegram_id`.",
            parse_mode="Markdown",
            reply_markup=aria_cancel_inline_keyboard(),
        )
        return

    await state.set_state(AIAssistantStates.action_flow)
    await _aria_list_confirmed_deposits_for_user(
        callback.message,
        session,
        state,
        user_identifier,
        payload,
    )


@router.message(
    AIAssistantStates.chatting,
    lambda m: m.text == "🛠 Действия",
)
async def show_actions_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show ARIA actions menu."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return
    await message.answer(
        "Выберите действие:",
        reply_markup=aria_actions_inline_keyboard(),
    )


@router.callback_query(StateFilter("*"), F.data == "aria:act:cancel")
async def aria_action_cancel(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Cancel current ARIA action."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return
    await state.set_state(AIAssistantStates.chatting)
    await state.update_data(aria_action=None, aria_step=None)
    await callback.answer("Отменено")
    await callback.message.answer(
        "Ок, отменил. Продолжаем диалог.",
        reply_markup=chat_keyboard(),
    )


@router.callback_query(
    AIAssistantStates.chatting,
    F.data.startswith("aria:act:"),
)
async def aria_action_start(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start ARIA action flow."""
    admin = await get_admin_or_deny(callback.message, session, **data)
    if not admin:
        return

    action = (callback.data or "").split(":", 2)[2]
    await state.set_state(AIAssistantStates.action_flow)
    await state.update_data(
        aria_action=action,
        aria_step="user",
        aria_payload={},
    )
    await callback.answer()

    if action == "cancel_deposit":
        await callback.message.answer(
            "🚫 Отмена депозита\n\n"
            "Укажи пользователя: `@username` или `telegram_id`.",
            parse_mode="Markdown",
            reply_markup=aria_cancel_inline_keyboard(),
        )
    elif action == "balance":
        await callback.message.answer(
            "💳 Изменение баланса\n\n"
            "Укажи пользователя: `@username` или `telegram_id`.",
            parse_mode="Markdown",
            reply_markup=aria_cancel_inline_keyboard(),
        )
    elif action == "manual_deposit":
        await callback.message.answer(
            "➕ Ручной депозит\n\n"
            "Укажи пользователя: `@username` или `telegram_id`.",
            parse_mode="Markdown",
            reply_markup=aria_cancel_inline_keyboard(),
        )
    elif action == "bonus":
        await callback.message.answer(
            "🎁 Начисление бонуса\n\n"
            "Укажи пользователя: `@username` или `telegram_id`.",
            parse_mode="Markdown",
            reply_markup=aria_cancel_inline_keyboard(),
        )
    else:
        await callback.message.answer(
            "❌ Неизвестное действие",
            reply_markup=chat_keyboard(),
        )
        await state.set_state(AIAssistantStates.chatting)
