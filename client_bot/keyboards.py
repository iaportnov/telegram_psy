from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📅 Записаться")],
        [KeyboardButton(text="📋 Мои записи")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def session_types_keyboard(session_types: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for st in session_types:
        text = f"{st['name']} ({st['format']}, {st['duration']} мин) - {st['price']} ₽"
        builder.button(text=text, callback_data=f"stype_{st['id']}")
    builder.adjust(1)
    return builder.as_markup()

def slots_keyboard(slots: list, show_cancel: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        # Convert YYYY-MM-DD to DD-MM-YYYY for display
        display_date = "-".join(slot['date'].split("-")[::-1])
        builder.button(text=f"{display_date} {slot['time']} ({slot['format']})", callback_data=f"slot_{slot['id']}")
    
    if show_cancel:
        builder.button(text="❌ Отмена", callback_data="cancel_reschedule")
        
    builder.adjust(1)
    return builder.as_markup()

def confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data="confirm_booking")
    builder.button(text="✏️ Изменить", callback_data="edit_booking")
    builder.button(text="❌ Отменить", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()

def payment_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить", callback_data="pay_stub")
    return builder.as_markup()

import datetime

def user_appointments_keyboard(appointments: list, action: str = "view") -> InlineKeyboardMarkup:
    # action can be "view" or "manage"
    builder = InlineKeyboardBuilder()
    for app in appointments:
        display_date = "-".join(app['date'].split("-")[::-1])
        
        # Calculate end time
        start_time = datetime.datetime.strptime(app['time'], "%H:%M")
        end_time = start_time + datetime.timedelta(minutes=app['duration'])
        time_range = f"{app['time']} – {end_time.strftime('%H:%M')}"
        
        text = f"{display_date} {time_range} - {app['status']}"
        builder.button(text=text, callback_data=f"app_{action}_{app['id']}")
    builder.adjust(1)
    return builder.as_markup()

def manage_appointment_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Перенести", callback_data=f"reschedule_{appointment_id}")
    builder.button(text="❌ Отменить", callback_data=f"cancel_app_{appointment_id}")
    builder.button(text="✉️ Написать психологу", callback_data=f"msg_psych_{appointment_id}")
    builder.adjust(2)
    return builder.as_markup()
