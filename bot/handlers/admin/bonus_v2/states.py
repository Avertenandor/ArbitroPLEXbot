"""
Bonus Management States.

Defines FSM states for the bonus management workflow v2.
Only includes actively used states to keep the state machine clean and maintainable.

States:
    - menu: Main bonus management menu
    - grant_user: User selection for bonus grant
    - grant_amount: Amount input for bonus grant
    - grant_reason: Reason input/selection for bonus grant
    - grant_confirm: Final confirmation before granting bonus
    - search_user: User search for viewing bonus history
    - cancel_reason: Reason input for bonus cancellation
"""

from aiogram.fsm.state import State, StatesGroup


class BonusStates(StatesGroup):
    """FSM states for bonus management workflow."""

    menu: State = State()
    """Main bonus management menu state.

    User can select from available actions:
    - Grant bonus
    - Search user bonuses
    - View statistics
    - Navigate back
    """

    # Bonus granting flow (4-step process)
    grant_user: State = State()
    """Step 1: User selection for bonus grant.

    Admin enters user identifier (ID, username, or phone).
    System validates user existence before proceeding.
    """

    grant_amount: State = State()
    """Step 2: Amount input for bonus grant.

    Admin enters bonus amount (must be positive decimal).
    System validates amount format and range.
    """

    grant_reason: State = State()
    """Step 3: Reason input/selection for bonus grant.

    Admin can either:
    - Select from predefined reason templates
    - Enter custom reason text
    """

    grant_confirm: State = State()
    """Step 4: Final confirmation before granting bonus.

    Displays summary of:
    - Target user
    - Bonus amount
    - Reason
    Requires explicit confirmation before database commit.
    """

    # User search flow
    search_user: State = State()
    """User search for viewing bonus history.

    Admin enters user identifier to search.
    System retrieves and displays user's bonus transaction history.
    """

    # Bonus cancellation flow
    cancel_reason: State = State()
    """Reason input for bonus cancellation.

    Admin must provide a reason when canceling a bonus.
    This reason is logged for audit trail.
    Only super_admin and extended_admin (for own bonuses) can cancel.
    """
