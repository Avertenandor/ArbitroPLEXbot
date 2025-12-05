"""
Admin User Transaction History Handler
Displays transaction history for a selected user
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction

router = Router(name="admin_users_transactions")


@router.message(F.text == "📜 История транзакций")
async def handle_profile_history(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Show transaction history"""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        return

    stmt = (
        select(Transaction).where(Transaction.user_id == user_id)
        .order_by(desc(Transaction.created_at)).limit(10)
    )
    result = await session.execute(stmt)
    txs = result.scalars().all()

    if not txs:
        await message.answer("📜 История транзакций пуста.")
        return

    text = "📜 **Последние 10 транзакций:**\n\n"
    for tx in txs:
        status_map = {
            "confirmed": "✅",
            "pending": "⏳",
            "failed": "❌",
            "rejected": "🚫"
        }
        status = status_map.get(tx.status, "❓")
        text += (
            f"{status} `{tx.created_at.strftime('%d.%m %H:%M')}`: "
            f"{tx.type} **{tx.amount} USDT**\n"
        )
        if tx.tx_hash:
            text += f"   🔗 `{tx.tx_hash}`\n"

    await message.answer(text, parse_mode="Markdown")
