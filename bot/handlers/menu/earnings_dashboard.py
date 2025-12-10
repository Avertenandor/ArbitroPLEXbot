"""
Earnings dashboard handler.

Displays detailed earnings statistics including:
- Period-based earnings (today, week, month)
- Total earnings, pending, and available balance
- ROI progress for all deposit levels
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.earnings_stats_service import EarningsStatsService
from bot.keyboards.user import earnings_dashboard_keyboard
from bot.utils.formatters import format_usdt
from bot.utils.user_loader import UserLoader


router = Router()


def _format_progress_bar(percent: float, width: int = 10) -> str:
    """
    Format progress bar for ROI display.

    Args:
        percent: Progress percentage (0-100)
        width: Width of progress bar in characters

    Returns:
        Progress bar string with filled and empty blocks
    """
    filled = round((percent / 100) * width)
    empty = width - filled
    return "█" * filled + "░" * empty


@router.message(StateFilter('*'), F.text == "📈 Мой заработок")
async def show_earnings_dashboard(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show earnings dashboard with detailed statistics.

    Displays:
    - Period earnings (today, week, month)
    - Total earned, pending, available balance
    - ROI progress for all deposit levels with progress bars
    """
    telegram_id = message.from_user.id if message.from_user else None
    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    # Show loading message
    status_msg = await message.answer("⏳ Загружаю статистику заработка...")

    try:
        # Get earnings statistics
        earnings_service = EarningsStatsService(session)
        stats = await earnings_service.get_full_earnings_stats(user.id)

        if not stats:
            await status_msg.delete()
            await message.answer(
                "❌ Не удалось загрузить статистику заработка. "
                "Попробуйте позже."
            )
            return

        # Format period earnings
        today = format_usdt(stats.get("today", 0))
        week = format_usdt(stats.get("week", 0))
        month = format_usdt(stats.get("month", 0))

        # Format balances
        total_earned = format_usdt(stats.get("total_earned", 0))
        pending = format_usdt(stats.get("pending_earnings", 0))
        available = format_usdt(stats.get("available_balance", 0))
        total_paid = format_usdt(stats.get("total_paid", 0))

        # Build message
        text = (
            f"📈 *МОЙ ЗАРАБОТОК*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Сегодня: *+{today} USDT*\n"
            f"📊 За неделю: *+{week} USDT*\n"
            f"📅 За месяц: *+{month} USDT*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Всего заработано: *{total_earned} USDT*\n"
            f"⏳ Ожидает вывода: {pending} USDT\n"
            f"💵 Доступно сейчас: *{available} USDT*\n"
            f"💸 Уже выплачено: {total_paid} USDT\n"
        )

        # Add ROI progress section
        roi_progress = stats.get("roi_progress", [])
        if roi_progress:
            text += "━━━━━━━━━━━━━━━━━━━━\n📊 *ROI прогресс:*\n\n"

            for roi in roi_progress:
                level = roi.get("level", 0)
                roi_percent = roi.get("roi_percent", 0)
                roi_paid = format_usdt(roi.get("roi_paid", 0))
                roi_cap = format_usdt(roi.get("roi_cap", 0))

                # Format progress bar
                progress_bar = _format_progress_bar(roi_percent)

                text += (
                    f"*Level {level}:* {progress_bar} {roi_percent:.0f}%\n"
                    f"└ {roi_paid}/{roi_cap} USDT\n\n"
                )

            text += "━━━━━━━━━━━━━━━━━━━━\n"
        else:
            text += (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📊 *ROI прогресс:*\n"
                "У вас пока нет активных депозитов\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

        text += (
            "\n💡 *Как увеличить заработок?*\n"
            "• Активируйте новые уровни депозитов\n"
            "• Приглашайте рефералов\n"
            "• Держите достаточно PLEX на балансе"
        )

        # Delete loading message and send final result with keyboard
        await status_msg.delete()
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=earnings_dashboard_keyboard()
        )

    except Exception as e:
        logger.error(
            f"Failed to show earnings dashboard for user {user.id}: {e}",
            exc_info=True,
        )
        try:
            await status_msg.delete()
        except Exception:
            pass
        await message.answer(
            "❌ Произошла ошибка при загрузке статистики. Попробуйте позже."
        )


@router.message(StateFilter('*'), F.text.in_(["💰 Мой заработок"]))
async def show_earnings_from_referral_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show earnings dashboard when accessed from referral menu.

    This is the same as the main earnings dashboard but can be accessed
    from the referral menu as well.
    """
    await show_earnings_dashboard(message, session, **data)
