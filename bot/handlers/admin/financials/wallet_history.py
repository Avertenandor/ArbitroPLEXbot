"""
Wallet history handlers.

Displays user's wallet change history.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_report_service import FinancialReportService
from bot.handlers.admin.financials.formatters import format_user_financial_detail
from bot.handlers.admin.financials.states import AdminFinancialStates
from bot.keyboards.reply import (
    admin_user_financial_detail_keyboard,
    admin_wallet_history_keyboard,
)
from bot.utils.formatters import format_wallet_short


router = Router()


@router.message(
    AdminFinancialStates.viewing_user_detail,
    F.text == "💳 История кошельков"
)
async def show_wallet_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show wallet change history."""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: пользователь не выбран")
        return

    service = FinancialReportService(session)
    dto = await service.get_user_detailed_financial_report(user_id)

    if not dto or not dto.wallet_history:
        await message.answer("💳 Пользователь не менял кошелек")
        return

    await state.set_state(AdminFinancialStates.viewing_wallet_history)

    text = "💳 **История смены кошельков:**\n\n"

    for i, wh in enumerate(dto.wallet_history, 1):
        date_str = wh.changed_at.strftime("%Y-%m-%d %H:%M")
        old_short = format_wallet_short(wh.old_wallet)
        new_short = format_wallet_short(wh.new_wallet)

        text += (
            f"{i}. **{date_str}**\n"
            f"   Старый: `{old_short}`\n"
            f"   Новый: `{new_short}`\n\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_wallet_history_keyboard()
    )


@router.message(
    AdminFinancialStates.viewing_wallet_history,
    F.text == "◀️ К карточке"
)
async def back_to_card_from_wallet_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Return to user card from wallet history."""
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
