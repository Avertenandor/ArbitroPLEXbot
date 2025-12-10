"""
Admin Deletion Handlers.

Handles the deletion of admin accounts with proper validation.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_log_service import AdminLogService
from app.services.admin_service import AdminService
from app.validators.common import validate_telegram_id
from bot.handlers.admin.utils.admin_checks import (
    format_role_display,
    get_admin_or_deny,
    is_last_super_admin,
)
from bot.keyboards.reply import admin_management_keyboard, cancel_keyboard
from bot.states.admin import AdminManagementStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .router import router


@router.message(F.text == "🗑️ Удалить админа")
async def handle_delete_admin(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start admin deletion process.

    Only accessible to super_admin.
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    # Get all admins
    admin_service = AdminService(session)
    admins = await admin_service.list_all_admins()

    if not admins:
        await message.answer("📋 Список админов пуст")
        return

    # Check if this is the last super_admin
    if is_last_super_admin(admin, admins):
        await message.answer(
            "❌ Нельзя удалить последнего супер-администратора"
        )
        return

    text = "🗑️ **Удаление админа**\n\n"
    text += "Введите Telegram ID админа для удаления:\n\n"
    text += "**Список админов:**\n"

    for idx, a in enumerate(admins, 1):
        role_display = await format_role_display(a.role)

        text += f"{idx}. {a.display_name} (ID: `{a.telegram_id}`, {role_display})\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(AdminManagementStates.awaiting_admin_telegram_id)
    await state.update_data(action="delete")


async def handle_delete_admin_telegram_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle Telegram ID input for admin deletion.

    Args:
        message: Telegram message with Telegram ID
        session: Database session
        state: FSM context
        **data: Handler data
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        await clear_state_preserve_admin_token(state)
        return

    telegram_id_str = message.text.strip() if message.text else ""

    # Validate telegram_id using validator
    is_valid, telegram_id, error = validate_telegram_id(telegram_id_str)
    if not is_valid:
        await message.answer(
            f"❌ {error}\n\n"
            "Введите числовое значение:"
        )
        return

    # Get admin to delete
    admin_service = AdminService(session)
    admin_to_delete = await admin_service.get_admin_by_telegram_id(
        telegram_id
    )

    if not admin_to_delete:
        await message.answer(
            f"❌ Админ с Telegram ID {telegram_id} не найден."
        )
        await clear_state_preserve_admin_token(state)
        return

    # Check if trying to delete self
    if admin_to_delete.id == admin.id:
        await message.answer("❌ Нельзя удалить самого себя")
        await clear_state_preserve_admin_token(state)
        return

    # Check if trying to delete last super_admin
    all_admins = await admin_service.list_all_admins()
    if is_last_super_admin(admin_to_delete, all_admins):
        await message.answer(
            "❌ Нельзя удалить последнего супер-администратора"
        )
        await clear_state_preserve_admin_token(state)
        return

    # Delete admin
    deleted = await admin_service.delete_admin(admin_to_delete.id)

    if not deleted:
        await message.answer("❌ Ошибка при удалении админа")
        await clear_state_preserve_admin_token(state)
        return

    # Log admin deletion
    log_service = AdminLogService(session)
    await log_service.log_admin_deleted(
        admin=admin,
        deleted_admin_id=admin_to_delete.id,
        deleted_admin_telegram_id=telegram_id,
    )

    await clear_state_preserve_admin_token(state)

    logger.info(
        f"Admin {admin.id} deleted admin {admin_to_delete.id} "
        f"(telegram_id={telegram_id})"
    )

    await message.answer(
        f"✅ **Админ удален**\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Имя: {admin_to_delete.display_name}",
        parse_mode="Markdown",
        reply_markup=admin_management_keyboard(),
    )
