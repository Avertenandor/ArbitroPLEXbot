"""
Formatting helpers for financial reports.

Contains helper functions to format financial data for display.
"""

from app.services.financial_report_service import UserDetailedFinancialDTO
from bot.utils.formatters import (
    format_balance,
    format_tx_hash_with_link,
    format_wallet_short,
)
from bot.utils.pagination import PaginationBuilder


# Initialize pagination builder for reuse
pagination_builder = PaginationBuilder()


def format_user_financial_detail(dto: UserDetailedFinancialDTO) -> str:
    """Format detailed user financial card."""
    username = f"@{dto.username}" if dto.username else f"ID: {dto.telegram_id}"

    # Общая информация
    text = (
        f"📂 **Детальная финансовая карточка**\n\n"
        f"👤 Пользователь: {username}\n"
        f"🆔 User ID: `{dto.user_id}`\n"
        f"💳 Кошелек: `{format_wallet_short(dto.current_wallet)}`\n\n"
        f"💰 **Финансовая сводка:**\n"
        f"├ Депозиты: `{format_balance(dto.total_deposited, decimals=2)}` USDT\n"
        f"├ Заработано: `{format_balance(dto.total_earned, decimals=2)}` USDT\n"
        f"├ Выведено: `{format_balance(dto.total_withdrawn, decimals=2)}` USDT\n"
        f"├ Баланс: `{format_balance(dto.balance, decimals=2)}` USDT\n"
        f"└ Ожидает: `{format_balance(dto.pending_earnings, decimals=2)}` USDT\n\n"
    )

    # Последние 5 депозитов
    if dto.deposits:
        text += "📊 **Последние депозиты** (топ-5):\n"
        for i, dep in enumerate(dto.deposits[:5], 1):
            status_emoji = "✅" if dep.is_completed else "⏳"
            tx_link = format_tx_hash_with_link(dep.tx_hash) if dep.tx_hash else "—"
            text += (
                f"{i}. {status_emoji} Lvl {dep.level}: `{format_balance(dep.amount, decimals=2)}` USDT\n"
                f"   ROI: `{format_balance(dep.roi_paid, decimals=2)}`/`{format_balance(dep.roi_cap, decimals=2)}` | TX: {tx_link}\n"
            )
        text += f"\n_Всего депозитов: {len(dto.deposits)}_\n\n"
    else:
        text += "📊 Депозитов нет\n\n"

    # Последние 5 выводов
    if dto.withdrawals:
        text += "💸 **Последние выводы** (топ-5):\n"
        for i, wd in enumerate(dto.withdrawals[:5], 1):
            status_emoji = "✅" if wd.status == "confirmed" else "⏳"
            tx_link = format_tx_hash_with_link(wd.tx_hash) if wd.tx_hash else "—"
            text += (
                f"{i}. {status_emoji} `{format_balance(wd.amount, decimals=2)}` USDT\n"
                f"   TX: {tx_link}\n"
            )
        text += f"\n_Всего выводов: {len(dto.withdrawals)}_\n\n"
    else:
        text += "💸 Выводов нет\n\n"

    # История смены кошельков
    if dto.wallet_history:
        wallet_count = len(dto.wallet_history)
        text += f"💳 **История кошельков:** {wallet_count} изменений\n\n"
    else:
        text += "💳 Кошелек не менялся\n\n"

    text += "Выберите раздел для детального просмотра:"

    return text


def format_deposits_page(
    deposits: list, page: int, per_page: int, total_pages: int
) -> str:
    """Format deposits page."""
    page_deposits = pagination_builder.get_page_items(deposits, page, per_page)
    start_idx = (page - 1) * per_page

    text = f"📊 **Все депозиты** (стр. {page}/{total_pages}):\n\n"

    for i, dep in enumerate(page_deposits, start=start_idx + 1):
        status_emoji = "✅" if dep.is_completed else "⏳"
        tx_link = format_tx_hash_with_link(dep.tx_hash) if dep.tx_hash else "—"
        date_str = dep.created_at.strftime("%Y-%m-%d %H:%M")

        text += (
            f"{i}. {status_emoji} **Lvl {dep.level}** | `{format_balance(dep.amount, decimals=2)}` USDT\n"
            f"   Дата: {date_str}\n"
            f"   ROI: `{format_balance(dep.roi_paid, decimals=2)}`/`{format_balance(dep.roi_cap, decimals=2)}` USDT"
        )

        if dep.roi_percent:
            text += f" ({format_balance(dep.roi_percent, decimals=1)}%)\n"
        else:
            text += "\n"

        text += f"   TX: {tx_link}\n\n"

    return text


def format_withdrawals_page(
    withdrawals: list, page: int, per_page: int, total_pages: int
) -> str:
    """Format withdrawals page."""
    page_withdrawals = pagination_builder.get_page_items(withdrawals, page, per_page)
    start_idx = (page - 1) * per_page

    text = f"💸 **Все выводы** (стр. {page}/{total_pages}):\n\n"

    for i, wd in enumerate(page_withdrawals, start=start_idx + 1):
        status_emoji = "✅" if wd.status == "confirmed" else "⏳"
        tx_link = format_tx_hash_with_link(wd.tx_hash) if wd.tx_hash else "—"
        date_str = wd.created_at.strftime("%Y-%m-%d %H:%M")

        text += (
            f"{i}. {status_emoji} `{format_balance(wd.amount, decimals=2)}` USDT\n"
            f"   Дата: {date_str}\n"
            f"   Статус: {wd.status}\n"
            f"   TX: {tx_link}\n\n"
        )

    return text
