"""
Financial list handlers.

Displays paginated list of users with financial summary.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.financial_report_service import FinancialReportService
from bot.handlers.admin.financials.states import AdminFinancialStates
from bot.keyboards.reply import admin_financial_list_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import escape_md, format_balance
from bot.utils.pagination import PaginationBuilder


router = Router()
pagination_builder = PaginationBuilder()


@router.message(StateFilter('*'), F.text.contains("Финансовая"))
async def show_financial_list(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show paginated list of users with financial summary.
    Entry point for the section.
    """
    await clear_state_preserve_admin_token(state)
    logger.info(f"[FINANCIALS] Handler triggered by: {message.text}")
    # Проверка прав доступа: любой админ
    # R-NEW: Allow basic admins to view financial reports (per user request)
    # Previously restricted to extended/super, now open.
    pass

    service = FinancialReportService(session)

    # Get platform-wide financial statistics
    platform_stats = await service.get_platform_financial_stats()

    # Default page 1
    page = 1
    per_page = 10

    users, total_count = await service.get_users_financial_summary(page, per_page)
    total_pages = pagination_builder.get_total_pages(total_count, per_page)

    await state.set_state(AdminFinancialStates.viewing_list)
    await state.update_data(current_page=page, total_pages=total_pages)

    # Format amounts for display
    def fmt(val):
        return f"{float(val):,.2f}".replace(",", " ")

    total_users_line = (
        f"👥 Пользователей: `{platform_stats.total_users}` "
        f"\\(✅ {platform_stats.verified_users} верифиц\\.\\)\n"
    )

    total_deps_line = (
        f"📥 Всего: `{platform_stats.total_deposits_count}` "
        f"на `{fmt(platform_stats.total_deposited_amount)}` USDT\n"
    )

    active_deps_line = (
        f"🔄 Активных: `{platform_stats.active_deposits_count}` "
        f"на `{fmt(platform_stats.active_deposits_amount)}` USDT\n\n"
    )

    total_withdrawals_line = (
        f"📤 Выведено: `{platform_stats.total_withdrawals_count}` "
        f"на `{fmt(platform_stats.total_withdrawn_amount)}` USDT\n"
    )

    pending_withdrawals_line = (
        f"⏳ Ожидают: `{platform_stats.pending_withdrawals_count}` "
        f"на `{fmt(platform_stats.pending_withdrawals_amount)}` USDT\n\n"
    )

    text = (
        "💰 **Финансовая отчетность**\n\n"
        "📊 **Общая статистика платформы:**\n"
        f"{total_users_line}"
        f"👛 С депозитами: `{platform_stats.users_with_deposits}`\n\n"

        "💵 **Депозиты:**\n"
        f"{total_deps_line}"
        f"{active_deps_line}"

        "💸 **Выводы:**\n"
        f"{total_withdrawals_line}"
        f"{pending_withdrawals_line}"

        "📈 **Начисления:**\n"
        f"💎 ROI выплачено: `{fmt(platform_stats.total_roi_paid)}` USDT\n"
        f"💰 Балансы польз\\.: "
        f"`{fmt(platform_stats.total_pending_balance)}` USDT\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Пользователей: `{total_count}` "
        f"\\| Стр\\. `{page}/{total_pages}`\n"
        "Выберите пользователя для детальной информации:"
    )

    await message.answer(
        text,
        parse_mode="MarkdownV2",
        reply_markup=admin_financial_list_keyboard(users, page, total_pages),
    )


@router.message(
    AdminFinancialStates.viewing_list,
    F.text.in_({"⬅ Предыдущая", "Следующая ➡"})
)
async def handle_pagination(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle pagination for financial list."""
    state_data = await state.get_data()
    current_page = state_data.get("current_page", 1)
    total_pages = state_data.get("total_pages", 1)

    if message.text == "⬅ Предыдущая" and current_page > 1:
        current_page -= 1
    elif message.text == "Следующая ➡" and current_page < total_pages:
        current_page += 1
    else:
        # No change needed
        return

    service = FinancialReportService(session)
    users, total_count = await service.get_users_financial_summary(current_page, 10)

    # Re-calculate in case count changed
    total_pages = pagination_builder.get_total_pages(total_count, 10)
    if current_page > total_pages:
        current_page = total_pages

    await state.update_data(current_page=current_page, total_pages=total_pages)

    text = (
        "💰 **Финансовая отчетность**\n\n"
        f"Всего пользователей: `{total_count}`\n"
        f"Страница: `{current_page}/{total_pages}`\n"
        "Выберите пользователя для просмотра "
        "детальной информации:"
    )

    await message.answer(
        text,
        parse_mode="MarkdownV2",
        reply_markup=admin_financial_list_keyboard(users, current_page, total_pages),
    )


@router.message(AdminFinancialStates.viewing_list, F.text.regexp(r'^👤 \d+\. @?'))
async def handle_user_selection(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle selection of a user from the list."""
    # Format is "👤 {id}. {username} | ..."
    try:
        # Extract ID from start of string
        user_id_str = message.text.split('.')[0].replace('👤 ', '')
        user_id = int(user_id_str)
    except (ValueError, IndexError):
        await message.answer("❌ Ошибка при выборе пользователя.")
        return

    service = FinancialReportService(session)
    details = await service.get_user_financial_details(user_id)

    if not details:
        await message.answer("❌ Пользователь не найден.")
        return

    # Escape data for MarkdownV2
    username = escape_md(details.user.username or "Нет юзернейма")
    escape_md(f"{details.user.telegram_id}")  # Use ID if name not available easily here

    reg_date = details.user.created_at.strftime('%d\\.%m\\.%Y')
    if details.user.last_active:
        last_active = details.user.last_active.strftime(
            '%d\\.%m\\.%Y %H:%M'
        )
    else:
        last_active = "Неизвестно"

    if details.last_deposit_date:
        last_dep = details.last_deposit_date.strftime(
            '%d\\.%m\\.%Y %H:%M'
        )
    else:
        last_dep = "Нет"

    if details.last_withdrawal_date:
        last_with = details.last_withdrawal_date.strftime(
            '%d\\.%m\\.%Y %H:%M'
        )
    else:
        last_with = "Нет"

    text = (
        f"📂 **Личное дело пользователя**\n"
        f"ID: `{details.user.id}`\n"
        f"Telegram ID: `{details.user.telegram_id}`\n"
        f"Username: @{username}\n\n"

        f"📅 Регистрация: {reg_date}\n"
        f"🕒 Активность: {last_active}\n\n"

        f"💰 **Финансы**:\n"
        f"📥 Всего внесено: `{format_balance(details.total_deposited, decimals=2)}` USDT\n"
        f"📤 Всего выведено: `{format_balance(details.total_withdrawn, decimals=2)}` USDT\n"
        f"📈 Начислено ROI: `{format_balance(details.total_earned, decimals=2)}` USDT\n"
        f"📊 Активных депозитов: `{details.active_deposits_count}`\n\n"

        f"Последний депозит: {last_dep}\n"
        f"Последний вывод: {last_with}"
    )

    await state.set_state(AdminFinancialStates.viewing_user)
    await state.update_data(selected_user_id=user_id)

    await message.answer(
        text,
        parse_mode="MarkdownV2",
        reply_markup=admin_user_financial_keyboard(),
    )


# Import keyboard after defining handlers to avoid circular imports
from bot.keyboards.reply import admin_user_financial_keyboard
