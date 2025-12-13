"""
Navigation handlers.

Handles back navigation and return to admin panel.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_report_service import FinancialReportService
from bot.handlers.admin.financials.states import AdminFinancialStates
from bot.keyboards.reply import admin_user_financial_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import escape_md


router = Router()


@router.message(
    StateFilter(AdminFinancialStates.viewing_user, AdminFinancialStates.viewing_withdrawals),
    F.text.in_({"◀️ Назад", "◀️ Назад к списку"})
)
async def handle_back(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle back navigation."""
    current_state = await state.get_state()

    if current_state == AdminFinancialStates.viewing_withdrawals:
        # Back to User Profile
        state_data = await state.get_data()
        user_id = state_data.get("selected_user_id")
        if user_id:
            # Re-render user profile
            service = FinancialReportService(session)
            details = await service.get_user_financial_details(user_id)
            if details:
                username = escape_md(details.user.username or "Нет юзернейма")
                text = (
                    f"📂 **Личное дело пользователя**\n"
                    f"ID: `{details.user.id}`\n"
                    f"Username: @{username}\n"
                    "Выберите действие:"
                )
                await state.set_state(AdminFinancialStates.viewing_user)
                await message.answer(
                    text,
                    parse_mode="MarkdownV2",
                    reply_markup=admin_user_financial_keyboard()
                )
                return

    # Default: Back to List
    from bot.handlers.admin.financials.list import show_financial_list
    await show_financial_list(message, session, state, **data)


@router.message(
    AdminFinancialStates.viewing_user_detail,
    F.text == "⬅ Назад к списку"
)
async def back_to_list_from_detail(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to users list from detail card."""
    from bot.handlers.admin.financials.list import show_financial_list
    await show_financial_list(message, session, state, **data)


@router.message(StateFilter(AdminFinancialStates), F.text == "👑 Админ-панель")
async def back_to_admin_panel(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to main admin panel from any financials state."""
    # Сохраняем admin_session_token и возвращаемся
    # в общий хендлер панели
    await clear_state_preserve_admin_token(state)
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
