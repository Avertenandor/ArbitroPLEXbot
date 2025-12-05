"""
Admin Withdrawal History Handler

Provides detailed withdrawal history with pagination functionality:
- View completed withdrawals with transaction hashes
- Navigate through pages of withdrawal records
- See user information and withdrawal amounts
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_withdrawal_history_pagination_keyboard
from bot.utils.formatters import format_usdt

router = Router(name="admin_panel_withdrawals")


@router.message(F.text == "📋 История выводов")
async def handle_withdrawal_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle detailed withdrawal history with pagination."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Store page in FSM
    await state.update_data(wd_history_page=1)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=1)


async def show_withdrawal_page(
    message: Message,
    withdrawal_service,
    page: int = 1,
) -> None:
    """Show withdrawal history page."""
    detailed = await withdrawal_service.get_detailed_withdrawals(page=page, per_page=5)

    text = "📋 **История выводов на кошельки**\n\n"

    if not detailed["withdrawals"]:
        text += "_Нет подтверждённых выводов_"
    else:
        for wd in detailed["withdrawals"]:
            wd_username = str(wd["username"] or "Без имени")
            safe_wd_username = (
                wd_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            tx_hash = wd["tx_hash"] or "N/A"
            tx_short = tx_hash[:16] + "..." if len(tx_hash) > 16 else tx_hash
            created = wd["created_at"].strftime("%d.%m %H:%M") if wd["created_at"] else "N/A"

            text += (
                f"👤 @{safe_wd_username}\n"
                f"   💵 {format_usdt(wd['amount'])} USDT\n"
                f"   🔗 `{tx_short}`\n"
                f"   📅 {created}\n\n"
            )

        text += f"_Страница {detailed['page']} из {detailed['total_pages']}_"

    # Reply keyboard with pagination
    keyboard = admin_withdrawal_history_pagination_keyboard(
        page=page,
        total_pages=detailed["total_pages"]
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.message(F.text == "⬅️ Пред. страница выводов")
async def handle_wd_prev_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle previous page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    new_page = max(1, current_page - 1)
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=new_page)


@router.message(F.text == "Вперёд страница выводов ➡️")
async def handle_wd_next_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle next page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    new_page = current_page + 1
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=new_page)
