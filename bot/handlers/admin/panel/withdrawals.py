"""
Admin Withdrawal History Handler

Provides detailed withdrawal history with pagination and search functionality:
- View completed withdrawals with transaction hashes
- Navigate through pages of withdrawal records
- Search withdrawals by username, telegram_id or tx_hash
- See user information and withdrawal amounts
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import (
    admin_withdrawal_history_pagination_keyboard,
    get_admin_keyboard_from_data,
)
from bot.states.admin_states import AdminStates
from bot.utils.formatters import format_usdt


router = Router(name="admin_panel_withdrawals")


@router.message(F.text == "📋 История выводов")
async def handle_withdrawal_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle detailed withdrawal history with pagination."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Clear any search state and reset to page 1
    await state.update_data(wd_history_page=1, wd_search_query=None)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=1)


async def show_withdrawal_page(
    message: Message,
    withdrawal_service,
    page: int = 1,
    search_query: str | None = None,
) -> None:
    """Show withdrawal history page with optional search."""
    if search_query:
        detailed = await withdrawal_service.search_withdrawals(
            query=search_query, page=page, per_page=5
        )
        text = f"🔍 **Поиск: {search_query}**\n\n"
    else:
        detailed = await withdrawal_service.get_detailed_withdrawals(
            page=page, per_page=5
        )
        text = "📋 **История выводов на кошельки**\n\n"

    if not detailed["withdrawals"]:
        if search_query:
            text += "_Ничего не найдено по запросу_"
        else:
            text += "_Нет подтверждённых выводов_"
    else:
        for wd in detailed["withdrawals"]:
            wd_username = str(wd["username"] or "Без имени")
            safe_wd_username = (
                wd_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            tx_hash = wd["tx_hash"] or "N/A"
            tx_short = tx_hash[:16] + "..." if len(tx_hash) > 16 else tx_hash
            created = (
                wd["created_at"].strftime("%d.%m %H:%M")
                if wd["created_at"]
                else "N/A"
            )

            text += (
                f"👤 @{safe_wd_username}\n"
                f"   💵 {format_usdt(wd['amount'])} USDT\n"
                f"   🔗 `{tx_short}`\n"
                f"   📅 {created}\n\n"
            )

        text += f"_Страница {detailed['page']} из {detailed['total_pages']}_"
        if search_query:
            text += f"\n_Найдено: {detailed['total_count']}_"

    # Reply keyboard with pagination
    keyboard = admin_withdrawal_history_pagination_keyboard(
        page=page,
        total_pages=detailed["total_pages"],
        is_search_mode=bool(search_query),
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.message(F.text == "🔍 Поиск по выводам")
async def handle_search_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start withdrawal search."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.set_state(AdminStates.searching_withdrawal_history)
    await message.answer(
        "🔍 **Поиск по выводам**\n\n"
        "Введите поисковый запрос:\n"
        "• Username (например: john)\n"
        "• Telegram ID (например: 123456789)\n"
        "• Хеш транзакции (например: 0xabc...)\n\n"
        "Или нажмите ◀️ Назад для отмены.",
        parse_mode="Markdown",
    )


@router.message(AdminStates.searching_withdrawal_history)
async def handle_search_query(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle search query input."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    query = message.text.strip()

    # Check if user wants to go back
    if query in ("◀️ Назад", "👑 Админ-панель"):
        await state.clear()
        if query == "👑 Админ-панель":
            await message.answer(
                "👑 **Панель администратора**\n\nВыберите действие:",
                parse_mode="Markdown",
                reply_markup=get_admin_keyboard_from_data(data),
            )
        else:
            withdrawal_service = WithdrawalService(session)
            await state.update_data(wd_history_page=1, wd_search_query=None)
            await show_withdrawal_page(message, withdrawal_service, page=1)
        return

    # Check for empty query
    if not query:
        await message.answer(
            "❌ Поисковый запрос не может быть пустым.\n"
            "Введите username, telegram ID или хеш транзакции.",
            parse_mode="Markdown",
        )
        return

    # Store search query and show results
    await state.update_data(wd_history_page=1, wd_search_query=query)
    await state.set_state(None)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(
        message, withdrawal_service, page=1, search_query=query
    )


@router.message(F.text == "🗑 Сбросить поиск")
async def handle_clear_search(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Clear search and show all withdrawals."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    await state.update_data(wd_history_page=1, wd_search_query=None)
    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=1)


@router.message(F.text == "⬅️ Пред. страница выводов")
async def handle_wd_prev_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle previous page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    search_query = state_data.get("wd_search_query")
    new_page = max(1, current_page - 1)
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(
        message, withdrawal_service, page=new_page, search_query=search_query
    )


@router.message(F.text == "Вперёд страница выводов ➡️")
async def handle_wd_next_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle next page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    search_query = state_data.get("wd_search_query")
    new_page = current_page + 1
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(
        message, withdrawal_service, page=new_page, search_query=search_query
    )
