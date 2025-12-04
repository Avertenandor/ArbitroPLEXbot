"""
Core calculator functionality.

Содержит основную логику калькулятора доходности и модели данных.
"""

from calculator.core.calculator import ProfitabilityCalculator
from calculator.core.models import DepositLevel, CalculationResult, DepositCalculation

__all__ = [
    "ProfitabilityCalculator",
    "DepositLevel",
    "CalculationResult",
    "DepositCalculation",
]
