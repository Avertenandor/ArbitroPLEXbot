"""
ArbitroPLEX Profitability Calculator.

Standalone package for deposit ROI calculations.

Example:
    >>> from calculator import ProfitabilityCalculator, DEFAULT_LEVELS
    >>> from decimal import Decimal
    >>>
    >>> calc = ProfitabilityCalculator()
    >>> level = DEFAULT_LEVELS[0]  # Level 1: 1000 USDT, 1.117%/day
    >>>
    >>> result = calc.calculate_full_projection(
    ...     Decimal("1000"),
    ...     level.roi_percent,
    ...     level.roi_cap_percent
    ... )
    >>> print(f"Daily reward: {result.daily_reward} USDT")
    Daily reward: 11.17 USDT
"""

from calculator.constants import (
    DEFAULT_LEVELS,
    get_active_levels,
    get_level_by_number,
    get_level_for_amount,
)
from calculator.core.calculator import ProfitabilityCalculator
from calculator.core.models import (
    CalculationResult,
    DepositCalculation,
    DepositLevel,
)
from calculator.utils import (
    format_calculation_result,
    format_calculation_result_ru,
    format_currency,
    format_days,
    format_days_ru,
    format_number,
    format_percentage,
)


__version__ = "1.0.0"
__all__ = [
    # Core
    "ProfitabilityCalculator",
    # Models
    "DepositLevel",
    "CalculationResult",
    "DepositCalculation",
    # Constants
    "DEFAULT_LEVELS",
    "get_level_by_number",
    "get_level_for_amount",
    "get_active_levels",
    # Formatters
    "format_currency",
    "format_percentage",
    "format_number",
    "format_days",
    "format_days_ru",
    "format_calculation_result",
    "format_calculation_result_ru",
]
