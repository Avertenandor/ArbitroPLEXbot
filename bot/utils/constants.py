"""
Bot Constants
Common constants used across bot handlers
"""

from decimal import Decimal

from app.config.business_constants import (
    DEPOSIT_LEVELS,
    DEPOSIT_LEVEL_ORDER,
    PLEX_CONTRACT_ADDRESS,
    PLEX_PER_DOLLAR_DAILY,
    get_level_by_order,
    get_next_level,
    get_previous_level,
    is_amount_in_corridor,
)


# Referral commission rates by level
# 3-level referral program: 5% from deposits AND earnings at each level
REFERRAL_RATES = {
    1: 0.05,  # 5% for level 1 (direct referrals)
    2: 0.05,  # 5% for level 2
    3: 0.05,  # 5% for level 3
}

# ROI cap for level 1 deposits
ROI_CAP_MULTIPLIER = 5.0  # 500% (5x)

# Error messages
ERROR_MESSAGES = {
    "NOT_REGISTERED": "❌ Пожалуйста, сначала зарегистрируйтесь",
    "ADMIN_ONLY": "❌ Эта функция доступна только администраторам",
    "INSUFFICIENT_BALANCE": "❌ Недостаточно средств на балансе",
    "INVALID_WALLET": "❌ Неверный адрес кошелька",
    "INVALID_AMOUNT": "❌ Неверная сумма",
    "USER_BANNED": "❌ Ваш аккаунт заблокирован",
}

# Button labels
BUTTON_LABELS = {
    "MAIN_MENU": "🏠 Главное меню",
    "BACK": "◀️ Назад",
    "CANCEL": "❌ Отмена",
    "CONFIRM": "✅ Подтвердить",
}

# Admin broadcast cooldown (1 minute)
BROADCAST_COOLDOWN_MS = 1 * 60 * 1000


# Export all for backward compatibility
__all__ = [
    # Imported constants
    "DEPOSIT_LEVELS",
    "DEPOSIT_LEVEL_ORDER",
    "PLEX_CONTRACT_ADDRESS",
    "PLEX_PER_DOLLAR_DAILY",
    # Local constants
    "REFERRAL_RATES",
    "ROI_CAP_MULTIPLIER",
    "ERROR_MESSAGES",
    "BUTTON_LABELS",
    "BROADCAST_COOLDOWN_MS",
    # Imported functions
    "get_level_by_order",
    "get_previous_level",
    "get_next_level",
    "is_amount_in_corridor",
]
