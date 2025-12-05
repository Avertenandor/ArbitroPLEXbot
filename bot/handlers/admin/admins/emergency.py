"""
Emergency Admin Block Handlers.

Handles emergency blocking of compromised admin accounts.
This includes blacklisting, deletion, and user banning.
"""

from typing import Any

from aiogram import F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.blacklist import BlacklistActionType
from app.repositories.user_repository import UserRepository
from app.services.admin_log_service import AdminLogService
from app.services.admin_service import AdminService
from app.services.blacklist_service import BlacklistService
from app.utils.admin_notifications import notify_security_event
from app.utils.security_logging import log_security_event
from app.validators.common import validate_telegram_id
from bot.handlers.admin.utils.admin_checks import (
    format_role_display,
    get_admin_or_deny,
    is_last_super_admin,
)
from bot.keyboards.reply import cancel_keyboard, admin_management_keyboard
from bot.states.admin import AdminManagementStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .router import router


@router.message(F.text == "🛑 Экстренно заблокировать админа")
async def handle_emergency_block_admin(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start emergency admin blocking process.

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
            "❌ Нельзя заблокировать последнего супер-администратора"
        )
        return

    text = (
        "🛑 **Экстренная блокировка админа**\n\n"
        "⚠️ **ВНИМАНИЕ:** Это действие:\n"
        "• Удалит админа из системы\n"
        "• Заблокирует его Telegram ID (TERMINATED)\n"
        "• Деактивирует все его сессии\n"
        "• Заблокирует его как пользователя (если есть)\n\n"
        "Введите Telegram ID админа для экстренной блокировки:\n\n"
        "**Список админов:**\n"
    )

    for idx, a in enumerate(admins, 1):
        role_display = await format_role_display(a.role)

        text += f"{idx}. {a.display_name} (ID: `{a.telegram_id}`, {role_display})\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(AdminManagementStates.awaiting_emergency_telegram_id)


@router.message(AdminManagementStates.awaiting_emergency_telegram_id)
async def handle_emergency_block_admin_telegram_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle Telegram ID input for emergency admin blocking.

    Performs atomic operation:
    1. Add to blacklist (TERMINATED)
    2. Delete admin
    3. Ban user if exists
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

    # Get admin to block
    admin_service = AdminService(session)
    admin_to_block = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin_to_block:
        await message.answer(
            f"❌ Админ с Telegram ID {telegram_id} не найден."
        )
        await clear_state_preserve_admin_token(state)
        return

    # Check if trying to block self
    if admin_to_block.id == admin.id:
        await message.answer("❌ Нельзя заблокировать самого себя")
        await clear_state_preserve_admin_token(state)
        return

    # Check if trying to block last super_admin
    all_admins = await admin_service.list_all_admins()
    if is_last_super_admin(admin_to_block, all_admins):
        await message.answer(
            "❌ Нельзя заблокировать последнего супер-администратора"
        )
        await clear_state_preserve_admin_token(state)
        return

    # Atomic operation: block and delete
    try:
        # 1. Add to blacklist (TERMINATED)
        blacklist_service = BlacklistService(session)
        blacklist_entry = await blacklist_service.add_to_blacklist(
            telegram_id=telegram_id,
            reason="Compromised admin account",
            added_by_admin_id=admin.id,
            action_type=BlacklistActionType.TERMINATED,
        )

        # 2. Delete admin (deactivates all sessions)
        deleted = await admin_service.delete_admin(admin_to_block.id)

        if not deleted:
            await message.answer("❌ Ошибка при удалении админа")
            await clear_state_preserve_admin_token(state)
            return

        # 3. Ban user if exists
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if user:
            user.is_banned = True
            await session.flush()

        # Commit all changes atomically
        await session.commit()

        # Log emergency block
        log_service = AdminLogService(session)
        await log_service.log_action(
            admin_id=admin.id,
            action_type="ADMIN_TERMINATED",
            target_user_id=user.id if user else None,
            details={
                "terminated_admin_id": admin_to_block.id,
                "terminated_admin_telegram_id": telegram_id,
                "terminated_admin_role": admin_to_block.role,
                "reason": "Compromised admin account",
                "blacklist_entry_id": blacklist_entry.id,
            },
        )

        await clear_state_preserve_admin_token(state)

        log_security_event(
            "EMERGENCY: Admin terminated",
            {
                "admin_id": admin.id,
                "target_telegram_id": telegram_id,
                "target_admin_id": admin_to_block.id,
                "action_type": "ADMIN_TERMINATED",
                "reason": "Compromised admin account",
                "blacklist_entry_id": blacklist_entry.id,
            }
        )

        # Send security notification
        await notify_security_event(
            "EMERGENCY: Admin Terminated",
            (
                f"Admin {admin.display_name} (ID: {admin.id}) "
                f"terminated admin {admin_to_block.display_name} "
                f"(Telegram ID: {telegram_id}) due to compromised account"
            ),
            priority="critical",
        )

        # Notify all super_admins
        try:
            # FIXED: Use context manager for Bot to prevent session leak
            async with Bot(token=settings.telegram_bot_token) as bot:
                notification_text = (
                    f"🚨 **Экстренная блокировка админа**\n\n"
                    f"Админ {admin.display_name} (ID: {admin.id}) "
                    f"экстренно заблокировал админа:\n\n"
                    f"• Telegram ID: `{telegram_id}`\n"
                    f"• Имя: {admin_to_block.display_name}\n"
                    f"• Роль: {admin_to_block.role}\n"
                    f"• Причина: Compromised admin account\n\n"
                    f"Действия выполнены:\n"
                    f"✅ Админ удален из системы\n"
                    f"✅ Telegram ID заблокирован (TERMINATED)\n"
                    f"✅ Все сессии деактивированы"
                )

                # Get super_admins for notification
                super_admins = [a for a in all_admins if a.is_super_admin]
                for super_admin in super_admins:
                    if super_admin.id != admin.id:
                        try:
                            await bot.send_message(
                                chat_id=super_admin.telegram_id,
                                text=notification_text,
                                parse_mode="Markdown",
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to notify super_admin "
                                f"{super_admin.id}: {e}"
                            )
        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")

        await message.answer(
            f"✅ **Админ экстренно заблокирован**\n\n"
            f"Telegram ID: `{telegram_id}`\n"
            f"Имя: {admin_to_block.display_name}\n"
            f"Роль: {admin_to_block.role}\n\n"
            f"Выполнено:\n"
            f"✅ Админ удален из системы\n"
            f"✅ Telegram ID заблокирован (TERMINATED)\n"
            f"✅ Все сессии деактивированы\n"
            f"✅ Пользователь забанен (если был зарегистрирован)\n\n"
            f"Все супер-администраторы уведомлены.",
            parse_mode="Markdown",
            reply_markup=admin_management_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error in emergency block: {e}")
        await session.rollback()
        await message.answer(
            f"❌ Ошибка при экстренной блокировке: {e}"
        )
        await clear_state_preserve_admin_token(state)
