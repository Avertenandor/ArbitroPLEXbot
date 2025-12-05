"""
FSM States for Wallet Setup.

Defines all states used in the wallet setup flow.
"""

from aiogram.fsm.state import State, StatesGroup


class WalletSetupStates(StatesGroup):
    """States for wallet setup."""

    setting_input_wallet = State()
    setting_output_key = State()
    setting_derivation_index = State()  # New state for HD Wallet index
    waiting_for_seed = State()
    confirming_input = State()
    confirming_output = State()
