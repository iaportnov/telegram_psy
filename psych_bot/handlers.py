from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram import Bot
import os
import urllib.parse
import datetime

import database as db
import keyboards as kb
from states import ProfileFlow, SessionTypeFlow, ScheduleFlow, PsychMessagingFlow

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    psych = await db.get_psychologist(message.from_user.id)
    if psych and psych['name']:
        name = psych['name']
    else:
        name = message.from_user.first_name
        # Initialize an empty profile
        await db.update_psychologist(message.from_user.id, {"name": name})

    text = (
        f"👋 Здравствуйте, {name}! Это ваш личный кабинет психолога.\n"
        "Здесь вы можете управлять расписанием, редактировать анкету и видеть своих клиентов."
    )
    await message.answer(text, reply_markup=kb.main_menu())

# --- Profile Menu ---
@router.message(F.text == "✏️ Редактировать анкету")
async def show_profile_menu(message: Message):
    psych = await db.get_psychologist(message.from_user.id)
    if not psych:
        await message.answer("Сначала нажмите /start")
        return
        
    text = "Ваша анкета (что видят клиенты при /start):\n"
    text += f"🧑‍⚕️ {psych['name'] or 'Не указано'}\n"
    text += f"📍 Стаж: {psych['experience'] or 'Не указано'}\n"
    text += f"🎓 Образование: {psych['education'] or 'Не указано'}\n"
    text += f"🔹 Направления: {psych['topics'] or 'Не указано'}\n"
    text += f"🏠 Очно: {psych['address_offline'] or 'Не указано'}\n"
    text += f"💻 Онлайн: {psych['platform_online'] or 'Не указано'}\n"
    
    session_types = await db.get_session_types(message.from_user.id)
    if session_types:
        text += "\n💰 Виды сессий:\n"
        for st in session_types:
            text += f"- {st['name']} ({st['format']}, {st['duration']} мин): {st['price']} ₽\n"
    else:
        text += "\n💰 Виды сессий: Не настроены"

    await message.answer(text, reply_markup=kb.profile_menu())

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()

# --- Edit Profile Flow ---
@router.callback_query(F.data == "edit_profile")
async def edit_profile_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Режим редактирования анкеты.\n1. Ваше имя и фамилия (как представитесь клиенту):", reply_markup=kb.skip_keyboard())
    await state.set_state(ProfileFlow.name)
    await callback.answer()

async def process_profile_step(message: Message, state: FSMContext, step_name: str, next_step_state, next_question: str):
    if message.text != "👍 Оставить как было":
        await state.update_data({step_name: message.text})
    await message.answer(next_question, reply_markup=kb.skip_keyboard())
    await state.set_state(next_step_state)

@router.message(ProfileFlow.name)
async def profile_name(message: Message, state: FSMContext):
    await process_profile_step(message, state, "name", ProfileFlow.experience, "2. Стаж (число лет):")

@router.message(ProfileFlow.experience)
async def profile_exp(message: Message, state: FSMContext):
    await process_profile_step(message, state, "experience", ProfileFlow.education, "3. Образование и подход:")

@router.message(ProfileFlow.education)
async def profile_edu(message: Message, state: FSMContext):
    await process_profile_step(message, state, "education", ProfileFlow.topics, "4. Основные направления (через запятую):")

@router.message(ProfileFlow.topics)
async def profile_topics(message: Message, state: FSMContext):
    await process_profile_step(message, state, "topics", ProfileFlow.address_offline, "5. Адрес очного приёма (или 'Нет'):")

@router.message(ProfileFlow.address_offline)
async def profile_addr(message: Message, state: FSMContext):
    if message.text != "👍 Оставить как было":
        await state.update_data(address_offline=message.text)
    await message.answer("6. Онлайн-платформа (Zoom / Telegram и т.д.):", reply_markup=kb.platform_keyboard())
    await state.set_state(ProfileFlow.platform_online)

@router.message(ProfileFlow.platform_online)
async def profile_finish(message: Message, state: FSMContext):
    if message.text != "👍 Оставить как было":
        await state.update_data(platform_online=message.text)
    
    data = await state.get_data()
    if data:
        await db.update_psychologist(message.from_user.id, data)
    
    await message.answer("✅ Анкета обновлена. Клиенты увидят новые данные.", reply_markup=kb.main_menu())
    await state.clear()

# --- Session Types Flow ---
@router.callback_query(F.data == "edit_session_types")
async def edit_session_types(callback: CallbackQuery, state: FSMContext):
    await db.clear_session_types(callback.from_user.id)
    await callback.message.answer("Старые виды сессий удалены. Давайте добавим новые.", reply_markup=kb.session_type_action_keyboard())
    await callback.answer()

@router.callback_query(F.data == "add_session_type")
async def add_session_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название сессии (например: Ознакомительная, Стандартная, Групповая):", reply_markup=kb.cancel_reply_keyboard())
    await state.set_state(SessionTypeFlow.name)
    await callback.answer()

@router.message(SessionTypeFlow.name)
async def session_name(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено", reply_markup=kb.main_menu())
        return
    await state.update_data(name=message.text)
    await message.answer("Формат (Онлайн или Очно):", reply_markup=kb.formats_keyboard())
    await state.set_state(SessionTypeFlow.format)

@router.message(SessionTypeFlow.format)
async def session_format(message: Message, state: FSMContext):
    await state.update_data(format=message.text)
    await message.answer("Укажите продолжительность в минутах (например, 50):", reply_markup=kb.cancel_reply_keyboard())
    await state.set_state(SessionTypeFlow.duration)

@router.message(SessionTypeFlow.duration)
async def session_duration(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено", reply_markup=kb.main_menu())
        return
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        await message.answer("Укажите стоимость в рублях (например, 3000):")
        await state.set_state(SessionTypeFlow.price)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

@router.message(SessionTypeFlow.price)
async def session_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено", reply_markup=kb.main_menu())
        return
    try:
        price = int(message.text)
        data = await state.get_data()
        await db.add_session_type(message.from_user.id, data['name'], data['format'], data['duration'], price)
        await message.answer(f"Добавлено: {data['name']} ({data['format']}, {data['duration']} мин) - {price} ₽", reply_markup=kb.session_type_action_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

@router.callback_query(F.data == "finish_session_types")
async def finish_session_types(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("✅ Виды сессий сохранены.", reply_markup=kb.main_menu())
    await callback.answer()


# --- Schedule Flow (Simplified) ---
@router.message(F.text == "📅 Моё расписание")
async def manage_slots_menu(message: Message):
    slots = await db.get_all_slots(message.from_user.id)
    if not slots:
        await message.answer("У вас пока нет созданных слотов.", reply_markup=kb.main_menu())
    else:
        await message.answer("Ваши текущие слоты (нажмите, чтобы удалить):", reply_markup=kb.slots_management_keyboard(slots))
    
    await message.answer("Хотите добавить новые слоты?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить блок слотов", callback_data="add_slots_block")]
    ]))

@router.callback_query(F.data == "add_slots_block")
async def start_add_slots(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Добавление блока слотов.\nВведите дату в формате ДД-ММ-ГГГГ (например, 15-05-2026):", reply_markup=kb.cancel_reply_keyboard())
    await state.set_state(ScheduleFlow.day)
    await callback.answer()

@router.callback_query(F.data.startswith("del_slot_"))
async def delete_slot_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[2])
    await db.delete_slot(slot_id)
    await callback.answer("Слот удален")
    slots = await db.get_all_slots(callback.from_user.id)
    if not slots:
        await callback.message.edit_text("У вас больше нет созданных слотов.")
    else:
        await callback.message.edit_reply_markup(reply_markup=kb.slots_management_keyboard(slots))

@router.message(ScheduleFlow.day)
async def schedule_day(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=kb.main_menu())
        return
        
    try:
        # Try to parse DD-MM-YYYY
        date_obj = datetime.datetime.strptime(message.text, "%d-%m-%Y")
        db_date = date_obj.strftime("%Y-%m-%d")
        await state.update_data(day=db_date)
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте ДД-ММ-ГГГГ (например, 15-05-2026):")
        return
        
    await message.answer("Формат слота:", reply_markup=kb.formats_keyboard())
    await state.set_state(ScheduleFlow.format)

@router.message(ScheduleFlow.format)
async def schedule_format(message: Message, state: FSMContext):
    await state.update_data(format=message.text)
    await message.answer("Время начала блока в формате ЧЧ:ММ (например, 10:00):")
    await state.set_state(ScheduleFlow.start_time)

@router.message(ScheduleFlow.start_time)
async def schedule_start(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=kb.main_menu())
        return
    await state.update_data(start_time=message.text)
    await message.answer("Время окончания блока в формате ЧЧ:ММ (например, 18:00):")
    await state.set_state(ScheduleFlow.end_time)

@router.message(ScheduleFlow.end_time)
async def schedule_end(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено", reply_markup=kb.main_menu())
        return
        
    data = await state.get_data()
    interval_mins = 30 # Auto 30 minutes
    
    try:
        start_obj = datetime.datetime.strptime(data['start_time'], "%H:%M")
        end_obj = datetime.datetime.strptime(message.text, "%H:%M")
    except ValueError:
        await message.answer("Ошибка в формате времени. Убедитесь, что используете ЧЧ:ММ.")
        await state.clear()
        return

    added_slots = 0
    current_time = start_obj
    
    while current_time < end_obj:
        time_str = current_time.strftime("%H:%M")
        await db.add_slot(message.from_user.id, data['day'], time_str, data['format'])
        added_slots += 1
        current_time += datetime.timedelta(minutes=interval_mins)
        
    await message.answer(f"✅ Успешно добавлено {added_slots} слотов на {data['day']} ({data['format']})!", reply_markup=kb.main_menu())
    await state.clear()


# --- Appointments Viewer ---
def format_appointment_card(app: dict) -> str:
    display_date = "-".join(app['date'].split("-")[::-1])
    
    # Calculate end time
    start_time = datetime.datetime.strptime(app['time'], "%H:%M")
    end_time = start_time + datetime.timedelta(minutes=app['duration'])
    time_range = f"{app['time']} – {end_time.strftime('%H:%M')}"
    
    user_contact = f"@{app['username']}" if app['username'] else "Нет username"
    text = (
        f"📅 {display_date} 🕒 {time_range} | 💻 {app['slot_format']}\n"
        f"👤 {app['user_name']} ({user_contact}), {app['age']}\n"
        f"📝 Деятельность: {app['occupation']}\n"
        f"❓ Запрос: {app['user_request'] or 'Нет'}\n"
        f"💰 {app['price']} ₽ ({app['duration']} мин)"
    )
    return text

def generate_gcal_link(app: dict) -> str:
    # 2026-05-15 11:00
    date_obj = datetime.datetime.strptime(f"{app['date']} {app['time']}", "%Y-%m-%d %H:%M")
    end_obj = date_obj + datetime.timedelta(minutes=app['duration'])
    
    start_str = date_obj.strftime("%Y%m%dT%H%M%S")
    end_str = end_obj.strftime("%Y%m%dT%H%M%S")
    
    text = urllib.parse.quote(f"Сессия с {app['user_name']}")
    details = urllib.parse.quote(f"Возраст: {app['age']}, Деятельность: {app['occupation']}")
    
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={text}&dates={start_str}/{end_str}&details={details}"

@router.message(F.text == "📋 Клиенты на сегодня")
async def today_clients(message: Message):
    today = datetime.date.today().strftime('%Y-%m-%d')
    apps = await db.get_psychologist_appointments(message.from_user.id, today)
    
    if not apps:
        await message.answer("😴 На сегодня записей нет. Отдыхайте!")
        return
        
    display_date = "-".join(today.split("-")[::-1])
    await message.answer(f"📅 Ваше расписание на сегодня, {display_date}:")
    for app in apps:
        link = generate_gcal_link(app)
        await message.answer(format_appointment_card(app), reply_markup=kb.google_calendar_keyboard(link))

@router.message(F.text.startswith("/reply_"))
async def start_reply(message: Message, state: FSMContext):
    user_id = int(message.text.split("_")[1])
    await state.update_data(reply_to_user_id=user_id)
    await message.answer(f"Введите ответ для пользователя (ID: {user_id}):")
    from states import PsychMessagingFlow
    await state.set_state(PsychMessagingFlow.replying)

@router.message(PsychMessagingFlow.replying)
async def send_reply_to_user(message: Message, state: FSMContext):
    from states import PsychMessagingFlow
    current_state = await state.get_state()
    if current_state != PsychMessagingFlow.replying.state:
        return
        
    data = await state.get_data()
    user_id = data['reply_to_user_id']
    
    msg_text = (
        f"📩 Ответ от психолога:\n\n"
        f"{message.text}"
    )
    try:
        # Save to DB
        await db.save_message(message.from_user.id, user_id, message.text, is_from_psych=True)
        
        # We use the client bot token to send the message to the client
        client_bot_token = os.getenv("CLIENT_BOT_TOKEN")
        if client_bot_token:
            async with Bot(token=client_bot_token) as client_bot:
                await client_bot.send_message(user_id, msg_text)
            await message.answer("✅ Ответ отправлен пользователю.")
        else:
            raise Exception("Token not found")
    except Exception as e:
        await message.answer("❌ Ошибка при отправке ответа.")
            
    await state.clear()

@router.message(F.text == "📊 Все записи")
async def all_clients(message: Message):
    apps = await db.get_psychologist_appointments(message.from_user.id)
    if not apps:
        await message.answer("Будущих записей пока нет.")
        return
        
    await message.answer("Ваши подтвержденные записи:")
    for app in apps:
        # Calculate end time for the summary line if needed, but format_appointment_card already does it
        await message.answer(format_appointment_card(app))

@router.callback_query(F.data == "copy_link")
async def copy_link(callback: CallbackQuery):
    # In Telegram, inline buttons can't strictly "copy to clipboard" directly without text message,
    # but we can send the link in a plain text format so the user can easily copy it.
    await callback.answer()
    
    # We must retrieve the link from the markup. A bit tricky, so let's just use answer text
    for row in callback.message.reply_markup.inline_keyboard:
        for btn in row:
            if btn.url:
                await callback.message.answer(f"🔗 Ссылка:\n{btn.url}")
                return
