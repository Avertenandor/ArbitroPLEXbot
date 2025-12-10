"""
Deposit Services Module.

Модуль содержит сервисы для работы с депозитами.

Подмодули:
- plex: Мониторинг и управление PLEX платежами
- lifecycle: Создание, подтверждение и управление статусами депозитов
- roi: Расчёты и начисления ROI
- validation: Валидация уровней депозитов, сумм и последовательности
- service: Основной фасад DepositService
- validation_service: Сервис валидации депозитов
"""

from .constants import DEPOSIT_LEVELS, PARTNER_REQUIREMENTS
from .plex import PlexPaymentMonitor, PlexPaymentNotifier
from .service import DepositService
from .validation_service import DepositValidationService


__all__ = [
    "DepositService",
    "DepositValidationService",
    "PlexPaymentMonitor",
    "PlexPaymentNotifier",
    "DEPOSIT_LEVELS",
    "PARTNER_REQUIREMENTS",
]
