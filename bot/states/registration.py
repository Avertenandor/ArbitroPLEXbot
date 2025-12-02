"""
Registration FSM states.

States for user registration flow.
"""

from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    """Registration flow states."""

    waiting_for_wallet = State()
    waiting_for_financial_password = State()
    waiting_for_password_confirmation = State()
    waiting_for_referrer = State()
    waiting_for_contacts_choice = State()
    waiting_for_phone = State()
    waiting_for_email = State()
