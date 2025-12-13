"""
Wallet viewing states.

Defines FSM states for wallet navigation.
"""

from aiogram.fsm.state import State, StatesGroup


class WalletStates(StatesGroup):
    """Wallet viewing states."""

    viewing_balances = State()
    viewing_bnb_txs = State()
    viewing_usdt_txs = State()
    viewing_plex_txs = State()
