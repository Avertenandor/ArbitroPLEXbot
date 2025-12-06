"""
Rules and levels constants for ArbitroPLEXbot.

Contains access levels, PLEX requirements, and rule texts.
"""

from decimal import Decimal

from app.config.settings import settings

# Access levels configuration
LEVELS = {
    1: {"plex": 5000, "rabbits": 1, "deposits": 1},
    2: {"plex": 10000, "rabbits": 3, "deposits": 2},
    3: {"plex": 15000, "rabbits": 5, "deposits": 3},
    4: {"plex": 20000, "rabbits": 10, "deposits": 4},
    5: {"plex": 25000, "rabbits": 15, "deposits": 5},
}

# Deposit levels configuration with amount corridors
DEPOSIT_LEVELS = {
    "test": {"min": 30, "max": 100, "name": "Тестовый", "order": 0},
    "level_1": {"min": 100, "max": 500, "name": "Уровень 1", "order": 1},
    "level_2": {"min": 700, "max": 1200, "name": "Уровень 2", "order": 2},
    "level_3": {"min": 1400, "max": 2200, "name": "Уровень 3", "order": 3},
    "level_4": {"min": 2500, "max": 3500, "name": "Уровень 4", "order": 4},
    "level_5": {"min": 4000, "max": 7000, "name": "Уровень 5", "order": 5},
}

# Daily PLEX cost per dollar of deposit
PLEX_PER_DOLLAR_DAILY = 10

# PLEX token contract address
PLEX_CONTRACT_ADDRESS = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"

# Deposit level order for sequential validation
DEPOSIT_LEVEL_ORDER = ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]

# Minimum PLEX balance required to work with system
MINIMUM_PLEX_BALANCE = 5000

# Maximum deposits per user
MAX_DEPOSITS_PER_USER = 5


# Work status constants
class WorkStatus:
    """User work status constants."""
    ACTIVE = "active"                       # Normal operation
    SUSPENDED_NO_PLEX = "suspended_no_plex"  # Balance < 5000 PLEX
    SUSPENDED_NO_PAYMENT = "suspended_no_payment"  # PLEX payment not received


# System wallet for PLEX payments (from settings)
SYSTEM_WALLET = settings.auth_system_wallet_address

# PLEX token address (from settings)
PLEX_TOKEN_ADDRESS = settings.auth_plex_token_address

# Levels table for display
LEVELS_TABLE = """
┌─────────┬──────────┬──────────┬──────────┐
│ Уровень │   PLEX   │ Кролики  │ Депозиты │
├─────────┼──────────┼──────────┼──────────┤
│    1    │   5,000  │    1     │    1     │
│    2    │  10,000  │    3     │    2     │
│    3    │  15,000  │    5     │    3     │
│    4    │  20,000  │   10     │    4     │
│    5    │  25,000  │   15     │    5     │
└─────────┴──────────┴──────────┴──────────┘
"""

# Short rules text (for auth and welcome)
RULES_SHORT_TEXT = """
⚠️ **ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:**

1️⃣ **Баланс PLEX** на кошельке должен соответствовать уровню
2️⃣ **Кролики** — владение минимумом на [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)
3️⃣ **Оплата работы:** 10 PLEX в сутки за каждый $ депозита

🔴 **ВАЖНО:** Монеты PLEX нельзя выводить с кошелька!
Продажа/перевод = отключение от бота + возврат депозитов
"""

# Brief rules version (for info page with "Read more" button)
RULES_BRIEF_VERSION = f"""
📋 **ПРАВИЛА (кратко)**
━━━━━━━━━━━━━━━━━━

💎 **PLEX:** 10 монет за $1 депозита/день
🐰 **Кролики:** минимум 1 на DEXRabbit
📊 **Уровни:** 1→2→3→4→5 (по балансу PLEX)
🔴 **ВАЖНО:** PLEX нельзя выводить!

💳 **Кошелек для оплаты:**
`{SYSTEM_WALLET}`

⏰ **Сроки:** оплата до 24ч, блокировка через 49ч
💰 **Доход:** 30-70% в день
"""

# Full rules text (for Rules button)
RULES_FULL_TEXT = f"""
📋 **ПРАВИЛА РАБОТЫ В ArbitroPLEXbot**

━━━━━━━━━━━━━━━━━━━━━━

📊 **УРОВНИ ДОСТУПА:**
{LEVELS_TABLE}

━━━━━━━━━━━━━━━━━━━━━━

⚠️ **ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:**

1️⃣ **Баланс PLEX на кошельке**
   • Минимум соответствует вашему уровню
   • Монеты должны находиться на кошельке постоянно
   • Проверка происходит автоматически

2️⃣ **Владение кроликами**
   • Минимум соответствует вашему уровню
   • Покупка на ферме партнеров [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)

3️⃣ **Ежедневная оплата работы**
   • 10 PLEX в сутки за каждый доллар депозита
   • Пример: депозит $100 = 1,000 PLEX/сутки
   • Оплата на системный кошелек

━━━━━━━━━━━━━━━━━━━━━━

💳 **КОШЕЛЕК ДЛЯ ОПЛАТЫ:**
`{SYSTEM_WALLET}`

━━━━━━━━━━━━━━━━━━━━━━

🔴 **КРИТИЧЕСКИЕ ПРАВИЛА:**

• **Монеты PLEX нельзя выводить с кошелька!**
  Продал/перевел = отключение от бота

• **При нарушении депозиты возвращаются**

• **Сумму депозита менять нельзя**
  Можно вывести — остальные продолжат работать

━━━━━━━━━━━━━━━━━━━━━━

⏰ **СРОКИ ОПЛАТЫ:**

• Оплата должна поступить в течение 24 часов
• Через 25 часов — предупреждение
• Через 49 часов — блокировка депозита

━━━━━━━━━━━━━━━━━━━━━━

📊 **Доход:** от **30% до 70%** в день!
"""


def get_user_level(plex_balance: int | Decimal) -> int:
    """
    Determine user level based on PLEX balance.

    Args:
        plex_balance: User's PLEX token balance

    Returns:
        User level (1-5) or 0 if insufficient balance
    """
    balance = int(plex_balance)

    for level in range(5, 0, -1):
        if balance >= LEVELS[level]["plex"]:
            return level

    return 0


def get_max_deposits_for_plex_balance(plex_balance: int | Decimal) -> int:
    """
    Get maximum allowed deposits for given PLEX balance.

    Args:
        plex_balance: User's PLEX token balance

    Returns:
        Maximum number of deposits allowed
    """
    level = get_user_level(plex_balance)
    if level == 0:
        return 0
    return LEVELS[level]["deposits"]


def get_required_plex_for_deposits(deposit_count: int) -> int:
    """
    Get required PLEX balance for given number of deposits.

    Args:
        deposit_count: Number of deposits user wants to have

    Returns:
        Required PLEX balance
    """
    for level in range(1, 6):
        if LEVELS[level]["deposits"] >= deposit_count:
            return LEVELS[level]["plex"]

    return LEVELS[5]["plex"]  # Max level


def calculate_daily_plex_payment(deposit_amount_usd: Decimal) -> Decimal:
    """
    Calculate daily PLEX payment required for deposit.

    Args:
        deposit_amount_usd: Deposit amount in USD

    Returns:
        Required PLEX payment per day
    """
    return Decimal(str(deposit_amount_usd)) * Decimal(str(PLEX_PER_DOLLAR_DAILY))


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
