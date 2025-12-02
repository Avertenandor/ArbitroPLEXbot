"""
Support FSM states.

States for support ticket flow.
"""

from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    """Support ticket flow states."""

    waiting_for_category = State()
    waiting_for_message = State()
    waiting_for_attachment = State()
    in_conversation = State()
