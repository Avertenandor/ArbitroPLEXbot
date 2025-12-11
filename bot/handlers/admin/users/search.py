"""
Admin User Search Handler
Handles user search by username, telegram ID, wallet address, or user ID
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.states.admin_states import AdminStates
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import escape_md
from bot.utils.menu_buttons import is_menu_button
from bot.utils.user_loader import UserLoader


router = Router(name="admin_users_search")


def search_user_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для поиска пользователя с кнопкой Назад."""
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="◀️ Назад"))
    builder.row(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)


@router.message(Command("search"))
async def cmd_search_user(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Quick search user by command: /search @username or /search 0x... or /search 123456
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Parse argument
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "🔍 *Быстрый поиск пользователя*\n\n"
            "Использование:\n"
            "`/search @username` - по юзернейму\n"
            "`/search 123456789` - по Telegram ID\n"
            "`/search 0x...` - по адресу кошелька\n",
            parse_mode="Markdown",
        )
        return

    query = args[1].strip()
    user = await UserLoader.search_user(session, query)

    if not user:
        await message.answer(
            f"❌ Пользователь не найден: `{escape_md(query)}`",
            parse_mode="Markdown",
        )
        return

    logger.info(f"Admin search: found user {user.id} by query '{query}'")

    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile

    await show_user_profile(message, user, state, session)


@router.message(F.text == "🔍 Найти пользователя")
async def handle_find_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Start find user flow"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AdminStates.finding_user)

    await message.answer(
        "🔍 **Поиск пользователя**\n\n"
        "Отправьте **Username** (с @ или без), **Telegram ID**, **User ID** "
        "или **адрес кошелька (0x...)**.\n\n"
        "Пример: `@username`, `123456789`, `0x1234...`\n\n"
        "💡 Или используйте команду: `/search @username`",
        parse_mode="Markdown",
        reply_markup=search_user_keyboard(),
    )


@router.message(AdminStates.finding_user, F.text == "◀️ Назад")
async def handle_search_back(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle back button - return to users menu."""
    from bot.handlers.admin.users.menu import handle_admin_users_menu

    await handle_admin_users_menu(message, state, session, **data)


@router.message(AdminStates.finding_user)
async def process_find_user_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Process find user input"""
    if message.text == "❌ Отмена":
        # Import here to avoid circular dependency
        from bot.handlers.admin.users.menu import handle_admin_users_menu

        await handle_admin_users_menu(message, state, session, **data)
        return

    if is_menu_button(message.text):
        await clear_state_preserve_admin_token(state)
        return

    identifier = message.text.strip()

    # Try multiple search strategies using UserLoader
    user = await UserLoader.search_user(session, identifier)

    # If not found by standard search, try as User ID (database primary key)
    if not user and identifier.isdigit():
        user_service = UserService(session)
        user = await user_service.get_by_id(int(identifier))

    if not user:
        await message.reply(
            "❌ **Пользователь не найден**\nПроверьте введенные данные и попробуйте снова.",
            parse_mode="Markdown",
            reply_markup=search_user_keyboard(),
        )
        return

    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile

    await show_user_profile(message, user, state, session)
