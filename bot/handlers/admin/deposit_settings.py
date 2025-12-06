"""
Deposit settings handler.

Allows admins to configure max open deposit level and manage level availability.
R17-2: Temporary level deactivation via is_active flag.
Enhanced with deposit corridors and PLEX rate management.
"""

import re
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.services.admin_log_service import AdminLogService
from bot.keyboards.reply import admin_deposit_settings_keyboard

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
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    if not levels:
        await message.answer(
            "⚠️ Уровни депозитов не настроены",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Emoji mapping for levels
    level_emoji = {
        "test": "🎯",
        "level_1": "💰",
        "level_2": "💎",
        "level_3": "🏆",
        "level_4": "👑",
        "level_5": "🚀",
    }

    # Build level display
    levels_display = []
    plex_rate = None

    for level_config in levels:
        emoji = level_emoji.get(level_config.level_type, "📊")
        status = "✅" if level_config.is_active else "❌"
        levels_display.append(
            f"{emoji} {level_config.name}: "
            f"${level_config.min_amount:,.0f} - ${level_config.max_amount:,.0f} {status}"
        )
        # Get PLEX rate (assuming it's the same for all levels)
        if plex_rate is None:
            plex_rate = level_config.plex_per_dollar

    text = (
        "⚙️ **Настройки уровней депозитов**\n\n"
        + "\n".join(levels_display)
        + f"\n\nPLEX за $1: {plex_rate} токенов/сутки\n\n"
        "**Команды управления:**\n"
        "• `коридор <уровень> <мин> <макс>` - изменить коридор\n"
        "• `включить <уровень>` - включить уровень\n"
        "• `отключить <уровень>` - отключить уровень\n"
        "• `plex <значение>` - изменить PLEX за $1\n"
        "• `статистика депозитов` - статистика по уровням\n\n"
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


@router.message(F.text.regexp(r"^уровень\s+(\d+)$", flags=re.IGNORECASE | re.UNICODE))
async def set_max_deposit_level(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Set max deposit level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level from message text
    match = re.match(r"^уровень\s+(\d+)$", message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `уровень <номер>` (1-5)",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    level = int(match.group(1))

    if level < 1 or level > 5:
        await message.answer(
            "❌ Уровень должен быть от 1 до 5",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Get admin
    from app.repositories.admin_repository import AdminRepository

    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    settings_repo = GlobalSettingsRepository(session)
    await settings_repo.update_settings(max_open_deposit_level=level)
    await session.commit()

    await message.answer(
        f"✅ Максимальный уровень установлен: {level}",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    await show_deposit_settings(message, session, **data)


@router.message(
    F.text.regexp(
        r"^(включить|отключить)\s+(test|level_[1-5])$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def toggle_level_availability(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle level availability."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract action and level type
    pattern = r"^(включить|отключить)\s+(test|level_[1-5])$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `включить <уровень>` или `отключить <уровень>`\n"
            "Пример: `включить level_2` или `отключить test`",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    action = match.group(1).lower()
    level_type = match.group(2).lower()

    # Get admin
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Get level config
    config_repo = DepositLevelConfigRepository(session)
    level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден.",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Toggle is_active
    new_status = action == "включить"

    if new_status:
        await config_repo.activate_level(level_type)
    else:
        await config_repo.deactivate_level(level_type)

    await session.commit()

    # Log admin action
    log_service = AdminLogService(session)
    await log_service.log_action(
        admin_id=admin.id,
        action_type="TOGGLE_DEPOSIT_LEVEL",
        details={
            "level_type": level_type,
            "action": action,
            "new_status": new_status,
        },
    )
    await session.commit()

    status_text = "включен" if new_status else "отключен"
    await message.answer(
        f"✅ Уровень {level_config.name} {status_text}",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    await show_deposit_settings(message, session, **data)


@router.message(
    F.text.regexp(
        r"^коридор\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def update_corridor(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Update deposit corridor for a level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level type and amounts
    pattern = r"^коридор\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `коридор <уровень> <мин> <макс>`\n"
            "Пример: `коридор test 30 100` или `коридор level_1 100 500`",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    level_type = match.group(1).lower()
    min_amount = Decimal(match.group(2))
    max_amount = Decimal(match.group(3))

    # Validate amounts
    if min_amount <= 0 or max_amount <= 0:
        await message.answer(
            "❌ Суммы должны быть больше нуля",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    if min_amount >= max_amount:
        await message.answer(
            "❌ Минимальная сумма должна быть меньше максимальной",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Get admin
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Update corridor
    config_repo = DepositLevelConfigRepository(session)
    updated_config = await config_repo.update_corridor(
        level_type, min_amount, max_amount
    )

    if not updated_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    await session.commit()

    # Log admin action
    log_service = AdminLogService(session)
    await log_service.log_action(
        admin_id=admin.id,
        action_type="UPDATE_DEPOSIT_CORRIDOR",
        details={
            "level_type": level_type,
            "old_min": str(updated_config.min_amount),
            "old_max": str(updated_config.max_amount),
            "new_min": str(min_amount),
            "new_max": str(max_amount),
        },
    )
    await session.commit()

    await message.answer(
        f"✅ Коридор для {updated_config.name} обновлен:\n"
        f"${min_amount:,.0f} - ${max_amount:,.0f}",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    await show_deposit_settings(message, session, **data)


@router.message(
    F.text.regexp(
        r"^plex\s+(\d+)$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def update_plex_rate(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Update PLEX rate for all levels."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract PLEX rate
    pattern = r"^plex\s+(\d+)$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `plex <значение>`\n"
            "Пример: `plex 15`",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    plex_rate = int(match.group(1))

    if plex_rate <= 0:
        await message.answer(
            "❌ PLEX должен быть больше нуля",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Get admin
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    # Update PLEX rate for all levels
    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    updated_count = 0
    for level_config in levels:
        await config_repo.update_plex_rate(level_config.level_type, plex_rate)
        updated_count += 1

    await session.commit()

    # Log admin action
    log_service = AdminLogService(session)
    await log_service.log_action(
        admin_id=admin.id,
        action_type="UPDATE_PLEX_RATE",
        details={
            "new_plex_rate": plex_rate,
            "levels_updated": updated_count,
        },
    )
    await session.commit()

    await message.answer(
        f"✅ PLEX обновлен для всех уровней: {plex_rate} токенов/сутки",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    await show_deposit_settings(message, session, **data)


@router.message(F.text == "📊 Статистика депозитов")
@router.message(F.text.regexp(r"^статистика\s+депозитов$", flags=re.IGNORECASE | re.UNICODE))
async def show_deposit_statistics(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show deposit statistics by level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    # Emoji mapping for levels
    level_emoji = {
        "test": "🎯",
        "level_1": "💰",
        "level_2": "💎",
        "level_3": "🏆",
        "level_4": "👑",
        "level_5": "🚀",
    }

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

        emoji = level_emoji.get(level_config.level_type, "📊")
        stats_lines.append(
            f"{emoji} {level_config.name}: "
            f"{active_count} активных, ${level_total:,.2f}"
        )

    text = (
        "📊 **Статистика депозитов по уровням**\n\n"
        + "\n".join(stats_lines)
        + f"\n\n**Итого:** {total_active} активных депозитов, ${total_amount:,.2f}"
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
        await message.answer("❌ Эта функция доступна только администраторам")
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
            f"   Коридор: ${level_config.min_amount:,.0f} - ${level_config.max_amount:,.0f}\n"
            f"   ROI: {level_config.roi_percent}%/день\n"
            f"   Кап: {level_config.roi_cap_percent}%\n"
            f"   PLEX: {level_config.plex_per_dollar} токенов/$"
        )

    text = "📊 **Статус уровней депозитов**\n\n" + "\n\n".join(status_lines)

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_settings_keyboard(),
    )


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from deposit settings menu"""
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
