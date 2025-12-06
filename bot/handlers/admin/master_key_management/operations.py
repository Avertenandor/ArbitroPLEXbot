"""
Master key operations.

Contains:
- Master key generation
- Key regeneration logic
"""

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.admin_log_service import AdminLogService
from app.services.admin_service import AdminService
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .messages import (
    build_key_copy_message,
    build_new_key_message,
    build_usage_instructions,
)
from .security import is_super_admin


async def regenerate_master_key(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Generate new master key for super admin.

    CRITICAL OPERATION:
    - Generates new random key (32 bytes = 256 bits)
    - Hashes with bcrypt
    - Updates admin record
    - Shows key to user (ONLY ONCE)
    - Logs action for security audit

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

    await clear_state_preserve_admin_token(state)

    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin:
        await message.answer("❌ Администратор не найден")
        return

    # Check if this is first key or regeneration
    is_first_key = admin.master_key is None or admin.master_key == ""

    # Generate new master key
    plain_master_key = admin_service.generate_master_key()
    hashed_master_key = admin_service.hash_master_key(plain_master_key)

    # Update admin with new master key
    admin.master_key = hashed_master_key
    await session.commit()

    # Log action for security audit
    action_type = "MASTER_KEY_CREATED" if is_first_key else "MASTER_KEY_REGENERATED"
    logger.warning(
        f"[SECURITY] {action_type} for super admin {telegram_id} (admin_id: {admin.id})"
    )

    # Log to admin_actions table
    try:
        admin_log_service = AdminLogService(session)
        await admin_log_service.log_action(
            admin_id=admin.id,
            action_type=action_type,
            details={
                "telegram_id": telegram_id,
                "is_first_key": is_first_key,
            }
        )
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to log master key action: {e}")

    # Show new key to user (ONLY ONCE!)
    text = build_new_key_message(plain_master_key, is_first_key)
    await message.answer(text, parse_mode="Markdown")

    # Send key in separate message for easy copying
    copy_message = build_key_copy_message(plain_master_key)
    await message.answer(copy_message, parse_mode="Markdown")

    # Send instructions with main menu keyboard
    user = data.get("user")
    blacklist_entry = data.get("blacklist_entry")
    is_admin = data.get("is_admin", False)

    instructions = build_usage_instructions()
    await message.answer(
        instructions,
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        )
    )
