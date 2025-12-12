"""
Admin States
FSM states for admin operations
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """States for admin operations"""

    # Authentication
    awaiting_master_key_input = State()  # Waiting for master key input

    # User management
    awaiting_user_to_block = State()  # Block user (with appeal)
    awaiting_user_to_terminate = State()  # Terminate user (no appeal)
    awaiting_user_to_unban = State()  # Unban user confirmation
    finding_user = State()  # Searching for a user
    changing_user_balance = State()  # Changing user balance
    selecting_deposit_to_void = State()  # Selecting user deposit to void
    confirming_deposit_void = State()  # Confirming deposit void action

    # Broadcast
    awaiting_broadcast_message = State()
    awaiting_broadcast_button_choice = State()  # Waiting for choice (add button or send)
    awaiting_broadcast_button_link = State()  # Waiting for button text|url

    # Support
    awaiting_support_reply = State()  # Waiting for admin reply text

    # Blacklist notification texts
    awaiting_block_notification_text = State()  # Waiting for block notification text
    awaiting_terminate_notification_text = State()  # Waiting for terminate notification text

    # Withdrawal management
    selecting_withdrawal = State()  # Selecting withdrawal ID to manage
    viewing_withdrawal = State()  # Viewing details (Approve/Reject options)
    confirming_withdrawal_action = State()  # Confirming approve/reject

    # Withdrawal history search
    searching_withdrawal_history = State()  # Waiting for search query

    # Removed deprecated states (2025-12-12):
    # - awaiting_user_to_ban (Legacy, no handler exists)
    # - awaiting_user_message_target (TODO handler never implemented)
    # - awaiting_user_message_content (TODO handler never implemented)
