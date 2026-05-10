from aiogram.fsm.state import State, StatesGroup

class RegistrationFlow(StatesGroup):
    entering_name = State()
    entering_age = State()
    entering_occupation = State()

class BookingFlow(StatesGroup):
    choosing_session_type = State()
    choosing_slot = State()
    entering_request = State()
    confirming = State()

class MessagingFlow(StatesGroup):
    writing_message = State()
    replying = State()

class RescheduleFlow(StatesGroup):
    choosing_appointment = State()
    choosing_new_slot = State()
    entering_reason = State()

class CancelFlow(StatesGroup):
    choosing_appointment = State()
    entering_reason = State()
