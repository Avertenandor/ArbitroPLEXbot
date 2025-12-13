"""
View and unban handlers for blacklist entries.

Implements viewing blacklist entry details and unbanning users.
"""

import re
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_blacklist_keyboard,
    confirmation_keyboard,
)
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token


router = Router()


@router.message(F.text.regexp(r'^Просмотр #(\d+)$'))
async def handle_view_blacklist_entry(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """View blacklist entry details."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    match = re.match(r'^Просмотр #(\d+)$', message.text, re.UNICODE)
    if not match:
        error_msg = (
            "❌ Неверный формат. "
            "Используйте: `Просмотр #ID`"
        )
        await message.answer(error_msg)
        return

    entry_id = int(match.group(1))

    from app.models.blacklist import BlacklistActionType
    from app.repositories.blacklist_repository import BlacklistRepository

    blacklist_repo = BlacklistRepository(session)
    entry = await blacklist_repo.get_by_id(entry_id)

    if not entry:
        await message.answer(
            f"❌ Запись #{entry_id} не найдена.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    action_type_text = {
        BlacklistActionType.REGISTRATION_DENIED: "🚫 Отказ в регистрации",
        BlacklistActionType.TERMINATED: "❌ Терминация",
        BlacklistActionType.BLOCKED: "⚠️ Блокировка",
    }.get(entry.action_type, entry.action_type)

    status_emoji = "🟢" if entry.is_active else "⚫"
    status_text = "Активна" if entry.is_active else "Неактивна"

    added_by_text = "Система"
    if entry.added_by_admin_id:
        from app.repositories.admin_repository import AdminRepository
        admin_repo = AdminRepository(session)
        admin_obj = await admin_repo.get_by_id(entry.added_by_admin_id)
        if admin_obj:
            added_by_text = f"@{admin_obj.username or 'N/A'} (ID: {admin_obj.id})"
        else:
            added_by_text = f"Admin ID: {entry.added_by_admin_id}"

    text = (
        f"📋 **Запись черного списка #{entry.id}**\n\n"
        f"{status_emoji} Статус: {status_text}\n"
        f"👤 Telegram ID: {entry.telegram_id or 'N/A'}\n"
        f"💳 Wallet: {entry.wallet_address or 'N/A'}\n"
        f"📋 Тип действия: {action_type_text}\n"
        f"📝 Причина: {entry.reason or 'N/A'}\n"
        f"👨‍💼 Добавил: {added_by_text}\n"
        f"📅 Создано: {entry.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"🔄 Обновлено: {entry.updated_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    # Show appeal deadline if BLOCKED
    if entry.action_type == BlacklistActionType.BLOCKED.value:
        if entry.appeal_deadline:
            deadline_str = entry.appeal_deadline.strftime('%d.%m.%Y %H:%M')
            text += f"⏰ Срок апелляции: {deadline_str}\n"
        else:
            text += "⏰ Срок апелляции: не установлен\n"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_blacklist_keyboard(),
    )


@router.message(F.text.regexp(r'^Разблокировать #(\d+)$', flags=re.UNICODE))
async def handle_unban_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Unban user from blacklist."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    match = re.match(r'^Разблокировать #(\d+)$', message.text, re.UNICODE)
    if not match:
        error_msg = (
            "❌ Неверный формат. "
            "Используйте: `Разблокировать #ID`"
        )
        await message.answer(error_msg)
        return

    entry_id = int(match.group(1))

    from app.repositories.blacklist_repository import BlacklistRepository

    blacklist_repo = BlacklistRepository(session)
    entry = await blacklist_repo.get_by_id(entry_id)

    if not entry:
        await message.answer(
            f"❌ Запись #{entry_id} не найдена.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    # Get user info for confirmation
    if entry.telegram_id:
        user_label = f"Telegram ID: {entry.telegram_id}"
    else:
        user_label = "Wallet: " + (entry.wallet_address or "N/A")

    await state.update_data(blacklist_entry_id=entry_id)
    await state.set_state(AdminStates.awaiting_user_to_unban)

    await message.answer(
        f"❓ **Подтвердите разблокировку**\n\n"
        f"Пользователь: {user_label}\n"
        f"Тип: {entry.action_type}\n"
        f"Причина: {entry.reason or 'N/A'}\n\n"
        "Пользователь снова сможет использовать бота.\n\n"
        "Подтвердите действие:",
        parse_mode="Markdown",
        reply_markup=confirmation_keyboard(),
    )


@router.message(AdminStates.awaiting_user_to_unban)
async def handle_unban_confirm(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Confirm unban."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        await clear_state_preserve_admin_token(state)
        return

    if message.text != "✅ Да":
        await message.answer(
            "❌ Разблокировка отменена.",
            reply_markup=admin_blacklist_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    state_data = await state.get_data()
    entry_id = state_data.get("blacklist_entry_id")

    if not entry_id:
        await message.answer(
            "❌ Ошибка: ID записи потерян.",
            reply_markup=admin_blacklist_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    from app.repositories.blacklist_repository import BlacklistRepository
    from app.services.blacklist_service import BlacklistService

    blacklist_repo = BlacklistRepository(session)
    entry = await blacklist_repo.get_by_id(entry_id)

    if not entry:
        await message.answer(
            f"❌ Запись #{entry_id} не найдена.",
            reply_markup=admin_blacklist_keyboard(),
        )
        await clear_state_preserve_admin_token(state)
        return

    # Remove from blacklist
    blacklist_service = BlacklistService(session)
    success = await blacklist_service.remove_from_blacklist(
        telegram_id=entry.telegram_id,
        wallet_address=entry.wallet_address,
    )

    await session.commit()

    if success:
        # Notify user if possible
        if entry.telegram_id:
            from aiogram import Bot
            bot: Bot = data.get("bot")
            if bot:
                try:
                    unban_msg = (
                        "✅ Ваш аккаунт разблокирован. "
                        "Вы снова можете использовать бота."
                    )
                    await bot.send_message(
                        chat_id=entry.telegram_id,
                        text=unban_msg,
                    )
                except Exception as e:
                    logger.warning(f"Failed to notify user about unban: {e}")

        await message.answer(
            f"✅ **Пользователь разблокирован!**\n\n"
            f"Запись #{entry_id} удалена из черного списка.",
            parse_mode="Markdown",
            reply_markup=admin_blacklist_keyboard(),
        )
    else:
        await message.answer(
            "❌ Ошибка при удалении из черного списка.",
            reply_markup=admin_blacklist_keyboard(),
        )

    await clear_state_preserve_admin_token(state)
