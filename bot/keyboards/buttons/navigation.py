"""Navigation and pagination button constants."""


class NavigationButtons:
    """Navigation buttons used across the bot."""

    # Back buttons (different variants)
    BACK = "◀️ Назад"
    BACK_ARROW = "⬅ Назад"
    BACK_TO_WITHDRAWALS = "◀️ Назад к выводам"
    BACK_TO_ADMIN = "◀️ Назад в админ-панель"
    BACK_TO_LIST = "◀️ Назад к списку"
    BACK_TO_LEVELS = "◀️ Назад к уровням"
    BACK_TO_USERS = "◀️ К списку пользователей"
    BACK_TO_DEPOSIT_MGMT = "◀️ Назад в управление депозитами"
    BACK_TO_CARD = "◀️ К карточке"

    # Main menu buttons (different variants)
    MAIN_MENU = "📊 Главное меню"
    HOME = "🏠 Главное меню"
    TO_MAIN_MENU = "◀️ Главное меню"

    # Cancel buttons
    CANCEL = "❌ Отмена"
    CANCEL_ARROW = "◀️ Отмена"


class PaginationButtons:
    """Pagination buttons (various formats)."""

    # Short format
    PREV_SHORT = "⬅️ Пред."
    NEXT_SHORT = "След. ➡️"

    # Medium format
    PREV_MEDIUM = "⬅️ Предыдущая"
    NEXT_MEDIUM = "Следующая ➡"

    # Long format
    PREV_PAGE = "⬅ Предыдущая страница"
    NEXT_PAGE = "➡ Следующая страница"

    # Specific contexts
    PREV_WITHDRAWAL_PAGE = "⬅ Предыдущая страница выводов"
    NEXT_WITHDRAWAL_PAGE = "➡ Следующая страница выводов"
    PREV_WITHDRAWAL_PAGE_ARROW = "⬅️ Предыдущая страница"
    NEXT_WITHDRAWAL_PAGE_ARROW = "➡️ Следующая страница"
    PREV_ADMIN_WITHDRAWAL = "⬅️ Пред. страница выводов"
    NEXT_ADMIN_WITHDRAWAL = "Вперёд страница выводов ➡️"
