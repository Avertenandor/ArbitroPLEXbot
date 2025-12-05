"""
Deposits listing handlers.

This module contains handlers for displaying user's active deposits with ROI progress.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.deposit_service import DepositService
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.formatters import format_usdt

router = Router()


@router.message(StateFilter('*'), F.text == "📦 Мои депозиты")
async def show_my_deposits(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show user's active deposits.

    Args:
        message: Telegram message
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    deposit_service = DepositService(session)

    # Get active deposits
    active_deposits = await deposit_service.get_active_deposits(user.id)

    if not active_deposits:
        is_admin = data.get("is_admin", False)
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        await message.answer(
            "📦 *Мои депозиты*\n\n"
            "У вас пока нет активных депозитов.\n\n"
            "Создайте депозит через меню '💰 Депозит'.",
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    # Build deposits list
    text = "📦 *Мои депозиты*\n\n"

    for deposit in active_deposits:
        # Calculate ROI progress
        roi_paid = float(getattr(deposit, "roi_paid_amount", 0) or 0)
        roi_cap = float(getattr(deposit, "roi_cap_amount", 0) or 0)

        if roi_cap > 0:
            roi_percent = (roi_paid / roi_cap) * 100
            roi_status = f"{roi_percent:.1f}%"
            # Progress bar (10 chars)
            filled = int(roi_percent / 10)
            empty = 10 - filled
            progress_bar = "█" * filled + "░" * empty
        else:
            roi_status = "0%"
            progress_bar = "░" * 10

        # Check if completed
        is_completed = getattr(deposit, "is_roi_completed", False)
        status_emoji = "✅" if is_completed else "🟢"
        status_text = "Закрыт (ROI 500%)" if is_completed else "Активен"

        created_date = deposit.created_at.strftime("%d.%m.%Y %H:%M")
        remaining = roi_cap - roi_paid

        text += (
            f"{status_emoji} *Уровень {deposit.level}*\n"
            f"💰 Сумма: {format_usdt(deposit.amount)} USDT\n"
            f"📊 ROI: `{progress_bar}` {roi_status}\n"
            f"✅ Получено: {format_usdt(roi_paid)} USDT\n"
            f"⏳ Осталось: {format_usdt(remaining)} USDT\n"
            f"📅 Создан: {created_date}\n"
            f"📋 Статус: {status_text}\n"
            f"─────────────────────────────\n\n"
        )

    is_admin = data.get("is_admin", False)
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )
