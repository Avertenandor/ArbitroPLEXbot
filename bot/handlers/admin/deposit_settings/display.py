"""Display handlers for deposit settings."""

import re
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from bot.keyboards.reply import admin_deposit_settings_keyboard
from bot.utils.formatters import format_balance

from .constants import LEVEL_EMOJI


router = Router()


@router.message(F.text == "⚙️ Настроить уровни депозитов")
async def show_deposit_settings(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show deposit settings with corridors and PLEX rates."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    if not levels:
        await message.answer(
            "⚠️ Уровни депозитов не настроены",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Build level display
    levels_display = []
    plex_rate = None

    for level_config in levels:
        emoji = LEVEL_EMOJI.get(level_config.level_type, "📊")
        status = "✅" if level_config.is_active else "❌"
        levels_display.append(
            f"{emoji} {level_config.name}: "
            f"${level_config.min_amount:,.0f} - "
            f"${level_config.max_amount:,.0f} {status}"
        )
        # Get PLEX rate (assuming it's the same for all levels)
        if plex_rate is None:
            plex_rate = level_config.plex_per_dollar

    text = (
        "⚙️ **Настройки уровней депозитов**\n\n"
        + "\n".join(levels_display)
        + f"\n\nPLEX за $1: {plex_rate} токенов/сутки\n\n"
        "**Команды управления:**\n"
        "• `коридор <уровень> <мин> <макс>` - "
        "изменить коридор\n"
        "• `включить <уровень>` - включить уровень\n"
        "• `отключить <уровень>` - отключить уровень\n"
        "• `plex <значение>` - изменить PLEX за $1\n"
        "• `статистика депозитов` - "
        "статистика по уровням\n\n"
        "**Примеры:**\n"
        "• `коридор test 30 100`\n"
        "• `коридор level_1 100 500`\n"
        "• `включить level_2`\n"
        "• `plex 15`"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_settings_keyboard(),
    )


@router.message(F.text == "📊 Статистика депозитов")
@router.message(
    F.text.regexp(
        r"^статистика\s+депозитов$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def show_deposit_statistics(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show deposit statistics by level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    stats_lines = []
    total_active = 0
    total_amount = Decimal("0")

    for level_config in levels:
        # Get active deposits count and sum for this level type
        stmt = (
            select(
                func.count(Deposit.id).label("count"),
                func.coalesce(func.sum(Deposit.amount), 0).label("total")
            )
            .where(Deposit.deposit_type == level_config.level_type)
            .where(Deposit.is_roi_completed == False)  # noqa: E712
            .where(Deposit.status == "confirmed")
        )
        result = await session.execute(stmt)
        row = result.first()

        active_count = row.count if row else 0
        level_total = Decimal(str(row.total)) if row else Decimal("0")

        total_active += active_count
        total_amount += level_total

        emoji = LEVEL_EMOJI.get(level_config.level_type, "📊")
        stats_lines.append(
            f"{emoji} {level_config.name}: "
            f"{active_count} активных, ${format_balance(level_total, decimals=2)}"
        )

    text = (
        "📊 **Статистика депозитов по уровням**\n\n"
        + "\n".join(stats_lines)
        + f"\n\n**Итого:** {total_active} активных депозитов, "
        f"${format_balance(total_amount, decimals=2)}"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_settings_keyboard(),
    )


@router.message(F.text == "📊 Статус уровней")
@router.message(F.text.regexp(r"^статус\s+уровней$", flags=0))
async def show_level_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show detailed status of all levels."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    if not levels:
        await message.answer(
            "⚠️ Уровни депозитов не настроены",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    status_lines = []
    for level_config in levels:
        status_icon = "✅" if level_config.is_active else "❌"
        status_text = "Активен" if level_config.is_active else "Отключен"
        status_lines.append(
            f"{status_icon} **{level_config.name}**: {status_text}\n"
            f"   Коридор: ${level_config.min_amount:,.0f} - "
            f"${level_config.max_amount:,.0f}\n"
            f"   ROI: {level_config.roi_percent}%/день\n"
            f"   Кап: {level_config.roi_cap_percent}%\n"
            f"   PLEX: {level_config.plex_per_dollar} токенов/$"
        )

    text = (
        "📊 **Статус уровней депозитов**\n\n"
        + "\n\n".join(status_lines)
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_settings_keyboard(),
    )
