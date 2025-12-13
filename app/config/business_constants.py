"""
Business logic constants for ArbitroPLEXbot.

Central location for business rules and constants used across the application.
This module can be imported by both app.services and bot handlers without circular dependencies.
"""

from decimal import Decimal

from app.config.deposit_levels import (
    DEPOSIT_LEVELS as DEPOSIT_LEVELS_CONFIG,
    DEPOSIT_LEVEL_ORDER as DEPOSIT_LEVEL_ORDER_TYPES,
    DepositLevelType,
    get_level_by_order as _get_level_by_order,
    get_next_level as _get_next_level,
    get_previous_level as _get_previous_level,
    is_amount_in_corridor as _is_amount_in_corridor,
)
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
# Импортировано из единого источника истины: app.config.deposit_levels
DEPOSIT_LEVELS = {
    level_type.value: {
        "min": int(config.min_amount),
        "max": int(config.max_amount),
        "name": config.display_name,
        "order": config.order,
    }
    for level_type, config in DEPOSIT_LEVELS_CONFIG.items()
}

# Daily PLEX cost per dollar of deposit
PLEX_PER_DOLLAR_DAILY = 10

# Minimum PLEX balance required to work with system (non-withdrawable reserve)
MINIMUM_PLEX_BALANCE = 5000

# Maximum deposits per user
MAX_DEPOSITS_PER_USER = 5

# PLEX token contract address on BSC
PLEX_CONTRACT_ADDRESS = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"

# Deposit level order for sequential validation
# Импортировано из единого источника истины: app.config.deposit_levels
DEPOSIT_LEVEL_ORDER = [level_type.value for level_type in DEPOSIT_LEVEL_ORDER_TYPES]

# System wallet for PLEX payments (from settings)
SYSTEM_WALLET = settings.auth_system_wallet_address


# Work status constants
class WorkStatus:
    """User work status constants."""
    ACTIVE = "active"                       # Normal operation
    SUSPENDED_NO_PLEX = "suspended_no_plex"  # Balance < 5000 PLEX
    SUSPENDED_NO_PAYMENT = "suspended_no_payment"  # PLEX payment not received


def get_available_plex_balance(total_plex: int | Decimal) -> Decimal:
    """
    Calculate available PLEX balance (above minimum reserve).

    The minimum reserve (5000 PLEX) must always remain on the wallet.
    Only PLEX above this minimum can be used for:
    - Daily deposit payments (10 PLEX per $1)
    - Authorization payments
    - Transfers to other wallets

    Args:
        total_plex: Total PLEX balance on wallet

    Returns:
        Available PLEX that can be spent (total - minimum reserve)
    """
    total = Decimal(str(total_plex))
    minimum = Decimal(str(MINIMUM_PLEX_BALANCE))
    available = total - minimum
    return max(Decimal("0"), available)


def can_spend_plex(total_plex: int | Decimal, amount_to_spend: int | Decimal) -> bool:
    """
    Check if user can spend specified amount of PLEX.

    Ensures that after spending, the balance won't drop below minimum reserve.

    Args:
        total_plex: Current total PLEX balance
        amount_to_spend: Amount user wants to spend

    Returns:
        True if spending is allowed (balance after >= minimum)
    """
    available = get_available_plex_balance(total_plex)
    return available >= Decimal(str(amount_to_spend))


def get_balance_after_spending(
    total_plex: int | Decimal,
    amount_to_spend: int | Decimal
) -> tuple[Decimal, bool]:
    """
    Calculate balance after spending and check if valid.

    Args:
        total_plex: Current total PLEX balance
        amount_to_spend: Amount to spend

    Returns:
        Tuple of (balance_after_spending, is_valid)
        is_valid is True if balance remains >= minimum reserve
    """
    total = Decimal(str(total_plex))
    spend = Decimal(str(amount_to_spend))
    balance_after = total - spend
    is_valid = balance_after >= Decimal(str(MINIMUM_PLEX_BALANCE))
    return (balance_after, is_valid)


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
# Импортируем функции из единого источника истины


def get_level_by_order(order: int) -> str | None:
    """
    Get deposit level type by order number.

    Args:
        order: Order number (0-5)

    Returns:
        Level type string or None if not found
    """
    config = _get_level_by_order(order)
    return config.level_type.value if config else None


def get_previous_level(level_type: str) -> str | None:
    """
    Get previous deposit level in the sequence.

    Args:
        level_type: Current level type

    Returns:
        Previous level type or None if this is the first level
    """
    config = _get_previous_level(level_type)
    return config.level_type.value if config else None


def get_next_level(level_type: str) -> str | None:
    """
    Get next deposit level in the sequence.

    Args:
        level_type: Current level type

    Returns:
        Next level type or None if this is the last level
    """
    config = _get_next_level(level_type)
    return config.level_type.value if config else None


def is_amount_in_corridor(level_type: str, amount: Decimal) -> bool:
    """
    Check if deposit amount is within the level corridor.

    Args:
        level_type: Deposit level type
        amount: Deposit amount to check

    Returns:
        True if amount is within min/max range for the level
    """
    return _is_amount_in_corridor(level_type, amount)
