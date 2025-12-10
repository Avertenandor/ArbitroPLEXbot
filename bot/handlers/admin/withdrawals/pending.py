"""
Admin Withdrawals - Pending Requests Handler.

Handles displaying and paginating pending withdrawal requests.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.withdrawal_service import WithdrawalService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_withdrawals_keyboard, withdrawal_list_keyboard
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.pagination import paginate_list


WITHDRAWALS_PER_PAGE = 8

router = Router(name="admin_withdrawals_pending")


async def _show_withdrawal_list(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    page: int = 1,
) -> None:
    """Helper to show paginated withdrawal list."""
    withdrawal_service = WithdrawalService(session)
    pending = await withdrawal_service.get_pending_withdrawals()

    if not pending:
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "📭 Нет ожидающих заявок на вывод.",
            reply_markup=admin_withdrawals_keyboard(),
        )
        return

    # Use pagination helper
    page_withdrawals, total, total_pages = paginate_list(
        pending, page, WITHDRAWALS_PER_PAGE
    )

    await state.set_state(AdminStates.selecting_withdrawal)
    await state.update_data(page=page)

    text = (
        f"⏳ **Ожидающие заявки на вывод**\n\n"
        f"📋 Всего заявок: {total}\n"
        f"📄 Страница: {page}/{total_pages}\n\n"
        "Нажмите на заявку для просмотра деталей:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=withdrawal_list_keyboard(
            page_withdrawals, page, total_pages
        ),
    )


@router.message(F.text == "⏳ Ожидающие выводы")
async def handle_pending_withdrawals(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show list of pending withdrawals as buttons for selection."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await _show_withdrawal_list(message, session, state, page=1)


@router.message(F.text == "⬅️ Пред.", AdminStates.selecting_withdrawal)
async def handle_prev_page(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Go to previous page of withdrawals."""
    fsm_data = await state.get_data()
    page = fsm_data.get("page", 1) - 1

    await _show_withdrawal_list(message, session, state, page=page)


@router.message(F.text == "След. ➡️", AdminStates.selecting_withdrawal)
async def handle_next_page(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Go to next page of withdrawals."""
    fsm_data = await state.get_data()
    page = fsm_data.get("page", 1) + 1

    await _show_withdrawal_list(message, session, state, page=page)
