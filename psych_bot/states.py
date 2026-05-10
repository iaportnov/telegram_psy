from aiogram.fsm.state import State, StatesGroup

class ProfileFlow(StatesGroup):
    name = State()
    experience = State()
    education = State()
    topics = State()
    address_offline = State()
    platform_online = State()

class SessionTypeFlow(StatesGroup):
    name = State()
    format = State()
    duration = State()
    price = State()

class ScheduleFlow(StatesGroup):
    day = State()
    format = State()
    start_time = State()
    end_time = State()

class PsychMessagingFlow(StatesGroup):
    replying = State()
