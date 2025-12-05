"""
Deposit Level Actions Handler

Handles deposit level modification actions:
- Change maximum open level
- Enable/disable individual levels
- Confirm level status changes
- Notify admins of level changes
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.deposit_level_version_repository import (
    DepositLevelVersionRepository,
)
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_deposit_level_actions_keyboard,
    admin_deposit_levels_keyboard,
    admin_deposit_management_keyboard,
    cancel_keyboard,
)
from bot.states.admin import AdminDepositManagementStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

router = Router(name="admin_deposit_management_actions")


@router.message(F.text == "🔢 Изм. макс. уровень")
async def start_max_level_change(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start max level change flow.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    global_settings_repo = GlobalSettingsRepository(session)
    settings = await global_settings_repo.get_settings()
    current_max = settings.max_open_deposit_level

    await state.set_state(AdminDepositManagementStates.setting_max_level)

    await message.answer(
        f"🔢 **Изменение максимального уровня**\n\n"
        f"Текущий макс. уровень: **{current_max}**\n\n"
        "Введите новое значение (1-5):\n"
        "Пользователи смогут открывать депозиты только до этого уровня включительно.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminDepositManagementStates.setting_max_level)
async def process_max_level_change(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process max level input.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        from bot.handlers.admin.deposit_management.levels import show_levels_management
        await show_levels_management(message, session, **data)
        return

    try:
        new_max = int(message.text.strip())
        if new_max < 1 or new_max > 5:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите число от 1 до 5.",
            reply_markup=cancel_keyboard(),
        )
        return

    # Get admin info for logging (admin is already in data from middleware)
    admin = data.get("admin")
    admin_info = f"admin {admin.telegram_id}" if admin else "unknown admin"

    global_settings_repo = GlobalSettingsRepository(session)
    await global_settings_repo.update_settings(max_open_deposit_level=new_max)
    await session.commit()

    logger.info(f"Max open deposit level changed to {new_max} by {admin_info}")

    await message.answer(
        f"✅ Максимальный уровень успешно изменён на **{new_max}**.",
        parse_mode="Markdown",
    )

    await clear_state_preserve_admin_token(state)
    from bot.handlers.admin.deposit_management.levels import show_levels_management
    await show_levels_management(message, session, **data)


@router.message(AdminDepositManagementStates.managing_level)
async def process_level_action(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process level management action.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Check for back button
    if message.text in ["◀️ Назад", "◀️ Назад к уровням"]:
        await clear_state_preserve_admin_token(state)
        from bot.handlers.admin.deposit_management.levels import show_levels_management
        await show_levels_management(message, session, **data)
        return

    # Check for ROI corridor management button
    if message.text == "💰 Настроить коридор доходности":
        # Redirect to ROI corridor handler
        from bot.handlers.admin.roi_corridor import show_level_roi_config
        state_data = await state.get_data()
        level = state_data.get("managing_level")
        if level:
            await clear_state_preserve_admin_token(state)
            await show_level_roi_config(message, session, state, level, from_level_management=True, **data)
        return

    # Get level from state
    state_data = await state.get_data()
    level = state_data.get("managing_level")

    if not level:
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Ошибка: уровень не найден.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    version_repo = DepositLevelVersionRepository(session)
    current_version = await version_repo.get_current_version(level)

    if not current_version:
        await clear_state_preserve_admin_token(state)
        await message.answer(
            f"❌ Уровень {level} не найден.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Process action with explicit confirmation
    if message.text in ("✅ Включить уровень", "❌ Отключить уровень"):
        target_status = (
            "enable" if message.text == "✅ Включить уровень" else "disable"
        )
        status_text = "ВКЛЮЧИТЬ" if target_status == "enable" else "ОТКЛЮЧИТЬ"

        await state.update_data(
            level_action=target_status,
            level_current_active=current_version.is_active,
        )
        await state.set_state(
            AdminDepositManagementStates.confirming_level_status
        )

        await message.answer(
            "⚠️ Подтверждение\n\n"
            f"Вы хотите {status_text} уровень {level}?\n\n"
            "❗️ ВАЖНО:\n"
            "• При включении пользователи смогут создавать новые депозиты "
            "этого уровня\n"
            "• При отключении новые депозиты этого уровня создавать нельзя, "
            "но существующие продолжат работать\n\n"
            "Подтвердите действие (Да/Нет).",
            reply_markup=cancel_keyboard(),
        )
        return

    await message.answer(
        "❌ Неизвестное действие.",
        reply_markup=admin_deposit_level_actions_keyboard(
            level, current_version.is_active
        ),
    )


@router.message(AdminDepositManagementStates.confirming_level_status)
async def confirm_level_status_change(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Confirm enabling/disabling a deposit level.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Handle cancellation
    if message.text in ("❌ Отмена", "◀️ Назад", "◀️ Назад к уровням"):
        await clear_state_preserve_admin_token(state)
        from bot.handlers.admin.deposit_management.levels import show_levels_management
        await show_levels_management(message, session, **data)
        return

    normalized = (message.text or "").strip().lower()
    if normalized not in ("да", "yes", "✅ да"):
        # Treat anything other than explicit "yes" as cancellation
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=admin_deposit_levels_keyboard(),
        )
        return

    state_data = await state.get_data()
    level = state_data.get("managing_level")
    action = state_data.get("level_action")

    if not level or action not in ("enable", "disable"):
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Ошибка: данные уровня не найдены.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    version_repo = DepositLevelVersionRepository(session)
    current_version = await version_repo.get_current_version(level)

    if not current_version:
        await clear_state_preserve_admin_token(state)
        await message.answer(
            f"❌ Уровень {level} не найден.",
            reply_markup=admin_deposit_management_keyboard(),
        )
        return

    # Apply status change
    if action == "enable":
        current_version.is_active = True
        status_msg = "✅ Уровень {level} включён!"
        notify_action = "включён"
    else:
        current_version.is_active = False
        status_msg = "❌ Уровень {level} отключён!"
        notify_action = "отключён"

    await session.commit()

    await message.answer(
        status_msg.format(level=level),
        reply_markup=admin_deposit_levels_keyboard(),
    )

    # Notify other admins about level status change
    try:
        from app.repositories.admin_repository import AdminRepository
        from bot.utils.notification import send_telegram_message

        admin_id = admin.id if admin else None
        admin_repo = AdminRepository(session)
        all_admins = await admin_repo.get_extended_admins()

        notification_text = (
            "🔔 **Изменён статус уровня депозитов**\n\n"
            f"**Уровень:** {level}\n"
            f"**Статус:** {notify_action}\n"
        )
        if admin_id:
            notification_text += f"**Изменил:** Admin ID {admin_id}"

        for other_admin in all_admins:
            if admin_id and other_admin.id == admin_id:
                continue
            try:
                await send_telegram_message(other_admin.telegram_id, notification_text)
            except Exception as e:
                logger.error(
                    "Failed to notify admin about level status change",
                    extra={"admin_id": other_admin.id, "error": str(e)},
                )
    except Exception as e:
        logger.error(
            "Failed to notify admins about level status change",
            extra={"error": str(e)},
        )

    await clear_state_preserve_admin_token(state)
