"""
Level settings handler for detailed deposit level configuration.

Allows admins to:
- View and modify ROI settings for each level
- View and modify deposit corridors
- View history of changes
"""

import re
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_corridor_history_repository import (
    DepositCorridorHistoryRepository,
)
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from app.services.admin_log_service import AdminLogService
from bot.keyboards.reply import admin_deposit_management_keyboard


router = Router()


# Emoji mapping for levels
LEVEL_EMOJI = {
    "test": "🎯",
    "level_1": "💰",
    "level_2": "💎",
    "level_3": "🏆",
    "level_4": "👑",
    "level_5": "🚀",
}


@router.message(
    F.text.regexp(
        r"^настройки\s+(test|level_[1-5])$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def show_level_settings(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show detailed settings for a specific level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level type
    pattern = r"^настройки\s+(test|level_[1-5])$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `настройки <уровень>`\n"
            "Пример: `настройки test` или `настройки level_1`",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    level_type = match.group(1).lower()

    # Get level config
    config_repo = DepositLevelConfigRepository(session)
    level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    emoji = LEVEL_EMOJI.get(level_type, "📊")
    status_icon = "✅" if level_config.is_active else "❌"

    text = (
        f"{emoji} **{level_config.name}** {status_icon}\n\n"
        f"**Коридор сумм:**\n"
        f"Мин: ${level_config.min_amount:,.2f}\n"
        f"Макс: ${level_config.max_amount:,.2f}\n\n"
        f"**ROI настройки:**\n"
        f"Процент: {level_config.roi_percent}%/день\n"
        f"Кап: {level_config.roi_cap_percent}%\n\n"
        f"**PLEX:**\n"
        f"{level_config.plex_per_dollar} токенов за $1/сутки\n\n"
        f"**Команды:**\n"
        f"• `roi {level_type} <процент>` - изменить ROI\n"
        f"• `кап {level_type} <процент>` - изменить кап ROI\n"
        f"• `история {level_type}` - показать историю изменений\n\n"
        f"**Примеры:**\n"
        f"• `roi {level_type} 2.5`\n"
        f"• `кап {level_type} 600`"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(
    F.text.regexp(
        r"^roi\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def update_level_roi(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Update ROI percentage for a level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level type and ROI
    pattern = r"^roi\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `roi <уровень> <процент>`\n"
            "Пример: `roi level_1 2.5`",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    level_type = match.group(1).lower()
    roi_percent = Decimal(match.group(2))

    # Validate ROI
    if roi_percent <= 0 or roi_percent > 100:
        await message.answer(
            "❌ ROI должен быть от 0.01 до 100",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Get admin
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Get level config
    config_repo = DepositLevelConfigRepository(session)
    level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    old_roi = level_config.roi_percent

    # Update ROI
    await config_repo.update_roi_settings(
        level_type, roi_percent=roi_percent
    )
    await session.commit()

    # Log admin action
    log_service = AdminLogService(session)
    await log_service.log_action(
        admin_id=admin.id,
        action_type="UPDATE_LEVEL_ROI",
        details={
            "level_type": level_type,
            "old_roi": str(old_roi),
            "new_roi": str(roi_percent),
        },
    )
    await session.commit()

    emoji = LEVEL_EMOJI.get(level_type, "📊")
    await message.answer(
        f"✅ {emoji} ROI для {level_config.name} обновлен:\n"
        f"{old_roi}% → {roi_percent}%/день",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(
    F.text.regexp(
        r"^кап\s+(test|level_[1-5])\s+(\d+)$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def update_level_roi_cap(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Update ROI cap percentage for a level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level type and cap
    pattern = r"^кап\s+(test|level_[1-5])\s+(\d+)$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `кап <уровень> <процент>`\n"
            "Пример: `кап level_1 600`",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    level_type = match.group(1).lower()
    roi_cap_percent = int(match.group(2))

    # Validate cap
    if roi_cap_percent <= 0 or roi_cap_percent > 10000:
        await message.answer(
            "❌ Кап ROI должен быть от 1 до 10000",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Get admin
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Get level config
    config_repo = DepositLevelConfigRepository(session)
    level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    old_cap = level_config.roi_cap_percent

    # Update cap
    await config_repo.update_roi_settings(
        level_type, roi_cap_percent=roi_cap_percent
    )
    await session.commit()

    # Log admin action
    log_service = AdminLogService(session)
    await log_service.log_action(
        admin_id=admin.id,
        action_type="UPDATE_LEVEL_ROI_CAP",
        details={
            "level_type": level_type,
            "old_cap": old_cap,
            "new_cap": roi_cap_percent,
        },
    )
    await session.commit()

    emoji = LEVEL_EMOJI.get(level_type, "📊")
    await message.answer(
        f"✅ {emoji} Кап ROI для {level_config.name} обновлен:\n"
        f"{old_cap}% → {roi_cap_percent}%",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(
    F.text.regexp(
        r"^история\s+(test|level_[1-5])$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def show_level_history(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show change history for a level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    # Extract level type
    pattern = r"^история\s+(test|level_[1-5])$"
    match = re.match(pattern, message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `история <уровень>`\n"
            "Пример: `история level_1`",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    level_type = match.group(1).lower()

    # Get level config
    config_repo = DepositLevelConfigRepository(session)
    level_config = await config_repo.get_by_level_type(level_type)

    if not level_config:
        await message.answer(
            f"❌ Уровень {level_type} не найден",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Get change history (using corridor history as example)
    # Note: You might want to extend this to include all types of changes
    history_repo = DepositCorridorHistoryRepository(session)

    # Map level_type to level number for history query
    level_num_map = {
        "test": 0,
        "level_1": 1,
        "level_2": 2,
        "level_3": 3,
        "level_4": 4,
        "level_5": 5,
    }
    level_num = level_num_map.get(level_type, 0)

    history = await history_repo.get_history_for_level(level_num, limit=10)

    emoji = LEVEL_EMOJI.get(level_type, "📊")

    if not history:
        await message.answer(
            f"{emoji} **История изменений для {level_config.name}**\n\n"
            "История изменений пуста",
            parse_mode="Markdown",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Build history display
    history_lines = []
    for i, record in enumerate(history[:10], 1):
        date_str = record.changed_at.strftime("%d.%m.%Y %H:%M")

        if record.mode == "custom":
            change_text = (
                f"Коридор ROI: {record.roi_min}% - {record.roi_max}%"
            )
        else:
            change_text = f"Фиксированный ROI: {record.roi_fixed}%"

        applies_text = "текущим" if record.applies_to == "current" else "следующим"

        history_lines.append(
            f"{i}. {date_str}\n"
            f"   {change_text}\n"
            f"   Применяется к {applies_text} депозитам"
        )

    text = (
        f"{emoji} **История изменений для {level_config.name}**\n\n"
        + "\n\n".join(history_lines)
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )


@router.message(F.text == "📋 Все уровни")
async def show_all_levels_summary(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show summary of all deposit levels."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    config_repo = DepositLevelConfigRepository(session)
    levels = await config_repo.get_all_ordered()

    if not levels:
        await message.answer(
            "⚠️ Уровни депозитов не настроены",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Build summary
    summary_lines = []
    for level_config in levels:
        emoji = LEVEL_EMOJI.get(level_config.level_type, "📊")
        status = "✅" if level_config.is_active else "❌"

        summary_lines.append(
            f"{emoji} **{level_config.name}** {status}\n"
            f"   Коридор: ${level_config.min_amount:,.0f} - "
            f"${level_config.max_amount:,.0f}\n"
            f"   ROI: {level_config.roi_percent}%/день (кап: {level_config.roi_cap_percent}%)\n"
            f"   PLEX: {level_config.plex_per_dollar} токенов/$"
        )

    text = (
        "📋 **Обзор всех уровней депозитов**\n\n"
        + "\n\n".join(summary_lines)
        + "\n\n**Команды:**\n"
        "• `настройки <уровень>` - детальные настройки уровня"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_deposit_management_keyboard(),
    )
