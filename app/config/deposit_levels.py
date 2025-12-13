"""
Единственный источник истины для конфигурации уровней депозитов.

Этот модуль содержит все константы и конфигурации для уровней депозитов.
Все другие модули должны импортировать из этого файла.
"""

from decimal import Decimal
from enum import Enum
from typing import NamedTuple


class DepositLevelType(str, Enum):
    """Типы уровней депозитов."""

    TEST = "test"
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"
    LEVEL_5 = "level_5"


class DepositLevelConfig(NamedTuple):
    """Конфигурация уровня депозита."""

    level_type: DepositLevelType
    level_number: int  # Номер уровня (0 для test, 1-5 для levels)
    min_amount: Decimal  # Минимальная сумма депозита
    max_amount: Decimal  # Максимальная сумма депозита
    display_name: str  # Отображаемое имя
    order: int  # Порядковый номер для сортировки
    roi_percent: Decimal  # ROI процент (дневной)
    roi_cap_percent: int  # ROI cap в процентах (обычно 500%)
    plex_per_dollar: int  # PLEX за $1 в сутки (обычно 10)
    plex_required: int  # Требуемый PLEX баланс для доступа к уровню
    rabbits_required: int  # Требуемое количество рефералов


# Конфигурация уровней депозитов (значения из app/config/business_constants.py)
DEPOSIT_LEVELS: dict[DepositLevelType, DepositLevelConfig] = {
    DepositLevelType.TEST: DepositLevelConfig(
        level_type=DepositLevelType.TEST,
        level_number=0,
        min_amount=Decimal("30"),
        max_amount=Decimal("100"),
        display_name="Тестовый",
        order=0,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=0,  # Для тестового уровня не требуется PLEX
        rabbits_required=0,
    ),
    DepositLevelType.LEVEL_1: DepositLevelConfig(
        level_type=DepositLevelType.LEVEL_1,
        level_number=1,
        min_amount=Decimal("100"),
        max_amount=Decimal("500"),
        display_name="Уровень 1",
        order=1,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=5000,
        rabbits_required=1,
    ),
    DepositLevelType.LEVEL_2: DepositLevelConfig(
        level_type=DepositLevelType.LEVEL_2,
        level_number=2,
        min_amount=Decimal("700"),
        max_amount=Decimal("1200"),
        display_name="Уровень 2",
        order=2,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=10000,
        rabbits_required=3,
    ),
    DepositLevelType.LEVEL_3: DepositLevelConfig(
        level_type=DepositLevelType.LEVEL_3,
        level_number=3,
        min_amount=Decimal("1400"),
        max_amount=Decimal("2200"),
        display_name="Уровень 3",
        order=3,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=15000,
        rabbits_required=5,
    ),
    DepositLevelType.LEVEL_4: DepositLevelConfig(
        level_type=DepositLevelType.LEVEL_4,
        level_number=4,
        min_amount=Decimal("2500"),
        max_amount=Decimal("3500"),
        display_name="Уровень 4",
        order=4,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=20000,
        rabbits_required=10,
    ),
    DepositLevelType.LEVEL_5: DepositLevelConfig(
        level_type=DepositLevelType.LEVEL_5,
        level_number=5,
        min_amount=Decimal("4000"),
        max_amount=Decimal("7000"),
        display_name="Уровень 5",
        order=5,
        roi_percent=Decimal("2.0"),  # 2% дневной ROI
        roi_cap_percent=500,  # 500% cap
        plex_per_dollar=10,
        plex_required=25000,
        rabbits_required=15,
    ),
}


# Порядок уровней для последовательной валидации
DEPOSIT_LEVEL_ORDER = [
    DepositLevelType.TEST,
    DepositLevelType.LEVEL_1,
    DepositLevelType.LEVEL_2,
    DepositLevelType.LEVEL_3,
    DepositLevelType.LEVEL_4,
    DepositLevelType.LEVEL_5,
]


# Legacy словарь для обратной совместимости (level_number -> min_amount)
DEPOSIT_LEVELS_LEGACY = {config.level_number: config.min_amount for config in DEPOSIT_LEVELS.values()}


def get_level_config(level_type: str | DepositLevelType) -> DepositLevelConfig | None:
    """
    Получить конфигурацию уровня по типу.

    Args:
        level_type: Тип уровня (строка или enum)

    Returns:
        Конфигурация уровня или None если не найдено
    """
    if isinstance(level_type, str):
        try:
            level_type = DepositLevelType(level_type)
        except ValueError:
            return None
    return DEPOSIT_LEVELS.get(level_type)


def get_level_config_by_number(level_number: int) -> DepositLevelConfig | None:
    """
    Получить конфигурацию уровня по номеру.

    Args:
        level_number: Номер уровня (0 для test, 1-5 для levels)

    Returns:
        Конфигурация уровня или None если не найдено
    """
    for config in DEPOSIT_LEVELS.values():
        if config.level_number == level_number:
            return config
    return None


def get_level_by_order(order: int) -> DepositLevelConfig | None:
    """
    Получить уровень по порядковому номеру.

    Args:
        order: Порядковый номер (0-5)

    Returns:
        Конфигурация уровня или None если не найдено
    """
    for config in DEPOSIT_LEVELS.values():
        if config.order == order:
            return config
    return None


def get_previous_level(level_type: str | DepositLevelType) -> DepositLevelConfig | None:
    """
    Получить предыдущий уровень в последовательности.

    Args:
        level_type: Текущий тип уровня

    Returns:
        Предыдущий уровень или None если это первый уровень
    """
    config = get_level_config(level_type)
    if not config or config.order == 0:
        return None
    return get_level_by_order(config.order - 1)


def get_next_level(level_type: str | DepositLevelType) -> DepositLevelConfig | None:
    """
    Получить следующий уровень в последовательности.

    Args:
        level_type: Текущий тип уровня

    Returns:
        Следующий уровень или None если это последний уровень
    """
    config = get_level_config(level_type)
    if not config:
        return None

    max_order = max(c.order for c in DEPOSIT_LEVELS.values())
    if config.order >= max_order:
        return None

    return get_level_by_order(config.order + 1)


def is_amount_in_corridor(level_type: str | DepositLevelType, amount: Decimal) -> bool:
    """
    Проверить, находится ли сумма в коридоре уровня.

    Args:
        level_type: Тип уровня
        amount: Сумма для проверки

    Returns:
        True если сумма в пределах min/max для уровня
    """
    config = get_level_config(level_type)
    if not config:
        return False

    return config.min_amount <= amount <= config.max_amount


def get_level_for_amount(amount: Decimal) -> DepositLevelConfig | None:
    """
    Найти подходящий уровень для суммы депозита.

    Args:
        amount: Сумма депозита

    Returns:
        Конфигурация подходящего уровня или None
    """
    for config in DEPOSIT_LEVELS.values():
        if config.min_amount <= amount <= config.max_amount:
            return config
    return None


def level_type_to_db_level(level_type: str | DepositLevelType) -> int | None:
    """
    Преобразовать тип уровня в номер уровня БД.

    Args:
        level_type: Тип уровня

    Returns:
        Номер уровня или None если не найдено
    """
    config = get_level_config(level_type)
    return config.level_number if config else None


def db_level_to_level_type(db_level: int) -> DepositLevelType | None:
    """
    Преобразовать номер уровня БД в тип уровня.

    Args:
        db_level: Номер уровня в БД (0 для test, 1-5 для levels)

    Returns:
        Тип уровня или None если не найдено
    """
    config = get_level_config_by_number(db_level)
    return config.level_type if config else None


def calculate_daily_plex_payment(
    deposit_amount_usd: Decimal, level_type: str | DepositLevelType | None = None
) -> Decimal:
    """
    Рассчитать ежедневный платеж в PLEX для депозита.

    Args:
        deposit_amount_usd: Сумма депозита в USD
        level_type: Тип уровня (опционально, по умолчанию 10 PLEX/$)

    Returns:
        Требуемый платеж PLEX в день
    """
    plex_per_dollar = 10  # По умолчанию

    if level_type:
        config = get_level_config(level_type)
        if config:
            plex_per_dollar = config.plex_per_dollar

    return Decimal(str(deposit_amount_usd)) * Decimal(str(plex_per_dollar))


def get_next_level_type(current_level_type: str | DepositLevelType) -> str | None:
    """
    Получить тип следующего уровня.

    Args:
        current_level_type: Текущий тип уровня

    Returns:
        Строка типа следующего уровня или None если это последний уровень
    """
    next_level = get_next_level(current_level_type)
    return next_level.level_type.value if next_level else None


def get_previous_level_type(current_level_type: str | DepositLevelType) -> str | None:
    """
    Получить тип предыдущего уровня.

    Args:
        current_level_type: Текущий тип уровня

    Returns:
        Строка типа предыдущего уровня или None если это первый уровень
    """
    prev_level = get_previous_level(current_level_type)
    return prev_level.level_type.value if prev_level else None
