"""
Deposits list handlers.

Displays full list of user deposits with pagination.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_report_service import FinancialReportService
from bot.handlers.admin.financials.formatters import (
    format_deposits_page,
    format_user_financial_detail,
    pagination_builder,
)
from bot.handlers.admin.financials.states import AdminFinancialStates
from bot.keyboards.reply import (
    admin_deposits_list_keyboard,
    admin_user_financial_detail_keyboard,
)

router = Router()


@router.message(AdminFinancialStates.viewing_user_detail, F.text == "📊 Все депозиты")
async def show_all_deposits(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show full list of user deposits with pagination."""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: пользователь не выбран")
        return

    service = FinancialReportService(session)
    dto = await service.get_user_detailed_financial_report(user_id)

    if not dto or not dto.deposits:
        await message.answer("📊 У пользователя нет депозитов")
        return

    # Пагинация: 10 депозитов на страницу
    page = 1
    per_page = 10
    total_pages = pagination_builder.get_total_pages(dto.deposits, per_page)

    await state.update_data(deposits_page=page, total_deposits_pages=total_pages)
    await state.set_state(AdminFinancialStates.viewing_deposits_list)

    text = format_deposits_page(dto.deposits, page, per_page, total_pages)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposits_list_keyboard(page, total_pages),
        disable_web_page_preview=True
    )


@router.message(
    AdminFinancialStates.viewing_deposits_list,
    F.text.in_({"⬅ Предыдущая", "Следующая ➡"})
)
async def handle_deposits_pagination(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle pagination for deposits list."""
    state_data = await state.get_data()
    current_page = state_data.get("deposits_page", 1)
    total_pages = state_data.get("total_deposits_pages", 1)
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Ошибка")
        return

    # Update page
    if message.text == "⬅ Предыдущая" and current_page > 1:
        current_page -= 1
    elif message.text == "Следующая ➡" and current_page < total_pages:
        current_page += 1
    else:
        return

    await state.update_data(deposits_page=current_page)

    # Get deposits
    service = FinancialReportService(session)
    dto = await service.get_user_detailed_financial_report(user_id)

    if not dto or not dto.deposits:
        await message.answer("❌ Ошибка загрузки данных")
        return

    per_page = 10
    text = format_deposits_page(dto.deposits, current_page, per_page, total_pages)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposits_list_keyboard(current_page, total_pages),
        disable_web_page_preview=True
    )


@router.message(
    AdminFinancialStates.viewing_deposits_list,
    F.text == "◀️ К карточке"
)
async def back_to_card_from_deposits(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to user card from deposits list."""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Ошибка")
        return

    service = FinancialReportService(session)
    dto = await service.get_user_detailed_financial_report(user_id)

    if not dto:
        await message.answer("❌ Пользователь не найден")
        return

    await state.set_state(AdminFinancialStates.viewing_user_detail)
    text = format_user_financial_detail(dto)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_financial_detail_keyboard(),
        disable_web_page_preview=True
    )
