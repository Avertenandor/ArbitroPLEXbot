"""
Bot Constants
Common constants used across bot handlers
"""

from decimal import Decimal

# Referral commission rates by level
# 3-level referral program: 5% from deposits AND earnings at each level
REFERRAL_RATES = {
    1: 0.05,  # 5% for level 1 (direct referrals)
    2: 0.05,  # 5% for level 2
    3: 0.05,  # 5% for level 3
}

# Deposit levels configuration with amount corridors
# New structure with min/max ranges for each level
DEPOSIT_LEVELS = {
    "test": {"min": 30, "max": 100, "name": "Тестовый", "order": 0},
    "level_1": {"min": 100, "max": 500, "name": "Уровень 1", "order": 1},
    "level_2": {"min": 700, "max": 1200, "name": "Уровень 2", "order": 2},
    "level_3": {"min": 1400, "max": 2200, "name": "Уровень 3", "order": 3},
    "level_4": {"min": 2500, "max": 3500, "name": "Уровень 4", "order": 4},
    "level_5": {"min": 4000, "max": 7000, "name": "Уровень 5", "order": 5},
}

# PLEX token - 10 coins per $1 deposit daily
PLEX_PER_DOLLAR_DAILY = 10

# PLEX token contract address
PLEX_CONTRACT_ADDRESS = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"

# Deposit level order for sequential validation
DEPOSIT_LEVEL_ORDER = ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]

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


# Deposit level helper functions

def get_level_by_order(order: int) -> str | None:
    """
    Get deposit level type by order number.

    Args:
        order: Order number (0-5)

    Returns:
        Level type string or None if not found
    """
    for level_type, level_data in DEPOSIT_LEVELS.items():
        if level_data["order"] == order:
            return level_type
    return None


def get_previous_level(level_type: str) -> str | None:
    """
    Get previous deposit level in the sequence.

    Args:
        level_type: Current level type

    Returns:
        Previous level type or None if this is the first level
    """
    if level_type not in DEPOSIT_LEVELS:
        return None

    current_order = DEPOSIT_LEVELS[level_type]["order"]
    if current_order == 0:
        return None

    return get_level_by_order(current_order - 1)


def get_next_level(level_type: str) -> str | None:
    """
    Get next deposit level in the sequence.

    Args:
        level_type: Current level type

    Returns:
        Next level type or None if this is the last level
    """
    if level_type not in DEPOSIT_LEVELS:
        return None

    current_order = DEPOSIT_LEVELS[level_type]["order"]
    max_order = max(level["order"] for level in DEPOSIT_LEVELS.values())

    if current_order >= max_order:
        return None

    return get_level_by_order(current_order + 1)


def is_amount_in_corridor(level_type: str, amount: Decimal) -> bool:
    """
    Check if deposit amount is within the level corridor.

    Args:
        level_type: Deposit level type
        amount: Deposit amount to check

    Returns:
        True if amount is within min/max range for the level
    """
    if level_type not in DEPOSIT_LEVELS:
        return False

    level_data = DEPOSIT_LEVELS[level_type]
    amount_value = Decimal(str(amount))

    return Decimal(str(level_data["min"])) <= amount_value <= Decimal(str(level_data["max"]))
