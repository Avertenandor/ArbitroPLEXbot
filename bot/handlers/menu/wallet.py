"""
Wallet menu handlers.

This module contains handlers for displaying user wallet information and history.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_wallet_history import UserWalletHistory
from bot.keyboards.reply import wallet_menu_keyboard
from bot.utils.formatters import format_wallet_short
from bot.utils.user_context import get_user_from_context


router = Router()


@router.message(StateFilter('*'), F.text == "💳 Мой кошелек")
async def show_my_wallet(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show user wallet."""
    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    # Get wallet history
    stmt = select(UserWalletHistory).where(
        UserWalletHistory.user_id == user.id
    ).order_by(desc(UserWalletHistory.changed_at)).limit(5)
    result = await session.execute(stmt)
    history = result.scalars().all()

    text = (
        f"💳 *Мой кошелек*\n\n"
        f"📍 Текущий адрес:\n`{user.wallet_address}`\n\n"
    )

    if history:
        text += "📜 *История изменений:*\n"
        for h in history:
            old_short = format_wallet_short(h.old_wallet_address)
            new_short = format_wallet_short(h.new_wallet_address)
            date_str = h.changed_at.strftime("%d.%m.%Y %H:%M")
            text += f"• {date_str}\n  `{old_short}` → `{new_short}`\n"
        text += "\n"

    text += "⚠️ Сохраните приватный ключ в безопасном месте!"

    await message.answer(text, parse_mode="Markdown", reply_markup=wallet_menu_keyboard())
