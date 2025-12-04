"""
Type definitions for calculator module.

Определяет TypedDict классы и пользовательские типы,
используемые в калькуляторе доходности.
"""

from typing import TypedDict, Optional


class LevelDataDict(TypedDict):
    """
    Словарь данных для одного уровня.

    Attributes:
        level_number: Номер уровня (1-10)
        investment: Инвестиция в уровень
        profit: Прибыль с уровня
        total_investment: Накопленная инвестиция
        total_profit: Накопленная прибыль
        cumulative_result: Чистый результат (прибыль - инвестиция)
        roi: ROI в процентах
    """
    level_number: int
    investment: float
    profit: float
    total_investment: float
    total_profit: float
    cumulative_result: float
    roi: float


class CalculationResultDict(TypedDict):
    """
    Результат расчета доходности.

    Attributes:
        levels: Список данных по уровням
        total_investment: Общая инвестиция
        total_profit: Общая прибыль
        net_result: Чистый результат
        overall_roi: Общий ROI в процентах
    """
    levels: list[LevelDataDict]
    total_investment: float
    total_profit: float
    net_result: float
    overall_roi: float
