from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_support_message = State()
    viewing_course = State()
    selecting_tariff = State()
    confirming_payment = State()