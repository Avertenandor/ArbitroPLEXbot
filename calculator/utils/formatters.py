"""
Formatting utilities for numbers and currency.

Функции для форматирования чисел, валюты и процентов
в читаемый вид для отображения пользователю.
"""

from typing import Optional, Union
from decimal import Decimal


def format_currency(
    amount: Union[float, Decimal],
    currency: str = "USDT",
    decimals: int = 2,
    thousands_separator: str = ",",
    decimal_separator: str = "."
) -> str:
    """
    Форматировать сумму в валютный формат.

    Args:
        amount: Сумма для форматирования
        currency: Символ или код валюты (по умолчанию "USDT")
        decimals: Количество знаков после запятой
        thousands_separator: Разделитель тысяч
        decimal_separator: Разделитель десятичных

    Returns:
        Отформатированная строка с валютой

    Example:
        >>> format_currency(1234.56)
        '1,234.56 USDT'
        >>> format_currency(1000, currency="$", decimals=0)
        '$1,000'
    """
    formatted = f"{float(amount):,.{decimals}f}"
    if thousands_separator != ",":
        formatted = formatted.replace(",", "TEMP").replace(".", decimal_separator).replace("TEMP", thousands_separator)
    elif decimal_separator != ".":
        formatted = formatted.replace(".", decimal_separator)

    if currency.startswith("$") or currency.startswith("€"):
        return f"{currency}{formatted}"
    return f"{formatted} {currency}"


def format_percentage(
    value: Union[float, Decimal],
    decimals: int = 2,
    show_sign: bool = False
) -> str:
    """
    Форматировать значение в процентный формат.

    Args:
        value: Значение для форматирования (уже в процентах)
        decimals: Количество знаков после запятой
        show_sign: Показывать ли знак + для положительных значений

    Returns:
        Отформатированная строка с процентами

    Example:
        >>> format_percentage(12.5)
        '12.50%'
        >>> format_percentage(50.0, decimals=0, show_sign=True)
        '+50%'
    """
    sign = ""
    if show_sign and float(value) > 0:
        sign = "+"
    return f"{sign}{float(value):.{decimals}f}%"


def format_number(
    value: Union[float, Decimal, int],
    decimals: Optional[int] = None,
    thousands_separator: str = ",",
    decimal_separator: str = "."
) -> str:
    """
    Форматировать число в читаемый вид.

    Args:
        value: Число для форматирования
        decimals: Количество знаков после запятой (None для автоопределения)
        thousands_separator: Разделитель тысяч
        decimal_separator: Разделитель десятичных

    Returns:
        Отформатированная строка

    Example:
        >>> format_number(1234567.89)
        '1,234,567.89'
        >>> format_number(1000, decimals=0)
        '1,000'
    """
    if decimals is None:
        formatted = f"{float(value):,}"
    else:
        formatted = f"{float(value):,.{decimals}f}"

    if thousands_separator != "," or decimal_separator != ".":
        formatted = formatted.replace(",", "TEMP").replace(".", decimal_separator).replace("TEMP", thousands_separator)

    return formatted


def format_days(days: int) -> str:
    """
    Format days to human-readable string.

    Args:
        days: Number of days

    Returns:
        Formatted string like "447 days (~15 months)"
    """
    if days <= 0:
        return "0 days"

    months = round(days / 30, 1)
    day_str = "1 day" if days == 1 else f"{days} days"

    if months >= 1:
        month_str = f"~{int(months)} months" if months == int(months) else f"~{months} months"
        return f"{day_str} ({month_str})"

    return day_str


def format_days_ru(days: int) -> str:
    """
    Format days to Russian human-readable string.

    Args:
        days: Number of days

    Returns:
        Formatted string like "447 дней (~15 мес.)"
    """
    if days <= 0:
        return "0 дней"

    months = round(days / 30, 1)

    # Russian pluralization for days
    if days % 10 == 1 and days % 100 != 11:
        day_str = f"{days} день"
    elif days % 10 in (2, 3, 4) and days % 100 not in (12, 13, 14):
        day_str = f"{days} дня"
    else:
        day_str = f"{days} дней"

    if months >= 1:
        month_str = f"~{int(months)} мес." if months == int(months) else f"~{months} мес."
        return f"{day_str} ({month_str})"

    return day_str


def format_calculation_result(
    result: "CalculationResult",
    currency: str = "USDT",
) -> str:
    """
    Format calculation result to text report.

    Args:
        result: CalculationResult object
        currency: Currency symbol

    Returns:
        Multi-line formatted report
    """
    from calculator.core.models import CalculationResult

    lines = [
        "Projection:",
        f"  Daily:     {format_currency(result.daily_reward, currency)}",
        f"  Weekly:    {format_currency(result.weekly_reward, currency)}",
        f"  Monthly:   {format_currency(result.monthly_reward, currency)}",
        f"  Yearly:    {format_currency(result.yearly_reward, currency)}",
        "",
        f"ROI Cap: {format_currency(result.roi_cap_amount, currency)}",
        f"Days to cap: {format_days(result.days_to_cap)}",
    ]
    return "\n".join(lines)


def format_calculation_result_ru(
    result: "CalculationResult",
    currency: str = "USDT",
) -> str:
    """
    Format calculation result to Russian text report.

    Args:
        result: CalculationResult object
        currency: Currency symbol

    Returns:
        Multi-line formatted report in Russian
    """
    from calculator.core.models import CalculationResult

    lines = [
        "Прогноз заработка:",
        f"  День:      {format_currency(result.daily_reward, currency)}",
        f"  Неделя:    {format_currency(result.weekly_reward, currency)}",
        f"  Месяц:     {format_currency(result.monthly_reward, currency)}",
        f"  Год:       {format_currency(result.yearly_reward, currency)}",
        "",
        f"ROI Cap: {format_currency(result.roi_cap_amount, currency)}",
        f"Достижение: {format_days_ru(result.days_to_cap)}",
    ]
    return "\n".join(lines)
