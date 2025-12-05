"""
Sponsor Inquiry FSM States.

States for referral-to-sponsor communication flow.
"""

from aiogram.fsm.state import State, StatesGroup


class SponsorInquiryStates(StatesGroup):
    """States for sponsor inquiry dialog."""

    # Referral states
    writing_question = State()  # Referral is writing a question
    in_dialog = State()  # Referral is in active dialog with sponsor

    # Sponsor states
    viewing_inquiries = State()  # Sponsor is viewing list of inquiries
    replying = State()  # Sponsor is replying to a specific inquiry
