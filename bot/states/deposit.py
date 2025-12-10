"""
Deposit FSM states.

States for deposit creation flow.
"""

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    """FSM состояния для процесса создания депозита."""

    # DEPRECATED/RESERVED - not currently used
    # Выбор уровня
    selecting_level = State()

    # Ввод суммы в коридоре
    entering_amount = State()

    # DEPRECATED/RESERVED - not currently used
    # Подтверждение параметров
    confirming_params = State()

    # DEPRECATED/RESERVED - not currently used
    # Ожидание USDT транзакции
    waiting_for_usdt = State()

    # Ввод хеша USDT транзакции
    waiting_for_tx_hash = State()

    # DEPRECATED/RESERVED - not currently used
    # Ожидание первого PLEX платежа
    waiting_for_plex = State()

    # DEPRECATED/RESERVED - not currently used
    # Ввод хеша PLEX транзакции
    waiting_for_plex_tx = State()


@dataclass
class DepositStateData:
    """Структура данных в FSM state."""

    level_type: str = ""           # test, level_1, ...
    level_name: str = ""           # Тестовый, Уровень 1, ...
    min_amount: Decimal = Decimal("0")      # Минимум коридора
    max_amount: Decimal = Decimal("0")      # Максимум коридора
    amount: Decimal = Decimal("0")          # Выбранная сумма
    plex_daily: Decimal = Decimal("0")      # Ежедневный PLEX
    deposit_id: int | None = None           # ID созданного депозита
    usdt_tx_hash: str | None = None         # Хеш USDT транзакции
    plex_tx_hash: str | None = None         # Хеш PLEX транзакции


# Вспомогательные функции для работы с данными состояния


async def get_deposit_state_data(state: FSMContext) -> DepositStateData:
    """
    Получить данные депозита из состояния FSM.

    Args:
        state: Контекст FSM

    Returns:
        DepositStateData: Данные состояния депозита
    """
    data = await state.get_data()

    return DepositStateData(
        level_type=data.get("level_type", ""),
        level_name=data.get("level_name", ""),
        min_amount=_to_decimal(data.get("min_amount", "0")),
        max_amount=_to_decimal(data.get("max_amount", "0")),
        amount=_to_decimal(data.get("amount", "0")),
        plex_daily=_to_decimal(data.get("plex_daily", "0")),
        deposit_id=data.get("deposit_id"),
        usdt_tx_hash=data.get("usdt_tx_hash"),
        plex_tx_hash=data.get("plex_tx_hash"),
    )


async def set_deposit_state_data(
    state: FSMContext,
    data: DepositStateData
) -> None:
    """
    Сохранить данные депозита в состояние FSM.

    Args:
        state: Контекст FSM
        data: Данные депозита для сохранения
    """
    state_dict = _to_serializable_dict(data)
    await state.update_data(**state_dict)


async def update_deposit_state_data(
    state: FSMContext,
    **kwargs: Any
) -> None:
    """
    Обновить отдельные поля в данных состояния депозита.

    Args:
        state: Контекст FSM
        **kwargs: Поля для обновления (level_type, amount, deposit_id и т.д.)
    """
    # Конвертируем Decimal в строки для сериализации
    serializable_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, Decimal):
            serializable_kwargs[key] = str(value)
        else:
            serializable_kwargs[key] = value

    await state.update_data(**serializable_kwargs)


async def clear_deposit_state(state: FSMContext) -> None:
    """
    Очистить состояние депозита.

    Args:
        state: Контекст FSM
    """
    await state.clear()


# Внутренние вспомогательные функции


def _to_decimal(value: Any) -> Decimal:
    """
    Конвертировать значение в Decimal.

    Args:
        value: Значение для конвертации

    Returns:
        Decimal: Сконвертированное значение
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except Exception:
            return Decimal("0")
    return Decimal("0")


def _to_serializable_dict(data: DepositStateData) -> dict[str, Any]:
    """
    Конвертировать DepositStateData в сериализуемый словарь.

    Decimal конвертируется в строки для хранения в FSM.

    Args:
        data: Данные депозита

    Returns:
        dict: Сериализуемый словарь
    """
    result = asdict(data)

    # Конвертируем Decimal в строки
    for key, value in result.items():
        if isinstance(value, Decimal):
            result[key] = str(value)

    return result
