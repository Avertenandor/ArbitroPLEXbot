from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    """Authorization flow states."""
    waiting_for_wallet = State()  # Step 1: User enters wallet
    waiting_for_payment = State()  # Step 2: User confirms payment
    waiting_for_payment_wallet = State()  # Payment wallet selection
