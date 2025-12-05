"""
Notification text editing handlers.

Implements editing of blacklist notification texts for block and terminate actions.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_blacklist_keyboard,
    cancel_keyboard,
)
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token

router = Router()


@router.message(F.text == "📝 Редактировать тексты")
async def handle_edit_notification_texts(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show notification texts editor menu."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    setting_repo = SystemSettingRepository(session)

    # Get current texts or use defaults
    default_block_text = (
        "⚠️ Ваш аккаунт временно заблокирован в нашем сообществе. "
        "Вы можете подать апелляцию в течение 3 рабочих дней."
    )
    block_text = await setting_repo.get_value(
        "blacklist_block_notification_text",
        default=default_block_text
    )
    terminate_text = await setting_repo.get_value(
        "blacklist_terminate_notification_text",
        default="❌ Ваш аккаунт терминирован в нашем сообществе без возможности восстановления."
    )

    text = (
        f"📝 **Редактирование текстов уведомлений**\n\n"
        f"**Текущий текст блокировки:**\n{block_text}\n\n"
        f"**Текущий текст терминации:**\n{terminate_text}\n\n"
        f"Выберите текст для редактирования:\n"
        f"• `Изменить текст блокировки`\n"
        f"• `Изменить текст терминации`"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_blacklist_keyboard(),
    )


@router.message(F.text == "Изменить текст блокировки")
async def handle_start_edit_block_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start editing block notification text."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    setting_repo = SystemSettingRepository(session)
    default_block_text = (
        "⚠️ Ваш аккаунт временно заблокирован в нашем сообществе. "
        "Вы можете подать апелляцию в течение 3 рабочих дней."
    )
    current_text = await setting_repo.get_value(
        "blacklist_block_notification_text",
        default=default_block_text
    )

    await state.set_state(AdminStates.awaiting_block_notification_text)

    await message.answer(
        f"📝 **Редактирование текста блокировки**\n\n"
        f"Текущий текст:\n{current_text}\n\n"
        f"Введите новый текст уведомления о блокировке:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminStates.awaiting_block_notification_text)
async def handle_save_block_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Save block notification text."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        await clear_state_preserve_admin_token(state)
        return

    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Редактирование отменено.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    new_text = message.text.strip()
    if len(new_text) < 10:
        await message.answer("❌ Текст слишком короткий. Минимум 10 символов.")
        return

    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    setting_repo = SystemSettingRepository(session)
    await setting_repo.set_value("blacklist_block_notification_text", new_text)
    await session.commit()

    await message.answer(
        f"✅ **Текст блокировки обновлён!**\n\n"
        f"Новый текст:\n{new_text}",
        parse_mode="Markdown",
        reply_markup=admin_blacklist_keyboard(),
    )
    await clear_state_preserve_admin_token(state)


@router.message(F.text == "Изменить текст терминации")
async def handle_start_edit_terminate_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start editing terminate notification text."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    setting_repo = SystemSettingRepository(session)
    current_text = await setting_repo.get_value(
        "blacklist_terminate_notification_text",
        default="❌ Ваш аккаунт терминирован в нашем сообществе без возможности восстановления."
    )

    await state.set_state(AdminStates.awaiting_terminate_notification_text)

    await message.answer(
        f"📝 **Редактирование текста терминации**\n\n"
        f"Текущий текст:\n{current_text}\n\n"
        f"Введите новый текст уведомления о терминации:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(AdminStates.awaiting_terminate_notification_text)
async def handle_save_terminate_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Save terminate notification text."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        await clear_state_preserve_admin_token(state)
        return

    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Редактирование отменено.",
            reply_markup=admin_blacklist_keyboard(),
        )
        return

    new_text = message.text.strip()
    if len(new_text) < 10:
        await message.answer("❌ Текст слишком короткий. Минимум 10 символов.")
        return

    from app.repositories.system_setting_repository import (
        SystemSettingRepository,
    )

    setting_repo = SystemSettingRepository(session)
    await setting_repo.set_value("blacklist_terminate_notification_text", new_text)
    await session.commit()

    await message.answer(
        f"✅ **Текст терминации обновлён!**\n\n"
        f"Новый текст:\n{new_text}",
        parse_mode="Markdown",
        reply_markup=admin_blacklist_keyboard(),
    )
    await clear_state_preserve_admin_token(state)
