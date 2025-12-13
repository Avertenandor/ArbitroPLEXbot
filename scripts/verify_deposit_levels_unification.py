"""
Скрипт для проверки унификации конфигурации уровней депозитов.

Проверяет, что все три источника теперь используют одинаковые значения
из единого источника истины: app.config.deposit_levels
"""

from decimal import Decimal

from app.config.deposit_levels import DEPOSIT_LEVELS, DepositLevelType
from app.config.business_constants import DEPOSIT_LEVELS as BUSINESS_LEVELS
from app.services.deposit.constants import DEPOSIT_LEVEL_CONFIGS
from calculator.constants import DEFAULT_LEVELS


def verify_unification():
    """Проверить унификацию конфигурации."""
    print("=" * 80)
    print("ПРОВЕРКА УНИФИКАЦИИ КОНФИГУРАЦИИ УРОВНЕЙ ДЕПОЗИТОВ")
    print("=" * 80)
    print()

    # 1. Проверяем единый источник истины
    print("1. Единый источник истины (app.config.deposit_levels):")
    print("-" * 80)
    for level_type, config in DEPOSIT_LEVELS.items():
        print(f"  {level_type.value:10} | "
              f"№{config.level_number} | "
              f"${config.min_amount:>6} - ${config.max_amount:>6} | "
              f"ROI: {config.roi_percent}% | "
              f"PLEX: {config.plex_required} | "
              f"Rabbits: {config.rabbits_required}")
    print()

    # 2. Проверяем business_constants
    print("2. Business Constants (app.config.business_constants):")
    print("-" * 80)
    for level_type, level_data in BUSINESS_LEVELS.items():
        print(f"  {level_type:10} | "
              f"${level_data['min']:>6} - ${level_data['max']:>6} | "
              f"Order: {level_data['order']} | "
              f"Name: {level_data['name']}")
    print()

    # 3. Проверяем deposit/constants
    print("3. Deposit Constants (app.services.deposit.constants):")
    print("-" * 80)
    for level_type, config in DEPOSIT_LEVEL_CONFIGS.items():
        print(f"  {level_type:10} | "
              f"DB Level: {config.db_level} | "
              f"${config.min_amount:>6} - ${config.max_amount:>6} | "
              f"Name: {config.display_name}")
    print()

    # 4. Проверяем calculator/constants
    print("4. Calculator Constants (calculator.constants):")
    print("-" * 80)
    for level in DEFAULT_LEVELS:
        print(f"  Level {level.level_number} | "
              f"${level.min_amount:>6}+ | "
              f"ROI: {level.roi_percent}% | "
              f"Cap: {level.roi_cap_percent}% | "
              f"Name: {level.name}")
    print()

    # 5. Проверяем совпадение значений
    print("5. Проверка совпадения значений:")
    print("-" * 80)
    errors = []

    for level_type, config in DEPOSIT_LEVELS.items():
        level_str = level_type.value

        # Проверяем business_constants
        if level_str in BUSINESS_LEVELS:
            bus_level = BUSINESS_LEVELS[level_str]
            if int(config.min_amount) != bus_level["min"]:
                errors.append(
                    f"  ❌ {level_str}: min_amount не совпадает "
                    f"(источник: {config.min_amount}, business: {bus_level['min']})"
                )
            if int(config.max_amount) != bus_level["max"]:
                errors.append(
                    f"  ❌ {level_str}: max_amount не совпадает "
                    f"(источник: {config.max_amount}, business: {bus_level['max']})"
                )

        # Проверяем deposit/constants
        if level_str in DEPOSIT_LEVEL_CONFIGS:
            dep_config = DEPOSIT_LEVEL_CONFIGS[level_str]
            if config.min_amount != dep_config.min_amount:
                errors.append(
                    f"  ❌ {level_str}: min_amount не совпадает "
                    f"(источник: {config.min_amount}, deposit: {dep_config.min_amount})"
                )
            if config.max_amount != dep_config.max_amount:
                errors.append(
                    f"  ❌ {level_str}: max_amount не совпадает "
                    f"(источник: {config.max_amount}, deposit: {dep_config.max_amount})"
                )

        # Проверяем calculator/constants (только для уровней 1-5)
        if config.level_number > 0:
            calc_level = next(
                (l for l in DEFAULT_LEVELS if l.level_number == config.level_number),
                None
            )
            if calc_level:
                if config.min_amount != calc_level.min_amount:
                    errors.append(
                        f"  ❌ Level {config.level_number}: min_amount не совпадает "
                        f"(источник: {config.min_amount}, calculator: {calc_level.min_amount})"
                    )
                if config.roi_percent != calc_level.roi_percent:
                    errors.append(
                        f"  ⚠️  Level {config.level_number}: roi_percent не совпадает "
                        f"(источник: {config.roi_percent}, calculator: {calc_level.roi_percent})"
                    )

    if errors:
        print("  Найдены расхождения:")
        for error in errors:
            print(error)
    else:
        print("  ✅ Все значения совпадают!")

    print()
    print("=" * 80)
    print("ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 80)

    return len(errors) == 0


if __name__ == "__main__":
    success = verify_unification()
    exit(0 if success else 1)
