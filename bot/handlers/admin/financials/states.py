"""
Financial reporting states.

Defines FSM states for the financial reporting section.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminFinancialStates(StatesGroup):
    """States for financial reporting section."""
    viewing_list = State()
    viewing_user = State()
    viewing_withdrawals = State()
    viewing_user_detail = State()  # Детальная карточка пользователя
    viewing_deposits_list = State()  # Полный список депозитов
    viewing_withdrawals_list = State()  # Полный список выводов
    viewing_wallet_history = State()  # История смены кошельков
