"""Parameters handlers for deposit settings."""

import re
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from app.services.admin_log_service import AdminLogService
from bot.keyboards.reply import admin_deposit_settings_keyboard


router = Router()


@router.message(
    F.text.regexp(
        r"^коридор\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)$",
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
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    # Extract level type and amounts
    pattern = (
        r"^коридор\s+(test|level_[1-5])\s+(\d+(?:\.\d+)?)\s+"
        r"(\d+(?:\.\d+)?)$"
    )
    match = re.match(
        pattern,
        message.text.strip(),
        re.IGNORECASE | re.UNICODE
    )
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: "
            "`коридор <уровень> <мин> <макс>`\n"
            "Пример: `коридор test 30 100` или "
            "`коридор level_1 100 500`",
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
            "❌ Минимальная сумма должна быть меньше "
            "максимальной",
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
    from .display import show_deposit_settings
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
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    # Extract PLEX rate
    pattern = r"^plex\s+(\d+)$"
    match = re.match(
        pattern,
        message.text.strip(),
        re.IGNORECASE | re.UNICODE
    )
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
        await config_repo.update_plex_rate(
            level_config.level_type,
            plex_rate
        )
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
        f"✅ PLEX обновлен для всех уровней: "
        f"{plex_rate} токенов/сутки",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    from .display import show_deposit_settings
    await show_deposit_settings(message, session, **data)
