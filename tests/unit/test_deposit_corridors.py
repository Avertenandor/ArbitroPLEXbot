"""
Тесты для новой системы депозитов с коридорами.

Проверяет:
- Конфигурацию уровней с min/max коридорами
- Валидацию суммы в пределах коридора
- Последовательность уровней (test -> level_1 -> ... -> level_5)
- Расчет PLEX за депозит
"""
import pytest
from decimal import Decimal
from bot.constants.rules import (
    DEPOSIT_LEVELS,
    DEPOSIT_LEVEL_ORDER,
    PLEX_PER_DOLLAR_DAILY,
)


class TestDepositLevels:
    """Тесты конфигурации уровней."""

    def test_all_levels_defined(self):
        """Все 6 уровней определены."""
        assert "test" in DEPOSIT_LEVELS
        assert "level_1" in DEPOSIT_LEVELS
        assert "level_2" in DEPOSIT_LEVELS
        assert "level_3" in DEPOSIT_LEVELS
        assert "level_4" in DEPOSIT_LEVELS
        assert "level_5" in DEPOSIT_LEVELS

    def test_test_level_corridor(self):
        """Тестовый уровень: $30-$100."""
        level = DEPOSIT_LEVELS["test"]
        assert level["min"] == 30
        assert level["max"] == 100

    def test_level_1_corridor(self):
        """Уровень 1: $100-$500."""
        level = DEPOSIT_LEVELS["level_1"]
        assert level["min"] == 100
        assert level["max"] == 500

    def test_level_2_corridor(self):
        """Уровень 2: $700-$1200."""
        level = DEPOSIT_LEVELS["level_2"]
        assert level["min"] == 700
        assert level["max"] == 1200

    def test_level_3_corridor(self):
        """Уровень 3: $1400-$2200."""
        level = DEPOSIT_LEVELS["level_3"]
        assert level["min"] == 1400
        assert level["max"] == 2200

    def test_level_4_corridor(self):
        """Уровень 4: $2500-$3500."""
        level = DEPOSIT_LEVELS["level_4"]
        assert level["min"] == 2500
        assert level["max"] == 3500

    def test_level_5_corridor(self):
        """Уровень 5: $4000-$7000."""
        level = DEPOSIT_LEVELS["level_5"]
        assert level["min"] == 4000
        assert level["max"] == 7000

    def test_all_levels_have_required_fields(self):
        """Все уровни имеют обязательные поля."""
        for level_key, level_data in DEPOSIT_LEVELS.items():
            assert "min" in level_data, f"Level {level_key} missing 'min'"
            assert "max" in level_data, f"Level {level_key} missing 'max'"
            assert "name" in level_data, f"Level {level_key} missing 'name'"
            assert "order" in level_data, f"Level {level_key} missing 'order'"

    def test_corridor_min_less_than_max(self):
        """Минимум всегда меньше максимума в коридоре."""
        for level_key, level_data in DEPOSIT_LEVELS.items():
            assert level_data["min"] < level_data["max"], (
                f"Level {level_key}: min ({level_data['min']}) "
                f"should be less than max ({level_data['max']})"
            )

    def test_levels_are_positive(self):
        """Все границы коридоров положительные."""
        for level_key, level_data in DEPOSIT_LEVELS.items():
            assert level_data["min"] > 0, f"Level {level_key} min must be positive"
            assert level_data["max"] > 0, f"Level {level_key} max must be positive"


class TestAmountValidation:
    """Тесты валидации суммы в коридоре."""

    def validate_amount_in_corridor(self, level_key: str, amount: Decimal) -> tuple[bool, str | None]:
        """
        Вспомогательная функция валидации суммы в коридоре.

        Args:
            level_key: Ключ уровня (например, "test", "level_1")
            amount: Сумма для проверки

        Returns:
            Tuple (is_valid, error_message)
        """
        if level_key not in DEPOSIT_LEVELS:
            return False, f"Неверный уровень: {level_key}"

        level = DEPOSIT_LEVELS[level_key]
        min_amount = Decimal(str(level["min"]))
        max_amount = Decimal(str(level["max"]))

        if amount < min_amount:
            return False, f"Сумма ниже минимума ({min_amount} USDT)"

        if amount > max_amount:
            return False, f"Сумма выше максимума ({max_amount} USDT)"

        return True, None

    def test_amount_in_corridor_valid_test_level(self):
        """Сумма в пределах коридора тестового уровня - валидна."""
        is_valid, error = self.validate_amount_in_corridor("test", Decimal("50"))
        assert is_valid is True
        assert error is None

    def test_amount_in_corridor_valid_level_1(self):
        """Сумма в пределах коридора уровня 1 - валидна."""
        is_valid, error = self.validate_amount_in_corridor("level_1", Decimal("300"))
        assert is_valid is True
        assert error is None

    def test_amount_below_min_invalid(self):
        """Сумма ниже минимума - невалидна."""
        is_valid, error = self.validate_amount_in_corridor("test", Decimal("20"))
        assert is_valid is False
        assert "минимум" in error.lower()

    def test_amount_above_max_invalid(self):
        """Сумма выше максимума - невалидна."""
        is_valid, error = self.validate_amount_in_corridor("test", Decimal("150"))
        assert is_valid is False
        assert "максимум" in error.lower()

    def test_amount_at_min_boundary(self):
        """Сумма на нижней границе - валидна."""
        is_valid, _ = self.validate_amount_in_corridor("level_1", Decimal("100"))
        assert is_valid is True

    def test_amount_at_max_boundary(self):
        """Сумма на верхней границе - валидна."""
        is_valid, _ = self.validate_amount_in_corridor("level_1", Decimal("500"))
        assert is_valid is True

    def test_invalid_level_key(self):
        """Неверный ключ уровня - невалидно."""
        is_valid, error = self.validate_amount_in_corridor("level_99", Decimal("100"))
        assert is_valid is False
        assert "неверный уровень" in error.lower()


class TestSequenceValidation:
    """Тесты валидации последовательности уровней."""

    def get_previous_level(self, level_key: str) -> str | None:
        """
        Получить предыдущий уровень в последовательности.

        Args:
            level_key: Текущий уровень

        Returns:
            Предыдущий уровень или None
        """
        try:
            index = DEPOSIT_LEVEL_ORDER.index(level_key)
            if index > 0:
                return DEPOSIT_LEVEL_ORDER[index - 1]
        except ValueError:
            pass
        return None

    def get_next_level(self, level_key: str) -> str | None:
        """
        Получить следующий уровень в последовательности.

        Args:
            level_key: Текущий уровень

        Returns:
            Следующий уровень или None
        """
        try:
            index = DEPOSIT_LEVEL_ORDER.index(level_key)
            if index < len(DEPOSIT_LEVEL_ORDER) - 1:
                return DEPOSIT_LEVEL_ORDER[index + 1]
        except ValueError:
            pass
        return None

    def test_test_has_no_previous(self):
        """Тестовый уровень не имеет предыдущего."""
        assert self.get_previous_level("test") is None

    def test_level_1_previous_is_test(self):
        """Предыдущий для level_1 - test."""
        assert self.get_previous_level("level_1") == "test"

    def test_level_5_previous_is_level_4(self):
        """Предыдущий для level_5 - level_4."""
        assert self.get_previous_level("level_5") == "level_4"

    def test_test_next_is_level_1(self):
        """Следующий после test - level_1."""
        assert self.get_next_level("test") == "level_1"

    def test_level_4_next_is_level_5(self):
        """Следующий после level_4 - level_5."""
        assert self.get_next_level("level_4") == "level_5"

    def test_level_5_has_no_next(self):
        """Level_5 не имеет следующего."""
        assert self.get_next_level("level_5") is None

    def test_deposit_level_order_complete(self):
        """DEPOSIT_LEVEL_ORDER содержит все уровни."""
        assert len(DEPOSIT_LEVEL_ORDER) == 6
        assert DEPOSIT_LEVEL_ORDER == ["test", "level_1", "level_2", "level_3", "level_4", "level_5"]


class TestPlexCalculation:
    """Тесты расчёта PLEX."""

    def test_plex_per_dollar_constant(self):
        """10 PLEX за $1 в день."""
        assert PLEX_PER_DOLLAR_DAILY == 10

    def calculate_daily_plex(self, amount: Decimal) -> Decimal:
        """
        Рассчитать ежедневный PLEX для суммы депозита.

        Args:
            amount: Сумма депозита в USDT

        Returns:
            Ежедневная сумма PLEX
        """
        return amount * Decimal(str(PLEX_PER_DOLLAR_DAILY))

    def test_calculate_daily_plex_350(self):
        """Расчёт ежедневного PLEX для $350."""
        amount = Decimal("350")
        expected_plex = Decimal("3500")  # 350 * 10
        actual = self.calculate_daily_plex(amount)
        assert actual == expected_plex

    def test_calculate_daily_plex_decimal_precision(self):
        """Расчёт PLEX сохраняет точность для дробных сумм."""
        amount = Decimal("123.45")
        expected_plex = Decimal("1234.5")  # 123.45 * 10
        actual = self.calculate_daily_plex(amount)
        assert actual == expected_plex

    def test_plex_calculation_for_all_level_minimums(self):
        """PLEX рассчитывается корректно для минимальных сумм всех уровней."""
        for level_key, level_data in DEPOSIT_LEVELS.items():
            min_amount = Decimal(str(level_data["min"]))
            plex = self.calculate_daily_plex(min_amount)
            expected = min_amount * Decimal("10")
            assert plex == expected, f"Level {level_key}: {plex} != {expected}"

    def test_plex_calculation_for_all_level_maximums(self):
        """PLEX рассчитывается корректно для максимальных сумм всех уровней."""
        for level_key, level_data in DEPOSIT_LEVELS.items():
            max_amount = Decimal(str(level_data["max"]))
            plex = self.calculate_daily_plex(max_amount)
            expected = max_amount * Decimal("10")
            assert plex == expected, f"Level {level_key}: {plex} != {expected}"
