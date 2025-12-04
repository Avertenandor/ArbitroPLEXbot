"""
Inquiry FSM States.

States for user inquiry flow (asking questions to admins).
"""

from aiogram.fsm.state import State, StatesGroup


class InquiryStates(StatesGroup):
    """States for user inquiry flow."""

    # User is writing their question
    writing_question = State()

    # User is in active dialog with admin
    in_dialog = State()


class AdminInquiryStates(StatesGroup):
    """States for admin inquiry handling."""

    # Admin is viewing inquiry list
    viewing_list = State()

    # Admin is viewing specific inquiry
    viewing_inquiry = State()

    # Admin is writing response to user
    writing_response = State()
