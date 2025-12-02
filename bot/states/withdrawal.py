"""
Withdrawal FSM states.

States for withdrawal request flow.
"""

from aiogram.fsm.state import State, StatesGroup


class WithdrawalStates(StatesGroup):
    """Withdrawal flow states."""

    waiting_for_amount = State()
    waiting_for_financial_password = State()
    waiting_for_confirmation = State()
