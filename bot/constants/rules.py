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

# Daily PLEX cost per dollar of deposit
PLEX_PER_DOLLAR_DAILY = 10

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
