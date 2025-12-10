"""
Кнопки для депозитов с коридорами сумм.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class DepositLevelButton:
    """Кнопка уровня депозита."""
    level_type: str
    emoji: str
    name: str
    min_amount: int
    max_amount: int


class DepositButtons:
    """Кнопки для депозитов."""

    # Эмодзи для статусов
    ACTIVE_EMOJI = "✅"
    AVAILABLE_EMOJI = ""
    LOCKED_EMOJI = "🔒"
    PENDING_EMOJI = "⏳"

    # Определения уровней
    LEVELS = {
        "test": DepositLevelButton("test", "🎯", "Тестовый", 30, 100),
        "level_1": DepositLevelButton("level_1", "💰", "Уровень 1", 100, 500),
        "level_2": DepositLevelButton("level_2", "💎", "Уровень 2", 700, 1200),
        "level_3": DepositLevelButton("level_3", "🏆", "Уровень 3", 1400, 2200),
        "level_4": DepositLevelButton("level_4", "👑", "Уровень 4", 2500, 3500),
        "level_5": DepositLevelButton("level_5", "🚀", "Уровень 5", 4000, 7000),
    }

    @classmethod
    def get_button_text(
        cls,
        level_type: str,
        status: str = "available"
    ) -> str:
        """
        Получить текст кнопки для уровня.

        Args:
            level_type: Тип уровня (test, level_1, ...)
            status: Статус (available, active, locked, pending)

        Returns:
            Текст кнопки, например:
            "🎯 Тестовый ($30 - $100)"
            "✅ 🎯 Тестовый ($30 - $100) - Активен"
            "🔒 💰 Уровень 1 ($100 - $500)"
        """
        level = cls.LEVELS.get(level_type)
        if not level:
            return "❓ Неизвестный уровень"

        base_text = f"{level.emoji} {level.name} (${level.min_amount} - ${level.max_amount})"

        if status == "active":
            return f"{cls.ACTIVE_EMOJI} {base_text} - Активен"
        elif status == "pending":
            return f"{cls.PENDING_EMOJI} {base_text} - Ожидает"
        elif status == "locked":
            return f"{cls.LOCKED_EMOJI} {base_text}"
        else:  # available
            return base_text

    @classmethod
    def parse_level_from_button(cls, button_text: str) -> str | None:
        """
        Извлечь level_type из текста кнопки.

        Args:
            button_text: Текст нажатой кнопки

        Returns:
            level_type или None если не распознано
        """
        for level_type, level in cls.LEVELS.items():
            if level.name in button_text:
                return level_type
        return None

    # Навигационные кнопки
    BACK = "◀️ Назад"
    MAIN_MENU = "📊 Главное меню"
    CONFIRM = "✅ Подтвердить"
    CANCEL = "❌ Отмена"
    REFRESH = "🔄 Обновить статус"
