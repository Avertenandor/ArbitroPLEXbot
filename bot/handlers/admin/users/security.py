"""
Admin User Security Handler
Handles user blocking, unblocking, and account termination
"""

from typing import Any

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.repositories.blacklist_repository import BlacklistRepository
from app.repositories.system_setting_repository import SystemSettingRepository
from app.services.admin_log_service import AdminLogService
from app.services.blacklist_service import (
    BlacklistActionType,
    BlacklistService,
)
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_users_keyboard,
    cancel_keyboard,
    main_menu_reply_keyboard,
)
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import escape_md
from bot.utils.menu_buttons import is_menu_button
from bot.utils.user_loader import UserLoader

router = Router(name="admin_users_security")


@router.message(F.text.in_({"🚫 Заблокировать", "✅ Разблокировать"}))
async def handle_profile_block_toggle(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle block status"""
    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        return

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if not user:
        return

    is_blocking = message.text == "🚫 Заблокировать"
    blacklist_service = BlacklistService(session)
    admin = data.get("admin")
    admin_id = admin.id if admin else None

    if is_blocking:
        await blacklist_service.add_to_blacklist(
            telegram_id=user.telegram_id,
            reason="Блокировка администратором через профиль",
            added_by_admin_id=admin_id,
            action_type=BlacklistActionType.BLOCKED,
        )
        user.is_banned = True
        await message.answer("✅ Пользователь заблокирован.")
    else:
        entry = await blacklist_service.repo.find_by_telegram_id(user.telegram_id)
        if entry and entry.is_active:
            await blacklist_service.repo.update(entry.id, is_active=False)

        user.is_banned = False
        await message.answer("✅ Пользователь разблокирован.")

    await session.commit()
    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile
    await show_user_profile(message, user, state, session)


@router.message(F.text == "⚠️ Терминировать аккаунт")
async def handle_profile_terminate(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Terminate account"""
    admin = await get_admin_or_deny(message, session, require_extended=True, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        # Fallback to legacy flow check if state is not set
        if await state.get_state() == AdminStates.awaiting_user_to_terminate:
            # This is part of the legacy flow which we are restoring below
            pass
        else:
            return

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if not user:
        return

    blacklist_service = BlacklistService(session)
    admin_id = admin.id if admin else None

    await blacklist_service.add_to_blacklist(
        telegram_id=user.telegram_id,
        reason="Терминация администратором через профиль",
        added_by_admin_id=admin_id,
        action_type=BlacklistActionType.TERMINATED,
    )
    user.is_banned = True
    await session.commit()

    await message.answer("✅ Аккаунт терминирован.")
    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile
    await show_user_profile(message, user, state, session)


# =================================================================================================
# Legacy / Direct Button Handlers (Restored)
# =================================================================================================

@router.message(F.text == "🚫 Заблокировать пользователя")
async def handle_start_block_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start block user flow"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AdminStates.awaiting_user_to_block)

    text = """
🚫 **Блокировка пользователя**

Отправьте username (с @) или Telegram ID пользователя для блокировки.

Пользователь получит уведомление и сможет подать апелляцию "
        "в течение 3 рабочих дней."

Пример: `@username` или `123456789`
    """.strip()

    await message.answer(
        text, parse_mode="Markdown", reply_markup=cancel_keyboard()
    )


@router.message(AdminStates.awaiting_user_to_block)
async def handle_block_user_input(  # noqa: C901
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle block user input"""
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Блокировка отменена.",
            reply_markup=admin_users_keyboard(),
        )
        return

    if message.text and is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return

    blacklist_service = BlacklistService(session)

    identifier = message.text.strip() if message.text else ""

    if not identifier:
        await message.reply("❌ Отправьте username или ID")
        return

    # Use UserLoader to search for user
    user = await UserLoader.search_user(session, identifier)

    if not user:
        await message.reply("❌ Пользователь не найден")
        await clear_state_preserve_admin_token(state)
        return

    admin = data.get("admin")
    admin_id = admin.id if admin else None

    try:
        await blacklist_service.add_to_blacklist(
            telegram_id=user.telegram_id,
            reason="Блокировка администратором",
            added_by_admin_id=admin_id,
            action_type=BlacklistActionType.BLOCKED,
        )

        user.is_banned = True
        await session.commit()

        # FIXED: Use context manager for Bot to prevent session leak
        try:
            async with Bot(token=settings.telegram_bot_token) as bot:
                setting_repo = SystemSettingRepository(session)
                notification_text = await setting_repo.get_value(
                    "blacklist_block_notification_text",
                    default=(
                        "⚠️ Ваш аккаунт временно заблокирован в нашем сообществе. "
                        "Вы можете подать апелляцию в течение 3 рабочих дней."
                    )
                )
                notification_text_with_instruction = (
                    f"{notification_text}\n\n"
                    "Чтобы подать апелляцию, нажмите кнопку "
                    "'📝 Подать апелляцию' в боте."
                )
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_text_with_instruction,
                )

                blacklist_repo = BlacklistRepository(session)
                blacklist_entry = await blacklist_repo.find_by_telegram_id(
                    user.telegram_id
                )
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text="Выберите действие:",
                    reply_markup=main_menu_reply_keyboard(
                        user=user, blacklist_entry=blacklist_entry, is_admin=False
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to send notification to user {user.telegram_id}: {e}")

        username = escape_md(user.username) if user.username else None
        display_name = f"@{username}" if username else f"ID {user.telegram_id}"

        await message.reply(
            f"✅ Пользователь {display_name} заблокирован.\n"
            f"Уведомление отправлено пользователю.",
            reply_markup=admin_users_keyboard(),
        )

        if admin:
            log_service = AdminLogService(session)
            await log_service.log_user_blocked(
                admin=admin,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                reason="Блокировка администратором",
            )

    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        await message.reply(
            f"❌ Ошибка: {str(e)}",
            reply_markup=admin_users_keyboard(),
        )

    await clear_state_preserve_admin_token(state)


# Re-use handle_profile_terminate but support direct call with state
@router.message(AdminStates.awaiting_user_to_terminate)
async def handle_terminate_user_input(  # noqa: C901
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle terminate user input (direct flow)"""
    if message.text == "❌ Отмена":
        await clear_state_preserve_admin_token(state)
        await message.answer(
            "❌ Терминация отменена.",
            reply_markup=admin_users_keyboard(),
        )
        return

    if message.text and is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return

    blacklist_service = BlacklistService(session)

    identifier = message.text.strip() if message.text else ""

    if not identifier:
        await message.reply("❌ Отправьте username или ID")
        return

    # Use UserLoader to search for user
    user = await UserLoader.search_user(session, identifier)

    if not user:
        await message.reply("❌ Пользователь не найден")
        await clear_state_preserve_admin_token(state)
        return

    admin = data.get("admin")
    admin_id = admin.id if admin else None

    try:
        await blacklist_service.add_to_blacklist(
            telegram_id=user.telegram_id,
            reason="Терминация администратором",
            added_by_admin_id=admin_id,
            action_type=BlacklistActionType.TERMINATED,
        )

        user.is_banned = True
        await session.commit()

        # FIXED: Use context manager for Bot to prevent session leak
        try:
            async with Bot(token=settings.telegram_bot_token) as bot:
                setting_repo = SystemSettingRepository(session)
                notification_text = await setting_repo.get_value(
                    "blacklist_terminate_notification_text",
                    default=(
                        "❌ Ваш аккаунт терминирован в нашем сообществе "
                        "без возможности восстановления."
                    )
                )
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=notification_text,
                )
        except Exception as e:
            logger.warning(f"Failed to send notification to user {user.telegram_id}: {e}")

        username = escape_md(user.username) if user.username else None
        display_name = f"@{username}" if username else f"ID {user.telegram_id}"

        await message.reply(
            f"✅ Аккаунт {display_name} терминирован.\n"
            f"Уведомление отправлено пользователю.",
            reply_markup=admin_users_keyboard(),
        )

        if admin:
            log_service = AdminLogService(session)
            await log_service.log_user_terminated(
                admin=admin,
                user_id=user.id,
                user_telegram_id=user.telegram_id,
                reason="Терминация администратором",
            )
    except Exception as e:
        logger.error(f"Error terminating user: {e}")
        await message.reply(
            f"❌ Ошибка: {str(e)}",
            reply_markup=admin_users_keyboard(),
        )

    await clear_state_preserve_admin_token(state)


@router.message(F.text == "⚠️ Терминировать аккаунт")
async def handle_start_terminate_user_direct(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start terminate user flow (direct)"""
    # Check permissions first (this is triggered by button)
    # Note: handle_profile_terminate also catches this text!
    # We need to differentiate based on state or context.
    # If we are in profile mode (selected_user_id set),
    # handle_profile_terminate should take precedence.
    # But handlers are registered in order.
    # handle_profile_terminate is registered BEFORE this one.
    # So if state has selected_user_id, handle_profile_terminate will run.
    # If not, it will return early (if not user_id: return).
    # So we can put this handler AFTER handle_profile_terminate and
    # it will catch cases where profile is not active.

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AdminStates.awaiting_user_to_terminate)

    text = """
⚠️ **Терминация аккаунта**

Отправьте username (с @) или Telegram ID пользователя для терминации.

⚠️ **ВНИМАНИЕ:** Аккаунт будет полностью заблокирован без возможности апелляции.

Пример: `@username` или `123456789`
    """.strip()

    await message.answer(
        text, parse_mode="Markdown", reply_markup=cancel_keyboard()
    )
