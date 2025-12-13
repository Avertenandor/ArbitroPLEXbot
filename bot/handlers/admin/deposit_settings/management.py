"""Management handlers for deposit settings."""

import re
from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_level_config_repository import (
    DepositLevelConfigRepository,
)
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.services.admin_log_service import AdminLogService
from bot.keyboards.reply import admin_deposit_settings_keyboard


router = Router()


@router.message(
    F.text.regexp(
        r"^уровень\s+(\d+)$",
        flags=re.IGNORECASE | re.UNICODE
    )
)
async def set_max_deposit_level(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Set max deposit level."""
    is_admin = data.get("is_admin", False)
    if not is_admin:
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    # Extract level from message text
    match = re.match(
        r"^уровень\s+(\d+)$",
        message.text.strip(),
        re.IGNORECASE | re.UNICODE
    )
    if not match:
        await message.answer(
            "❌ Неверный формат. "
            "Используйте: `уровень <номер>` (1-5)",
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
    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by(telegram_id=message.from_user.id)

    if not admin:
        await message.answer(
            "❌ Администратор не найден",
            reply_markup=admin_deposit_settings_keyboard(),
        )
        return

    redis_client = data.get("redis_client")
    settings_repo = GlobalSettingsRepository(session, redis_client)
    await settings_repo.update_settings(max_open_deposit_level=level)
    await session.commit()

    await message.answer(
        f"✅ Максимальный уровень установлен: {level}",
        reply_markup=admin_deposit_settings_keyboard(),
    )

    # Refresh display
    from .display import show_deposit_settings
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
        await message.answer(
            "❌ Эта функция доступна только администраторам"
        )
        return

    # Extract action and level type
    pattern = r"^(включить|отключить)\s+(test|level_[1-5])$"
    match = re.match(
        pattern,
        message.text.strip(),
        re.IGNORECASE | re.UNICODE
    )
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: "
            "`включить <уровень>` или `отключить <уровень>`\n"
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
    from .display import show_deposit_settings
    await show_deposit_settings(message, session, **data)
