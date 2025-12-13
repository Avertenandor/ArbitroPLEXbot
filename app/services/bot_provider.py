"""Provider для получения экземпляра бота без циклических зависимостей."""
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from aiogram import Bot

_bot_getter: Callable[[], "Bot | None"] | None = None


def set_bot_getter(getter: Callable[[], "Bot | None"]) -> None:
    """Устанавливает функцию получения бота. Вызывается при инициализации бота."""
    global _bot_getter
    _bot_getter = getter


def get_bot() -> "Bot | None":
    """Получает экземпляр бота."""
    if _bot_getter is None:
        return None
    return _bot_getter()
