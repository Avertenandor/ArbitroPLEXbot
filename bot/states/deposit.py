"""
Deposit FSM states.

States for deposit creation flow.
"""

from aiogram.fsm.state import State, StatesGroup


class DepositStates(StatesGroup):
    """Deposit flow states."""

    waiting_for_level = State()
    waiting_for_amount = State()
    waiting_for_confirmation = State()
    waiting_for_tx_hash = State()
