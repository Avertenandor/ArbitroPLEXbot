"""
Admin Panel Main Handlers

Main entry points for accessing the admin panel:
- /admin command
- Admin panel button handler
- Back to main menu handler

Shows summary statistics on panel entry.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_keyboard, get_admin_keyboard_from_data


router = Router(name="admin_panel_main")


async def get_admin_summary(session: AsyncSession) -> str:
    """Get summary statistics for admin panel."""
    from app.services.deposit import DepositService
    from app.services.inquiry_service import InquiryService
    from app.services.user_service import UserService
    from app.services.withdrawal_service import WithdrawalService

    try:
        withdrawal_service = WithdrawalService(session)
        inquiry_service = InquiryService(session)
        deposit_service = DepositService(session)
        user_service = UserService(session)

        # Get pending withdrawals count
        pending_withdrawals = await withdrawal_service.get_pending_withdrawals()
        pending_count = len(pending_withdrawals)

        # Get new inquiries count
        new_inquiries = await inquiry_service.count_new_inquiries()

        # Get active deposits count
        deposit_stats = await deposit_service.get_platform_stats()
        active_deposits = deposit_stats.get("total_deposits", 0)

        # Get total users
        total_users = await user_service.get_total_users()

        summary = (
            f"📊 **Сводка:**\n"
            f"• Ожидающих выводов: {pending_count}\n"
            f"• Новых обращений: {new_inquiries}\n"
            f"• Активных депозитов: {active_deposits}\n"
            f"• Всего пользователей: {total_users}\n"
        )

        return summary

    except Exception as e:
        logger.warning(f"Failed to get admin summary: {e}")
        return ""


@router.message(Command("admin"))
async def cmd_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Вход в админ-панель по команде /admin.
    Работает только для админов (is_admin=True из middleware).
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    user: User | None = data.get("user")
    from app.repositories.blacklist_repository import BlacklistRepository
    blacklist_repo = BlacklistRepository(session)
    if user:
        await blacklist_repo.find_by_telegram_id(user.telegram_id)

    # Get summary statistics
    summary = await get_admin_summary(session)

    text = f"""
👑 **Панель администратора**

{summary}
Выберите действие:
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
            is_super_admin=admin.is_super_admin,
            is_extended_admin=admin.is_extended_admin
        ),
    )


@router.message(F.text == "👑 Админ-панель")
async def handle_admin_panel_button(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Вход в админ-панель по кнопке в reply keyboard.
    Работает только для админов (is_admin=True из middleware).
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[ADMIN] handle_admin_panel_button called for user {telegram_id}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning(f"[ADMIN] User {telegram_id} tried to access admin panel but was denied")
        return

    user: User | None = data.get("user")
    from app.repositories.blacklist_repository import BlacklistRepository
    blacklist_repo = BlacklistRepository(session)
    if user:
        await blacklist_repo.find_by_telegram_id(user.telegram_id)

    # Get summary statistics
    summary = await get_admin_summary(session)

    text = f"""
👑 **Панель администратора**

{summary}
Выберите действие:
    """.strip()

    # AdminAuthMiddleware already populates is_extended_admin / is_super_admin in data
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )


@router.message(F.text == "◀️ Главное меню")
async def handle_back_to_main_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to main menu from admin panel"""
    from bot.handlers.menu import show_main_menu

    state: FSMContext = data.get("state")
    user: User | None = data.get("user")

    if state:
        # Clear state but preserve admin token for smoother UX
        from bot.utils.admin_utils import clear_state_preserve_admin_token
        await clear_state_preserve_admin_token(state)

    # Remove 'user' and 'state' from data to avoid duplicate arguments
    safe_data = {k: v for k, v in data.items() if k not in ('user', 'state')}
    await show_main_menu(message, session, user, state, **safe_data)
