"""
Admin User List Handler
Handles paginated user list display and selection
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_user_list_keyboard, admin_users_keyboard


router = Router(name="admin_users_list")


@router.message(F.text == "👥 Список пользователей")
async def handle_list_users(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    page: int = 1,
    **data: Any,
) -> None:
    """Show paginated list of users"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user_service = UserService(session)
    limit = 10
    offset = (page - 1) * limit

    # Fetch users sorted by created_at desc
    stmt = select(User).order_by(desc(User.created_at)).limit(limit).offset(offset)
    result = await session.execute(stmt)
    users = result.scalars().all()

    total_users = await user_service.get_total_users()
    total_pages = (total_users + limit - 1) // limit if total_users > 0 else 1

    await state.update_data(current_user_list_page=page)

    if not users:
        await message.answer(
            "👥 Пользователи не найдены.",
            reply_markup=admin_users_keyboard(),
        )
        return

    text = f"👥 **Список пользователей** (Страница {page}/{total_pages})\n\n"
    text += "Выберите пользователя для просмотра профиля:"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_list_keyboard(users, page, total_pages),
    )


@router.message(F.text == "⬅ Предыдущая")
@router.message(F.text == "Следующая ➡")
async def handle_user_list_pagination(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle list pagination"""
    state_data = await state.get_data()
    current_page = state_data.get("current_user_list_page", 1)

    if message.text == "⬅ Предыдущая":
        page = max(1, current_page - 1)
    else:
        page = current_page + 1

    await handle_list_users(message, session, state, page=page, **data)


@router.message(F.text.regexp(r"^🆔 (\d+):"))
async def handle_user_selection(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle user selection from list"""
    match = F.text.regexp(r"^🆔 (\d+):").resolve(message)
    if not match:
        return

    user_id = int(match.group(1))
    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)

    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    # Import here to avoid circular dependency
    from bot.handlers.admin.users.profile import show_user_profile
    await show_user_profile(message, user, state, session)


@router.message(F.text == "◀️ К списку пользователей")
async def handle_back_to_list(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to list"""
    state_data = await state.get_data()
    page = state_data.get("current_user_list_page", 1)
    await handle_list_users(message, session, state, page=page, **data)
