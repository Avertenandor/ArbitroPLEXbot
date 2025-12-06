"""
Message handlers for master key management.

Contains all message and command handlers for master key operations.
"""

from typing import Any

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_service import AdminService
from bot.keyboards.reply import (
    main_menu_reply_keyboard,
    master_key_management_reply_keyboard,
)
from bot.states.admin import AdminMasterKeyStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .messages import (
    build_confirmation_message,
    build_key_already_exists_message,
    build_key_status_message,
    build_master_key_menu_message,
    build_quick_key_created_message,
    build_quick_key_regenerated_message,
)
from .operations import regenerate_master_key
from .security import is_super_admin


async def cmd_masterkey(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect command to button handler."""
    await btn_my_master_key(message, session, state, **data)


async def btn_my_master_key(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Quick command to get master key.

    Only works for SUPER_ADMIN_TELEGRAM_ID.
    If key doesn't exist - generates new one immediately.
    If key exists - shows it was already generated and offers to regenerate.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    # Security check
    if not is_super_admin(telegram_id):
        logger.warning(
            f"[SECURITY] Unauthorized /masterkey command from user {telegram_id}"
        )
        await message.answer(
            "❌ Эта команда доступна только главному администратору.\n\n"
            f"Ваш ID: `{telegram_id}`",
            parse_mode="Markdown"
        )
        return

    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin:
        await message.answer(
            "❌ Вы не найдены в базе администраторов.\n\n"
            f"Ваш Telegram ID: `{telegram_id}`\n"
            "Обратитесь к разработчику для добавления.",
            parse_mode="Markdown"
        )
        return

    if admin.role != "super_admin":
        await message.answer(
            f"❌ Требуется роль super_admin.\n"
            f"Ваша роль: {admin.role}"
        )
        return

    # Check if master key already exists
    has_key = admin.master_key is not None and admin.master_key != ""

    if has_key:
        # Key already exists - offer to regenerate
        text = build_key_already_exists_message()
        await message.answer(text, parse_mode="Markdown")

        # Generate new key immediately for convenience
        await message.answer(
            "🔄 **Генерирую новый мастер-ключ...**",
            parse_mode="Markdown"
        )

        # Generate new master key
        plain_master_key = admin_service.generate_master_key()
        hashed_master_key = admin_service.hash_master_key(plain_master_key)

        # Update admin with new master key
        admin.master_key = hashed_master_key
        await session.commit()

        logger.warning(
            f"[SECURITY] MASTER_KEY_REGENERATED via /masterkey command "
            f"for super admin {telegram_id} (admin_id: {admin.id})"
        )

        regenerated_message = build_quick_key_regenerated_message(plain_master_key)
        await message.answer(regenerated_message, parse_mode="Markdown")
    else:
        # No key - generate first one
        plain_master_key = admin_service.generate_master_key()
        hashed_master_key = admin_service.hash_master_key(plain_master_key)

        # Update admin with new master key
        admin.master_key = hashed_master_key
        await session.commit()

        logger.warning(
            f"[SECURITY] MASTER_KEY_CREATED via /masterkey command "
            f"for super admin {telegram_id} (admin_id: {admin.id})"
        )

        created_message = build_quick_key_created_message(plain_master_key)
        await message.answer(created_message, parse_mode="Markdown")


async def show_master_key_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show master key management menu.

    Only accessible to super admin (configured via SUPER_ADMIN_TELEGRAM_ID env var).
    NOTE: This handler does NOT require master key authentication
    because it's used to GET the master key.

    SECURITY:
    - Checks telegram_id == SUPER_ADMIN_TELEGRAM_ID
    - Verifies admin exists in database
    - Verifies role == super_admin
    - Logs all access attempts

    Args:
        message: Message object
        session: Database session
        state: FSM context
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    # SECURITY CHECK 1: Only super admin by telegram_id
    if not is_super_admin(telegram_id):
        logger.warning(
            f"[SECURITY] Unauthorized master key access attempt from user {telegram_id}"
        )
        await message.answer(
            "❌ Доступ запрещен.\n\n"
            "Эта функция доступна только главному администратору."
        )
        return

    # SECURITY CHECK 2: Verify user is actually an admin in database
    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin:
        logger.error(
            f"[SECURITY] User {telegram_id} tried to access master key "
            f"but not found in admins table"
        )
        await message.answer("❌ Администратор не найден в базе данных")
        return

    # SECURITY CHECK 3: Verify role is super_admin
    if admin.role != "super_admin":
        logger.warning(
            f"[SECURITY] User {telegram_id} tried to access master key "
            f"but role is {admin.role}, not super_admin"
        )
        await message.answer(
            "❌ Доступ запрещен.\n\n"
            "Требуется роль: super_admin\n"
            f"Ваша роль: {admin.role}"
        )
        return

    # SECURITY CHECK 4: Verify admin is not blocked
    if admin.is_blocked:
        logger.warning(
            f"[SECURITY] Blocked admin {telegram_id} tried to access master key"
        )
        await message.answer(
            "❌ Доступ запрещен.\n\n"
            "Ваш аккаунт администратора заблокирован."
        )
        return

    await clear_state_preserve_admin_token(state)

    # Check if master key exists
    has_master_key = admin.master_key is not None and admin.master_key != ""

    # Build message
    text = build_master_key_menu_message(has_master_key)

    # Log access
    logger.info(
        f"[MASTER_KEY] Super admin {telegram_id} opened master key menu "
        f"(has_key={has_master_key})"
    )

    await message.answer(
        text,
        reply_markup=master_key_management_reply_keyboard(),
        parse_mode="Markdown"
    )


async def show_master_key_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show current master key status.

    Cannot show actual key (it's hashed), but shows:
    - Key exists
    - Security information

    Args:
        message: Message object
        session: Database session
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    if not is_super_admin(telegram_id):
        await message.answer("❌ Доступ запрещен")
        return

    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin or not admin.master_key:
        await message.answer(
            "⚠️ **Мастер-ключ не установлен**\n\n"
            "Используйте кнопку '🔄 Сгенерировать новый ключ' для создания.",
            parse_mode="Markdown",
            reply_markup=master_key_management_reply_keyboard()
        )
        return

    # Build status message
    text = build_key_status_message(admin.master_key)

    logger.info(f"[MASTER_KEY] Super admin {telegram_id} viewed key status")

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=master_key_management_reply_keyboard()
    )


async def confirm_regenerate_master_key(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Ask for confirmation before regenerating master key.

    This is a critical operation that will invalidate the old key.

    Args:
        message: Message object
        state: FSM context
        session: Database session
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    if not is_super_admin(telegram_id):
        await message.answer("❌ Доступ запрещен")
        return

    # Check if admin has existing key
    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    has_existing_key = admin and admin.master_key is not None and admin.master_key != ""

    if has_existing_key:
        # Ask for confirmation
        text = build_confirmation_message()

        await state.set_state(AdminMasterKeyStates.awaiting_confirmation)
        await message.answer(
            text, parse_mode="Markdown",
            reply_markup=master_key_management_reply_keyboard()
        )
    else:
        # First time - generate immediately
        await regenerate_master_key(message, session, state, **data)


async def process_confirmation(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process confirmation for master key regeneration.

    Args:
        message: Message object
        session: Database session
        state: FSM context
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    if not is_super_admin(telegram_id):
        await message.answer("❌ Доступ запрещен")
        await clear_state_preserve_admin_token(state)
        return

    if message.text and message.text.strip().upper() == "ПОДТВЕРЖДАЮ":
        await regenerate_master_key(message, session, state, **data)
    else:
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Генерация нового ключа отменена.\n\n"
            "Ваш текущий ключ остался без изменений.",
            reply_markup=master_key_management_reply_keyboard()
        )


async def back_to_main_menu(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Return to main menu from master key management.

    Args:
        message: Message object
        state: FSM context
        **data: Additional context data
    """
    telegram_id = message.from_user.id if message.from_user else None

    if not is_super_admin(telegram_id):
        return  # Let other handlers process this

    await clear_state_preserve_admin_token(state)

    user = data.get("user")
    blacklist_entry = data.get("blacklist_entry")
    is_admin = data.get("is_admin", False)

    await message.answer(
        "📊 **Главное меню**\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        )
    )

    logger.info(f"[MASTER_KEY] Super admin {telegram_id} returned to main menu")
