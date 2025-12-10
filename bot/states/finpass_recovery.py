"""
Financial Password Recovery States.

FSM states for financial password recovery flow.
"""

from aiogram.fsm.state import State, StatesGroup


class FinpassRecoveryStates(StatesGroup):
    """States for financial password recovery."""

    # Step 1: Choose recovery type (password only OR password + wallet)
    choosing_recovery_type = State()
    # Step 2a: If wallet change - enter new wallet address
    waiting_for_new_wallet = State()
    # Step 2b: Enter reason for recovery
    waiting_for_reason = State()
    # Step 3: Confirm and submit
    waiting_for_confirmation = State()
