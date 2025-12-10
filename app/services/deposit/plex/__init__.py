"""
PLEX Payment Monitoring Service.

Модуль для мониторинга и управления ежедневными PLEX платежами.

Компоненты:
- PlexPaymentMonitor: Главный фасад для мониторинга PLEX платежей
- PlexPaymentNotifier: Уведомления пользователей о статусе PLEX платежей
- PlexTransferScanner: Сканирование блокчейна на PLEX переводы
- PlexPaymentProcessor: Обработка платежей и обновление статусов

Использование:
    from app.services.deposit.plex import PlexPaymentMonitor

    # Создание монитора
    monitor = PlexPaymentMonitor(session, blockchain_service)

    # Проверка платежа пользователя
    result = await monitor.check_user_plex_payment(user_id, deposit_id)

    # Обработка всех ожидающих платежей (для job)
    stats = await monitor.process_pending_payments()
"""

from .monitor import PlexPaymentMonitor
from .notifier import PlexPaymentNotifier
from .processor import PlexPaymentProcessor
from .scanner import PlexTransferScanner


__all__ = [
    "PlexPaymentMonitor",
    "PlexPaymentNotifier",
    "PlexPaymentProcessor",
    "PlexTransferScanner",
]
