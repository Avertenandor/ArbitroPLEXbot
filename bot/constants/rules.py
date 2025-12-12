"""
Rules and levels constants for ArbitroPLEXbot.

Contains access levels, PLEX requirements, and rule texts.
"""

from decimal import Decimal

from app.config.business_constants import (
    DEPOSIT_LEVELS,
    DEPOSIT_LEVEL_ORDER,
    LEVELS,
    MAX_DEPOSITS_PER_USER,
    MINIMUM_PLEX_BALANCE,
    PLEX_CONTRACT_ADDRESS,
    PLEX_PER_DOLLAR_DAILY,
    SYSTEM_WALLET,
    WorkStatus,
    calculate_daily_plex_payment,
    can_spend_plex,
    get_available_plex_balance,
    get_balance_after_spending,
    get_level_by_order,
    get_max_deposits_for_plex_balance,
    get_next_level,
    get_previous_level,
    get_required_plex_for_deposits,
    get_user_level,
    is_amount_in_corridor,
)
from app.config.settings import settings

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


# Export all business logic functions for backward compatibility
__all__ = [
    # Imported constants from business_constants
    "LEVELS",
    "DEPOSIT_LEVELS",
    "PLEX_PER_DOLLAR_DAILY",
    "MINIMUM_PLEX_BALANCE",
    "MAX_DEPOSITS_PER_USER",
    "PLEX_CONTRACT_ADDRESS",
    "DEPOSIT_LEVEL_ORDER",
    "SYSTEM_WALLET",
    "WorkStatus",
    # Local constants
    "PLEX_TOKEN_ADDRESS",
    "LEVELS_TABLE",
    "RULES_SHORT_TEXT",
    "RULES_BRIEF_VERSION",
    "RULES_FULL_TEXT",
    # Imported functions from business_constants
    "get_available_plex_balance",
    "can_spend_plex",
    "get_balance_after_spending",
    "get_user_level",
    "get_max_deposits_for_plex_balance",
    "get_required_plex_for_deposits",
    "calculate_daily_plex_payment",
    "get_level_by_order",
    "get_previous_level",
    "get_next_level",
    "is_amount_in_corridor",
]

# Short rules text (for auth and welcome)
RULES_SHORT_TEXT = """
⚠️ **ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:**

1️⃣ **Баланс PLEX** на кошельке должен соответствовать уровню
2️⃣ **Кролики** — владение минимумом на [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)
3️⃣ **Оплата работы:** 10 PLEX в сутки за каждый $ депозита

🔴 **НЕСГОРАЕМЫЙ МИНИМУМ:** 5,000 PLEX всегда должны оставаться на кошельке!
💡 Использовать можно только PLEX **сверх** этой суммы.
"""

# Brief rules version (for info page with "Read more" button)
RULES_BRIEF_VERSION = f"""
📋 **ПРАВИЛА (кратко)**
━━━━━━━━━━━━━━━━━━

💎 **PLEX:** 10 монет за $1 депозита/день
🐰 **Кролики:** минимум 1 на DEXRabbit
📊 **Уровни:** 1→2→3→4→5 (по балансу PLEX)
🔴 **НЕСГОРАЕМЫЙ МИНИМУМ:** 5,000 PLEX
💡 Использовать можно ТОЛЬКО сверх минимума!

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

• **НЕСГОРАЕМЫЙ МИНИМУМ:** 5,000 PLEX всегда на кошельке!
• **Использовать можно ТОЛЬКО PLEX сверх 5,000**
  Оплата депозитов, авторизация — всё из свободной суммы

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
