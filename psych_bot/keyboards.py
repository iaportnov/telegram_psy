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
        status = " (Занят)" if slot['is_booked'] else " (Свободен)"
        text = f"{display_date} {slot['time']} ({slot['format']}){status}"
        builder.button(text=text, callback_data=f"manage_slot_{slot['id']}")
    builder.adjust(1)
    return builder.as_markup()

def slot_actions_keyboard(slot_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Удалить слот", callback_data=f"del_slot_{slot_id}")
    builder.button(text="⏳ Подобрать клиентов (Лист ожидания)", callback_data=f"wl_matches_{slot_id}")
    builder.button(text="🔙 Назад к списку", callback_data="back_to_slots")
    builder.adjust(1)
    return builder.as_markup()

def wl_matches_keyboard(slot_id: int, matching_entries: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for entry in matching_entries:
        user_name = entry['user_name']
        occupation = entry['occupation'] or 'не указана'
        text = f"👤 {user_name} ({occupation}) -> Предложить"
        builder.button(text=text, callback_data=f"offer_slot_{slot_id}_{entry['user_id']}")
    
    if len(matching_entries) > 1:
        builder.button(text="📢 Предложить всем подходящим", callback_data=f"offer_slot_all_{slot_id}")
        
    builder.button(text="🔙 Назад к слоту", callback_data=f"manage_slot_{slot_id}")
    builder.adjust(1)
    return builder.as_markup()
