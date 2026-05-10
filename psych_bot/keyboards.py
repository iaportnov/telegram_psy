from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📅 Моё расписание"), KeyboardButton(text="✏️ Редактировать анкету")],
        [KeyboardButton(text="📋 Клиенты на сегодня"), KeyboardButton(text="📊 Все записи")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def profile_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Редактировать анкету", callback_data="edit_profile")
    builder.button(text="💳 Настроить виды сессий (Цены)", callback_data="edit_session_types")
    builder.button(text="Отмена", callback_data="cancel_action")
    builder.adjust(1)
    return builder.as_markup()

def platform_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Zoom"), KeyboardButton(text="Telegram")],
        [KeyboardButton(text="Google Meet"), KeyboardButton(text="Skype")],
        [KeyboardButton(text="👍 Оставить как было")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def skip_keyboard() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="👍 Оставить как было")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def session_type_action_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить вид сессии", callback_data="add_session_type")
    builder.button(text="✅ Завершить", callback_data="finish_session_types")
    builder.adjust(1)
    return builder.as_markup()

def days_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Пн"), KeyboardButton(text="Вт"), KeyboardButton(text="Ср"), KeyboardButton(text="Чт")],
        [KeyboardButton(text="Пт"), KeyboardButton(text="Сб"), KeyboardButton(text="Вс")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def formats_keyboard() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="Онлайн"), KeyboardButton(text="Очно")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def google_calendar_keyboard(link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Добавить в Google Календарь", url=link)
    builder.button(text="Скопировать ссылку", callback_data="copy_link")
    builder.adjust(1)
    return builder.as_markup()

def slots_management_keyboard(slots: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        display_date = "-".join(slot['date'].split("-")[::-1])
        text = f"❌ {display_date} {slot['time']} ({slot['format']})"
        builder.button(text=text, callback_data=f"del_slot_{slot['id']}")
    builder.adjust(1)
    return builder.as_markup()
