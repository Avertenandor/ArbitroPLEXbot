"""
FSM States.

State groups for multi-step dialogs.
"""

from bot.states.account_recovery import AccountRecoveryStates
from bot.states.deposit import DepositStates
from bot.states.inquiry import AdminInquiryStates, InquiryStates
from bot.states.registration import RegistrationStates
from bot.states.support_states import SupportStates
from bot.states.withdrawal import WithdrawalStates


__all__ = [
    "AccountRecoveryStates",
    "AdminInquiryStates",
    "DepositStates",
    "InquiryStates",
    "RegistrationStates",
    "SupportStates",
    "WithdrawalStates",
]
