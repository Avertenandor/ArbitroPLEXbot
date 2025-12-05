"""
User detail view handlers.

Displays detailed financial card for selected user.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_report_service import FinancialReportService
from bot.handlers.admin.financials.formatters import format_user_financial_detail
from bot.handlers.admin.financials.states import AdminFinancialStates
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_back_keyboard,
    admin_user_financial_detail_keyboard,
)

router = Router()


@router.message(AdminFinancialStates.viewing_list, F.text.startswith("👤"))
async def show_user_financial_detail(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show detailed financial card for selected user."""
    # Проверка прав доступа
    admin = await get_admin_or_deny(message, session, require_extended=True, **data)
    if not admin:
        return

    # Парсим ID пользователя из текста кнопки: "👤 123. username | +100 | -50"
    try:
        text_parts = message.text.split(".")
        user_id = int(text_parts[0].replace("👤", "").strip())
    except (ValueError, IndexError):
        await message.answer("❌ Ошибка при разборе ID пользователя")
        return

    service = FinancialReportService(session)
    dto = await service.get_user_detailed_financial_report(user_id)

    if not dto:
        await message.answer("❌ Пользователь не найден")
        return

    # Сохраняем ID для навигации
    await state.update_data(selected_user_id=user_id)
    await state.set_state(AdminFinancialStates.viewing_user_detail)

    # Форматируем детальную карточку
    text = format_user_financial_detail(dto)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_financial_detail_keyboard(),
        disable_web_page_preview=True
    )


@router.message(AdminFinancialStates.viewing_user, F.text == "💸 История выводов")
async def show_user_withdrawals(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show recent withdrawals with copyable hashes."""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")

    if not user_id:
        await message.answer("❌ Ошибка: ID пользователя потерян.")
        return

    service = FinancialReportService(session)
    withdrawals = await service.get_user_withdrawals(user_id, limit=10)

    if not withdrawals:
        await message.answer("💸 У пользователя нет подтвержденных выводов.")
        return

    from bot.utils.formatters import escape_md

    text = "💸 **История выводов (последние 10):**\n\n"

    for tx in withdrawals:
        date_str = tx.created_at.strftime('%d\\.%m\\.%Y %H:%M')
        amount = f"{tx.amount:.2f}"
        tx_hash = escape_md(tx.tx_hash) if tx.tx_hash else "Нет хеша"

        text += (
            f"📅 {date_str}\n"
            f"💵 `{amount}` USDT\n"
            f"🔗 Hash: `{tx_hash}`\n"
            f"──────────────────\n"
        )

    await state.set_state(AdminFinancialStates.viewing_withdrawals)
    # Use simple back keyboard for this leaf view
    await message.answer(
        text,
        parse_mode="MarkdownV2",
        reply_markup=admin_back_keyboard(),
    )


@router.message(AdminFinancialStates.viewing_user, F.text == "📜 История начислений")
async def show_user_accruals_stub(
    message: Message,
    state: FSMContext,
) -> None:
    """Stub for accrual history (can be expanded later)."""
    # For now, just show a message, as detailed accrual logs might be huge
    # Could reuse the Transaction model if we log accruals there, but currently
    # they are in DepositReward which is separate.
    await message.answer("ℹ️ Детальный лог начислений доступен в базе данных. (Функция в разработке)")
