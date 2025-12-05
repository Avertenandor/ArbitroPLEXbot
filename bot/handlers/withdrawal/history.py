"""
Withdrawal history module.

This module handles displaying withdrawal transaction history with pagination support.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.models.user import User
from app.services.withdrawal_service import WithdrawalService

# Router will be created in __init__.py and imported there
router = Router()


@router.message(F.text == "📜 История выводов")
async def show_history(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show withdrawal history."""
    user: User | None = data.get("user")
    if not user:
        return

    # Filter out 'user' to avoid duplicate argument error
    filtered_data = {k: v for k, v in data.items() if k != "user"}
    await _show_withdrawal_history(message, state, user, page=1, **filtered_data)


async def _show_withdrawal_history(
    message: Message,
    state: FSMContext,
    user: User,
    page: int = 1,
    **data: Any,
) -> None:
    """Show withdrawal history with pagination."""
    session_factory = data.get("session_factory")

    if not session_factory:
        session = data.get("session")
        if not session:
            await message.answer("❌ Системная ошибка.")
            return
        withdrawal_service = WithdrawalService(session)
        result = await withdrawal_service.get_user_withdrawals(
            user.id, page=page, limit=10
        )
    else:
        async with session_factory() as session:
            async with session.begin():
                withdrawal_service = WithdrawalService(session)
                result = await withdrawal_service.get_user_withdrawals(
                    user.id, page=page, limit=10
                )

    withdrawals = result["withdrawals"]
    result["total"]
    total_pages = result["pages"]

    await state.update_data(withdrawal_page=page)

    if not withdrawals:
        await message.answer("📜 История выводов пуста")
        return

    text = f"📜 *История выводов* (Страница {page}/{total_pages})\n\n"

    for tx in withdrawals:
        status_icon = {
            "PENDING": "⏳",
            "PROCESSING": "⚙️",
            "COMPLETED": "✅",
            "FAILED": "❌",
            "REJECTED": "🚫"
        }.get(tx.status, "❓")

        date = tx.created_at.strftime("%d.%m.%Y %H:%M")
        net_amount = tx.amount - tx.fee
        text += f"{status_icon} *{tx.amount} USDT* (комиссия: {tx.fee}, получено: {net_amount}) | {date}\n"
        text += f"ID: `{tx.id}`\n"
        if tx.tx_hash:
            text += f"🔗 [BscScan](https://bscscan.com/tx/{tx.tx_hash})\n"
        text += "───────────────────\n"

    # Pagination keyboard would go here (omitted for brevity, assume simple list)
    await message.answer(text, parse_mode="Markdown")
