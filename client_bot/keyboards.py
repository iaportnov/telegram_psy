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
    
    # Add option to sign up for waiting list
    builder.button(text="⏳ Встать в лист ожидания", callback_data="join_waiting_list")
    
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

def payment_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить полностью (100%)", callback_data=f"pay_full_{appointment_id}")
    builder.button(text="💵 Внести предоплату (50%)", callback_data=f"pay_pre_{appointment_id}")
    builder.adjust(1)
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
        
        # Translate status for user display
        status_display = "Ожидает оплаты ⏳" if app['status'] == 'pending' else "Предоплата 50% ⚠️" if app['status'] == 'prepaid' else "Подтверждена ✅" if app['status'] == 'confirmed' else app['status']
        text = f"{display_date} {time_range} ({status_display})"
        builder.button(text=text, callback_data=f"app_{action}_{app['id']}")
    builder.adjust(1)
    return builder.as_markup()

def manage_appointment_keyboard(appointment_id: int, status: str, gcal_link: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == 'pending':
        builder.button(text="💳 Оплатить полностью (100%)", callback_data=f"pay_full_{appointment_id}")
        builder.button(text="💵 Внести предоплату (50%)", callback_data=f"pay_pre_{appointment_id}")
        builder.button(text="❌ Отменить", callback_data=f"cancel_app_{appointment_id}")
        builder.adjust(1)
    else:
        if gcal_link:
            builder.button(text="📅 Добавить в Google Календарь", url=gcal_link)
        builder.button(text="🔄 Перенести", callback_data=f"reschedule_{appointment_id}")
        builder.button(text="❌ Отменить", callback_data=f"cancel_app_{appointment_id}")
        builder.button(text="✉️ Написать психологу", callback_data=f"msg_psych_{appointment_id}")
        builder.adjust(1)
    return builder.as_markup()

def google_calendar_keyboard(link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Добавить в Google Календарь", url=link)
    builder.button(text="Скопировать ссылку", callback_data="copy_link")
    builder.adjust(1)
    return builder.as_markup()

def waiting_list_only_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏳ Встать в лист ожидания", callback_data="join_waiting_list")
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()

def wl_formats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💻 Онлайн", callback_data="wl_fmt_online")
    builder.button(text="📍 Очно", callback_data="wl_fmt_offline")
    builder.button(text="🌍 Любой формат", callback_data="wl_fmt_any")
    builder.button(text="❌ Отмена", callback_data="cancel_wl")
    builder.adjust(1)
    return builder.as_markup()

def wl_days_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Будни (Пн-Пт)", callback_data="wl_days_weekdays")
    builder.button(text="🎉 Выходные (Сб-Вс)", callback_data="wl_days_weekends")
    builder.button(text="🗓️ Любые дни", callback_data="wl_days_any")
    builder.button(text="❌ Отмена", callback_data="cancel_wl")
    builder.adjust(1)
    return builder.as_markup()

def wl_time_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🌅 Утро (10:00 - 14:00)", callback_data="wl_time_morning")
    builder.button(text="☀️ День (14:00 - 18:00)", callback_data="wl_time_afternoon")
    builder.button(text="🌆 Вечер (18:00 - 22:00)", callback_data="wl_time_evening")
    builder.button(text="🌌 Любое время", callback_data="wl_time_any")
    builder.button(text="❌ Отмена", callback_data="cancel_wl")
    builder.adjust(1)
    return builder.as_markup()
