"""
Admin Creation Handlers.

Handles the creation of new admin accounts with role selection.
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
)
from bot.states.admin import AdminManagementStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .router import router


@router.message(F.text == "➕ Добавить админа")
async def handle_create_admin(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start admin creation process.

    Only accessible to super_admin.
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    await state.set_state(AdminManagementStates.awaiting_admin_telegram_id)
    await message.answer(
        "👤 **Создание нового админа**\n\n"
        "Введите Telegram ID нового админа:",
        parse_mode="Markdown",
    )


@router.message(AdminManagementStates.awaiting_admin_telegram_id)
async def handle_admin_telegram_id(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle Telegram ID input for new admin or deletion.

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

    # Check if cancel
    if message.text == "❌ Отмена":
        from bot.keyboards.reply import admin_management_keyboard

        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Операция отменена.",
            reply_markup=admin_management_keyboard(),
        )
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

    # Get action from state
    state_data = await state.get_data()
    action = state_data.get("action")

    # If action is delete, delegate to delete handler
    if action == "delete":
        from .delete import handle_delete_admin_telegram_id
        await handle_delete_admin_telegram_id(
            message, session, state, **data
        )
        return

    # Otherwise, process creation
    admin_service = AdminService(session)
    existing = await admin_service.get_admin_by_telegram_id(telegram_id)

    if existing:
        await message.answer(
            f"❌ Админ с Telegram ID {telegram_id} уже существует.\n\n"
            "Введите другой Telegram ID или отправьте /cancel для отмены:"
        )
        return

    # Save telegram_id and ask for role
    await state.update_data(new_admin_telegram_id=telegram_id)
    await state.set_state(AdminManagementStates.awaiting_admin_role)

    await message.answer(
        "👤 **Выбор роли**\n\n"
        "Выберите роль для нового админа:\n\n"
        "1️⃣ `admin` - Базовые права\n"
        "2️⃣ `extended_admin` - Расширенные права\n"
        "3️⃣ `super_admin` - Полные права\n\n"
        "Введите номер (1, 2 или 3):",
        parse_mode="Markdown",
    )


@router.message(AdminManagementStates.awaiting_admin_role)
async def handle_admin_role_selection(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle role selection for new admin.

    Args:
        message: Telegram message with role selection
        session: Database session
        state: FSM context
        **data: Handler data
    """
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    role_input = message.text.strip() if message.text else ""

    role_map = {
        "1": "admin",
        "2": "extended_admin",
        "3": "super_admin",
        "admin": "admin",
        "extended_admin": "extended_admin",
        "super_admin": "super_admin",
    }

    role = role_map.get(role_input.lower())

    if not role:
        await message.answer(
            "❌ Неверный выбор роли.\n\n"
            "Введите номер (1, 2 или 3) или название роли:"
        )
        return

    # Get telegram_id from state
    state_data = await state.get_data()
    telegram_id = state_data.get("new_admin_telegram_id")

    if not telegram_id:
        await message.answer("❌ Ошибка: Telegram ID не найден")
        await clear_state_preserve_admin_token(state)
        return

    # Save role and create admin
    await state.update_data(new_admin_role=role)

    # Create admin
    admin_service = AdminService(session)
    new_admin, master_key, error = await admin_service.create_admin(
        telegram_id=telegram_id,
        role=role,
        created_by=admin.id,
        username=None,  # Will be set when admin first logs in
    )

    if error or not new_admin or not master_key:
        await message.answer(
            f"❌ Ошибка при создании админа: {error or 'Неизвестная ошибка'}"
        )
        await clear_state_preserve_admin_token(state)
        return

    # Clear state
    await clear_state_preserve_admin_token(state)

    logger.info(
        f"Admin {admin.id} created new admin {new_admin.id} "
        f"(telegram_id={telegram_id}, role={role})"
    )

    # Log admin creation
    log_service = AdminLogService(session)
    await log_service.log_admin_created(
        admin=admin,
        created_admin_id=new_admin.id,
        created_admin_telegram_id=telegram_id,
        role=role,
    )

    # Send confirmation
    role_display = await format_role_display(role)

    from bot.keyboards.reply import admin_management_keyboard

    await message.answer(
        f"✅ **Админ успешно создан**\n\n"
        f"Telegram ID: `{telegram_id}`\n"
        f"Роль: `{role_display}`\n\n"
        f"Мастер-ключ отправлен новому админу в Telegram.",
        parse_mode="Markdown",
        reply_markup=admin_management_keyboard(),
    )

    # Send master key to new admin via Telegram
    try:
        bot = message.bot
        master_key_message = (
            "🔐 **Ваш мастер-ключ для доступа к админ-панели**\n\n"
            f"Мастер-ключ: `{master_key}`\n\n"
            "⚠️ **ВАЖНО:**\n"
            "• Сохраните этот ключ в безопасном месте\n"
            "• Не передавайте его третьим лицам\n"
            "• Используйте его для входа в админ-панель\n"
            "• При первом входе введите `/admin` и затем мастер-ключ\n\n"
            "Для входа в админ-панель используйте команду `/admin`."
        )

        await bot.send_message(
            chat_id=telegram_id,
            text=master_key_message,
            parse_mode="Markdown",
        )

        logger.info(
            f"Master key sent to new admin {new_admin.id} "
            f"(telegram_id={telegram_id})"
        )
    except Exception as e:
        logger.error(
            f"Failed to send master key to new admin {new_admin.id}: {e}"
        )
        # Notify creating admin about delivery failure
        await message.answer(
            "⚠️ **Внимание:** Не удалось отправить мастер-ключ "
            "новому админу. Передайте ключ лично.",
            parse_mode="Markdown",
        )
