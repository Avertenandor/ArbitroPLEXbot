from aiogram.fsm.state import State, StatesGroup

class AuthStates(StatesGroup):
    waiting_for_payment_wallet = State()

