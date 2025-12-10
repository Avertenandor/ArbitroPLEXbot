"""
Admin Event Monitor - Financial Notifications.

This module provides notification methods for financial events:
- Deposits
- Withdrawals
- PLEX payments
- Referral bonuses
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from ..constants import EventCategory, EventPriority


if TYPE_CHECKING:
    from ..monitor import AdminEventMonitor


async def notify_new_deposit(
    monitor: "AdminEventMonitor",
    user_id: int,
    username: str | None,
    amount: Decimal,
    tx_hash: str,
    deposit_id: int,
    level: int,
) -> int:
    """Уведомление о новом депозите."""
    return await monitor.notify(
        category=EventCategory.DEPOSIT,
        priority=EventPriority.MEDIUM,
        title="Новый депозит создан",
        details={
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Сумма": f"{amount} USDT",
            "Депозит": f"#{deposit_id}",
            "Уровень": level,
            "TX Hash": tx_hash[:20] + "...",
        },
    )


async def notify_deposit_error(
    monitor: "AdminEventMonitor",
    user_id: int,
    tx_hash: str,
    error: str,
) -> int:
    """Уведомление об ошибке депозита."""
    return await monitor.notify(
        category=EventCategory.DEPOSIT,
        priority=EventPriority.HIGH,
        title="Ошибка обработки депозита",
        details={
            "Пользователь": user_id,
            "TX Hash": tx_hash,
            "Ошибка": error[:100],
        },
        footer="Требуется ручная проверка",
    )


async def notify_unidentified_deposit(
    monitor: "AdminEventMonitor",
    from_address: str,
    amount: Decimal,
    tx_hash: str,
) -> int:
    """Уведомление о неопознанном депозите."""
    return await monitor.notify(
        category=EventCategory.SUSPICIOUS,
        priority=EventPriority.HIGH,
        title="Неопознанный депозит",
        details={
            "Адрес отправителя": from_address,
            "Сумма": f"{amount} USDT",
            "TX Hash": tx_hash,
        },
        footer="Кошелёк не привязан ни к одному пользователю!",
    )


async def notify_withdrawal_request(
    monitor: "AdminEventMonitor",
    user_id: int,
    username: str | None,
    amount: Decimal,
    to_address: str,
) -> int:
    """Уведомление о запросе на вывод."""
    return await monitor.notify(
        category=EventCategory.WITHDRAWAL,
        priority=EventPriority.MEDIUM,
        title="Новый запрос на вывод",
        details={
            "Пользователь": f"{user_id} (@{username or 'нет'})",
            "Сумма": f"{amount} USDT",
            "Адрес": to_address[:20] + "...",
        },
    )


async def notify_withdrawal_completed(
    monitor: "AdminEventMonitor",
    user_id: int,
    amount: Decimal,
    tx_hash: str,
) -> int:
    """Уведомление о выполненном выводе."""
    return await monitor.notify(
        category=EventCategory.WITHDRAWAL,
        priority=EventPriority.LOW,
        title="Вывод выполнен",
        details={
            "Пользователь": user_id,
            "Сумма": f"{amount} USDT",
            "TX Hash": tx_hash[:20] + "...",
        },
    )


async def notify_large_transaction(
    monitor: "AdminEventMonitor",
    transaction_type: str,
    user_id: int,
    amount: Decimal,
    threshold: Decimal,
) -> int:
    """Уведомление о крупной транзакции."""
    return await monitor.notify(
        category=EventCategory.SECURITY,
        priority=EventPriority.HIGH,
        title="Крупная транзакция",
        details={
            "Тип": transaction_type,
            "Пользователь": user_id,
            "Сумма": f"{amount} USDT",
            "Порог": f"{threshold} USDT",
        },
        footer="Рекомендуется проверить транзакцию",
    )


async def notify_plex_payment(
    monitor: "AdminEventMonitor",
    user_id: int,
    amount: int,
    deposit_id: int,
    is_sufficient: bool,
) -> int:
    """Уведомление об оплате PLEX."""
    priority = EventPriority.LOW if is_sufficient else EventPriority.MEDIUM
    status = "✅ Достаточно" if is_sufficient else "⚠️ Недостаточно"

    return await monitor.notify(
        category=EventCategory.PLEX_PAYMENT,
        priority=priority,
        title="Оплата PLEX",
        details={
            "Пользователь": user_id,
            "Сумма PLEX": f"{amount:,}",
            "Депозит": f"#{deposit_id}",
            "Статус": status,
        },
    )


async def notify_referral_bonus(
    monitor: "AdminEventMonitor",
    referrer_id: int,
    referrer_username: str | None,
    amount: Decimal,
    level: int,
    source_user_id: int,
    bonus_type: str,
) -> int:
    """Уведомление о реферальном бонусе (только крупные)."""
    # Уведомляем только о крупных бонусах (> 1 USDT)
    if amount < 1:
        return 0

    return await monitor.notify(
        category=EventCategory.REFERRAL,
        priority=EventPriority.LOW,
        title="Реферальный бонус начислен",
        details={
            "Получатель": f"{referrer_id} (@{referrer_username or 'нет'})",
            "Сумма": f"{amount} USDT",
            "Уровень": level,
            "Источник": f"User #{source_user_id}",
            "Тип": bonus_type,
        },
    )
