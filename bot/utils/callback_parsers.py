"""
Утилиты для безопасного парсинга callback данных.

Этот модуль содержит функции для безопасного извлечения данных
из callback_data Telegram ботов с валидацией.
"""


def parse_callback_id(callback_data: str, prefix: str) -> int | None:
    """
    Безопасно извлечь ID из callback данных с префиксом.

    Args:
        callback_data: Строка callback данных (например, "show_password_12345")
        prefix: Ожидаемый префикс (например, "show_password_")

    Returns:
        int | None: Извлечённый ID или None при ошибке

    Examples:
        >>> parse_callback_id("show_password_123", "show_password_")
        123
        >>> parse_callback_id("show_password_abc", "show_password_")
        None
        >>> parse_callback_id("wrong_prefix_123", "show_password_")
        None
    """
    if not callback_data or not isinstance(callback_data, str):
        return None

    if not callback_data.startswith(prefix):
        return None

    id_str = callback_data[len(prefix):]

    if not id_str:
        return None

    if not id_str.isdigit():
        return None

    try:
        return int(id_str)
    except (ValueError, OverflowError):
        return None


def parse_callback_split_id(
    callback_data: str,
    delimiter: str,
    position: int
) -> int | None:
    """
    Безопасно извлечь ID из callback данных с разделителем.

    Args:
        callback_data: Строка callback данных (например, "cancel_withdrawal_123")
        delimiter: Разделитель (например, "_")
        position: Позиция ID после split (например, 2 для "cancel_withdrawal_123")

    Returns:
        int | None: Извлечённый ID или None при ошибке

    Examples:
        >>> parse_callback_split_id("cancel_withdrawal_123", "_", 2)
        123
        >>> parse_callback_split_id("cancel_withdrawal_abc", "_", 2)
        None
        >>> parse_callback_split_id("short", "_", 2)
        None
    """
    if not callback_data or not isinstance(callback_data, str):
        return None

    try:
        parts = callback_data.split(delimiter)
        if len(parts) <= position:
            return None

        id_str = parts[position]
        if not id_str.isdigit():
            return None

        return int(id_str)
    except (ValueError, OverflowError, IndexError):
        return None


def parse_callback_colon_value(
    callback_data: str,
    prefix: str
) -> str | None:
    """
    Безопасно извлечь значение из callback данных с префиксом и двоеточием.

    Args:
        callback_data: Строка callback данных (например, "si_sponsor_view:123")
        prefix: Ожидаемый префикс с двоеточием (например, "si_sponsor_view:")

    Returns:
        str | None: Извлечённое значение или None при ошибке

    Examples:
        >>> parse_callback_colon_value("si_sponsor_view:123", "si_sponsor_view:")
        "123"
        >>> parse_callback_colon_value("wrong:123", "si_sponsor_view:")
        None
    """
    if not callback_data or not isinstance(callback_data, str):
        return None

    if not callback_data.startswith(prefix):
        return None

    value = callback_data[len(prefix):]

    if not value:
        return None

    return value


def parse_callback_colon_id(
    callback_data: str,
    prefix: str
) -> int | None:
    """
    Безопасно извлечь числовой ID из callback данных с префиксом и двоеточием.

    Args:
        callback_data: Строка callback данных (например, "si_sponsor_view:123")
        prefix: Ожидаемый префикс с двоеточием (например, "si_sponsor_view:")

    Returns:
        int | None: Извлечённый ID или None при ошибке

    Examples:
        >>> parse_callback_colon_id("si_sponsor_view:123", "si_sponsor_view:")
        123
        >>> parse_callback_colon_id("si_sponsor_view:abc", "si_sponsor_view:")
        None
    """
    value = parse_callback_colon_value(callback_data, prefix)

    if value is None:
        return None

    if not value.isdigit():
        return None

    try:
        return int(value)
    except (ValueError, OverflowError):
        return None
