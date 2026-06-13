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
from states import ProfileFlow, SessionTypeFlow, ScheduleFlow, PsychMessagingFlow, GoogleCalendarFlow

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

@router.callback_query(F.data.startswith("manage_slot_"))
async def manage_slot_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[2])
    slot = await db.get_slot_by_id(slot_id)
    if not slot:
        await callback.answer("Слот не найден", show_alert=True)
        return
        
    display_date = "-".join(slot['date'].split("-")[::-1])
    status_str = "забронирован" if slot['is_booked'] else "свободен"
    text = (
        f"📅 <b>Слот</b>: {display_date} в {slot['time']}\n"
        f"📹 <b>Формат</b>: {slot['format']}\n"
        f"📌 <b>Текущий статус</b>: {status_str}\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=kb.slot_actions_keyboard(slot_id), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "back_to_slots")
async def back_to_slots_handler(callback: CallbackQuery):
    slots = await db.get_all_slots(callback.from_user.id)
    if not slots:
        await callback.message.edit_text("У вас пока нет созданных слотов.")
    else:
        await callback.message.edit_text("Ваши текущие слоты:", reply_markup=kb.slots_management_keyboard(slots))
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
         await callback.message.edit_text("Ваши текущие слоты:", reply_markup=kb.slots_management_keyboard(slots))

@router.callback_query(F.data.startswith("wl_matches_"))
async def wl_matches_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[2])
    slot = await db.get_slot_by_id(slot_id)
    if not slot:
        await callback.answer("Слот не найден", show_alert=True)
        return
        
    matching = await db.get_matching_waiting_list(slot_id)
    display_date = "-".join(slot['date'].split("-")[::-1])
    
    if not matching:
        text = (
            f"Для слота <b>{display_date} {slot['time']} ({slot['format']})</b> подходящих клиентов в листе ожидания не найдено.\n\n"
            "Бот автоматически подбирает людей по формату, дням недели и времени суток."
        )
        await callback.message.edit_text(text, reply_markup=kb.slot_actions_keyboard(slot_id), parse_mode="HTML")
    else:
        text = (
            f"Найдено <b>{len(matching)}</b> подходящих клиентов в листе ожидания для слота <b>{display_date} {slot['time']} ({slot['format']})</b>:\n\n"
            "Выберите клиента, чтобы предложить ему это время (в порядке очереди, предложение будет выслано в чат с ботом):"
        )
        await callback.message.edit_text(text, reply_markup=kb.wl_matches_keyboard(slot_id, matching), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("offer_slot_all_"))
async def offer_slot_all_handler(callback: CallbackQuery):
    slot_id = int(callback.data.split("_")[3])
    slot = await db.get_slot_by_id(slot_id)
    if not slot:
        await callback.answer("Слот не найден", show_alert=True)
        return
        
    matching = await db.get_matching_waiting_list(slot_id)
    if not matching:
        await callback.answer("Подходящие клиенты не найдены.", show_alert=True)
        return
        
    client_bot_token = os.getenv("CLIENT_BOT_TOKEN")
    if not client_bot_token:
        await callback.answer("Ошибка токена клиента", show_alert=True)
        return
        
    display_date = "-".join(slot['date'].split("-")[::-1])
    count = 0
    
    async with Bot(token=client_bot_token) as client_bot:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Забронировать и оплатить", callback_data=f"wl_offer_book_{slot_id}")
        builder.button(text="❌ Отказаться", callback_data=f"wl_offer_decline_{slot_id}")
        builder.adjust(1)
        
        offer_text = (
            "🔔 <b>Вам предложено свободное время для сессии!</b>\n\n"
            "Психолог предлагает вам записаться на сессию:\n"
            f"📅 <b>Дата</b>: {display_date}\n"
            f"⏰ <b>Время</b>: {slot['time']}\n"
            f"📹 <b>Формат</b>: {slot['format']}\n\n"
            "Бронирование выполняется в порядке очереди (кто первый оплатил, тот и занял слот). Выберите действие:"
        )
        
        for entry in matching:
            try:
                await client_bot.send_message(entry['user_id'], offer_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                count += 1
            except Exception as e:
                pass
                
    await callback.message.edit_text(
        f"✅ <b>Предложение успешно отправлено {count} клиентам!</b>\n"
        "Время будет отдано первому, кто перейдет к бронированию и совершит оплату.",
        reply_markup=kb.slots_management_keyboard(await db.get_all_slots(callback.from_user.id)),
        parse_mode="HTML"
    )
    await callback.answer("Предложения отправлены")

@router.callback_query(F.data.startswith("offer_slot_"))
async def offer_slot_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    slot_id = int(parts[2])
    user_id = int(parts[3])
    
    slot = await db.get_slot_by_id(slot_id)
    if not slot:
        await callback.answer("Слот не найден", show_alert=True)
        return
        
    client_bot_token = os.getenv("CLIENT_BOT_TOKEN")
    if not client_bot_token:
        await callback.answer("Ошибка токена клиента", show_alert=True)
        return
        
    display_date = "-".join(slot['date'].split("-")[::-1])
    
    async with Bot(token=client_bot_token) as client_bot:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Забронировать и оплатить", callback_data=f"wl_offer_book_{slot_id}")
        builder.button(text="❌ Отказаться", callback_data=f"wl_offer_decline_{slot_id}")
        builder.adjust(1)
        
        offer_text = (
            "🔔 <b>Вам предложено свободное время для сессии!</b>\n\n"
            "Психолог предлагает вам записаться на сессию:\n"
            f"📅 <b>Дата</b>: {display_date}\n"
            f"⏰ <b>Время</b>: {slot['time']}\n"
            f"📹 <b>Формат</b>: {slot['format']}\n\n"
            "Бронирование выполняется в порядке очереди. Выберите действие:"
        )
        try:
            await client_bot.send_message(user_id, offer_text, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception as e:
            await callback.answer("Не удалось отправить сообщение клиенту в бот.", show_alert=True)
            return
            
    user = await db.get_user(user_id)
    user_name = user['name'] if user else f"ID: {user_id}"
    
    await callback.message.edit_text(
        f"✅ <b>Предложение успешно отправлено клиенту {user_name}!</b>\n"
        "Время будет забронировано, как только клиент подтвердит и оплатит сессию.",
        reply_markup=kb.slots_management_keyboard(await db.get_all_slots(callback.from_user.id)),
        parse_mode="HTML"
    )
    await callback.answer("Предложение отправлено")

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
        link = db.generate_gcal_link(app, for_psychologist=True)
        card_text = db.format_meeting_card(app, for_psychologist=True)
        await message.answer(card_text, reply_markup=kb.google_calendar_keyboard(link), parse_mode="HTML")

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
        card_text = db.format_meeting_card(app, for_psychologist=True)
        await message.answer(card_text, parse_mode="HTML")

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


# --- Google Calendar Settings / Management (Sprint 5) ---

async def get_gcal_settings_text(psychologist_id: int) -> str:
    psych = await db.get_psychologist(psychologist_id)
    if not psych:
        return "Профиль психолога не инициализирован. Нажмите /start."
        
    psych_dict = dict(psych) if psych and not isinstance(psych, dict) else (psych or {})
    
    enabled = psych_dict.get("gcal_sync_enabled", 0)
    mode = psych_dict.get("gcal_sync_mode", "all")
    ical_url = psych_dict.get("gcal_ical_url")
    
    status_str = "🟢 <b>Включена</b>" if enabled else "🔴 <b>Выключена</b>"
    mode_str = "🔒 <i>Только #private</i> (скрываются только слоты, пересекающиеся с событиями календаря, содержащими тег #private)" if mode == 'private' else "🌐 <i>Все события</i> (скрываются все слоты, пересекающиеся с любыми событиями в календаре)"
    ical_status = "🔗 Подключена" if ical_url else "❌ Не подключена"
    
    text = (
        "⚙️ <b>Интеграция с Google Calendar</b>\n\n"
        f"Синхронизация: {status_str}\n"
        f"Режим: {mode_str}\n"
        f"iCal-ссылка: {ical_status}\n\n"
        "Когда синхронизация включена, бот сверяет ваши слоты с личным календарем. "
        "Если в календаре есть событие, перекрывающее слот (с учетом длительности сессии), этот слот автоматически скрывается для клиентов.\n\n"
        "Вы можете наполнять Google Календарь личными делами, чтобы избежать накладок."
    )
    return text

@router.message(F.text == "⚙️ Google Календарь")
async def show_gcal_settings(message: Message, state: FSMContext):
    await state.clear()
    psych = await db.get_psychologist(message.from_user.id)
    if not psych:
        # Initialize profile if not existing
        await db.update_psychologist(message.from_user.id, {"name": message.from_user.first_name})
        psych = await db.get_psychologist(message.from_user.id)
        
    psych_dict = dict(psych) if psych and not isinstance(psych, dict) else (psych or {})
    enabled = psych_dict.get("gcal_sync_enabled", 0)
    mode = psych_dict.get("gcal_sync_mode", "all")
    has_ical = bool(psych_dict.get("gcal_ical_url"))
    
    text = await get_gcal_settings_text(message.from_user.id)
    await message.answer(text, reply_markup=kb.google_calendar_settings_keyboard(enabled, mode, has_ical), parse_mode="HTML")

@router.callback_query(F.data == "gcal_back_settings")
async def gcal_back_settings(callback: CallbackQuery):
    psych = await db.get_psychologist(callback.from_user.id)
    psych_dict = dict(psych) if psych and not isinstance(psych, dict) else (psych or {})
    enabled = psych_dict.get("gcal_sync_enabled", 0)
    mode = psych_dict.get("gcal_sync_mode", "all")
    has_ical = bool(psych_dict.get("gcal_ical_url"))
    
    text = await get_gcal_settings_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb.google_calendar_settings_keyboard(enabled, mode, has_ical), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "gcal_toggle_sync")
async def gcal_toggle_sync(callback: CallbackQuery):
    psych = await db.get_psychologist(callback.from_user.id)
    psych_dict = dict(psych) if psych and not isinstance(psych, dict) else (psych or {})
    
    current_enabled = psych_dict.get("gcal_sync_enabled", 0)
    new_enabled = 0 if current_enabled else 1
    current_mode = psych_dict.get("gcal_sync_mode", "all")
    has_ical = bool(psych_dict.get("gcal_ical_url"))
    
    await db.update_gcal_sync_settings(callback.from_user.id, new_enabled, current_mode)
    
    text = await get_gcal_settings_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb.google_calendar_settings_keyboard(new_enabled, current_mode, has_ical), parse_mode="HTML")
    await callback.answer(f"Синхронизация {'включена' if new_enabled else 'выключена'}")

@router.callback_query(F.data == "gcal_toggle_mode")
async def gcal_toggle_mode(callback: CallbackQuery):
    psych = await db.get_psychologist(callback.from_user.id)
    psych_dict = dict(psych) if psych and not isinstance(psych, dict) else (psych or {})
    
    current_enabled = psych_dict.get("gcal_sync_enabled", 0)
    current_mode = psych_dict.get("gcal_sync_mode", "all")
    new_mode = "private" if current_mode == "all" else "all"
    has_ical = bool(psych_dict.get("gcal_ical_url"))
    
    await db.update_gcal_sync_settings(callback.from_user.id, current_enabled, new_mode)
    
    text = await get_gcal_settings_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb.google_calendar_settings_keyboard(current_enabled, new_mode, has_ical), parse_mode="HTML")
    await callback.answer(f"Установлен режим: {'Только #private' if new_mode == 'private' else 'Все события'}")

@router.callback_query(F.data == "gcal_edit_ical")
async def gcal_edit_ical_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Чтобы подключить ваш реальный Google Календарь, скопируйте секретную iCal-ссылку:\n\n"
        "1. Откройте Google Календарь (веб-версию).\n"
        "2. Перейдите в Настройки календаря (шестеренка -> Настройки).\n"
        "3. В левой колонке выберите ваш календарь.\n"
        "4. Прокрутите вниз до раздела <b>Интеграция календаря</b>.\n"
        "5. Скопируйте ссылку из поля <b>Закрытый адрес в формате iCal</b>.\n\n"
        "Отправьте полученную ссылку в чат (или нажмите '❌ Отмена'):",
        reply_markup=kb.cancel_reply_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GoogleCalendarFlow.ical_url)
    await callback.answer()

@router.message(GoogleCalendarFlow.ical_url)
async def gcal_ical_url_entered(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Ввод отменен.", reply_markup=kb.main_menu())
        return
        
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await message.answer("Неверный формат ссылки. Ссылка должна начинаться с https://. Пожалуйста, попробуйте еще раз:")
        return
        
    await db.update_gcal_ical_url(message.from_user.id, url)
    
    await message.answer("✅ iCal-ссылка успешно сохранена! События будут автоматически синхронизироваться в фоне.", reply_markup=kb.main_menu())
    await state.clear()

@router.callback_query(F.data == "gcal_list_events")
async def gcal_list_events(callback: CallbackQuery):
    events = await db.get_gcal_events(callback.from_user.id)
    if not events:
        await callback.message.edit_text(
            "📅 <b>Google Календарь пуст.</b>\n\nНет запланированных событий.",
            reply_markup=kb.google_calendar_events_keyboard([]),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "📅 <b>Ваши события в Google Календаре:</b>\n\n(нажмите на событие для управления)",
            reply_markup=kb.google_calendar_events_keyboard(events),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("gcal_event_"))
async def gcal_event_details(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    # Fetch details from DB
    async with aiosqlite.connect(db.DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM gcal_events WHERE id = ?", (event_id,)) as cursor:
            ev = await cursor.fetchone()
            
    if not ev:
        await callback.answer("Событие не найдено", show_alert=True)
        return
        
    display_date = "-".join(ev['date'].split("-")[::-1])
    text = (
        f"📅 <b>Событие Google Calendar</b>\n\n"
        f"📌 <b>Название</b>: {ev['title']}\n"
        f"📆 <b>Дата</b>: {display_date}\n"
        f"⏰ <b>Время</b>: {ev['start_time']} – {ev['end_time']}\n"
    )
    await callback.message.edit_text(text, reply_markup=kb.google_calendar_event_actions_keyboard(event_id), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("gcal_del_event_"))
async def gcal_del_event(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[3])
    await db.delete_gcal_event(event_id)
    await callback.answer("Событие удалено")
    # Return to listing
    await gcal_list_events(callback)

# --- FSM Add Google Calendar Event ---
@router.callback_query(F.data == "gcal_add_event")
async def gcal_add_event_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название события (например: 'Обед' или 'Встреча #private'):", reply_markup=kb.cancel_reply_keyboard())
    await state.set_state(GoogleCalendarFlow.event_title)
    await callback.answer()

@router.message(GoogleCalendarFlow.event_title)
async def gcal_event_title_entered(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=kb.main_menu())
        return
    await state.update_data(title=message.text)
    await message.answer("Введите дату события в формате ДД-ММ-ГГГГ (например, 15-05-2026):", reply_markup=kb.skip_keyboard())
    await state.set_state(GoogleCalendarFlow.event_date)

@router.message(GoogleCalendarFlow.event_date)
async def gcal_event_date_entered(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=kb.main_menu())
        return
        
    date_str = message.text
    if date_str == "👍 Оставить как было":
        date_str = datetime.date.today().strftime("%d-%m-%Y")
        
    try:
        # Validate date format
        parsed_date = datetime.datetime.strptime(date_str, "%d-%m-%Y")
        iso_date = parsed_date.strftime("%Y-%m-%d")
        await state.update_data(date=iso_date)
        await message.answer("Введите время начала в формате ЧЧ:ММ (например, 14:00):", reply_markup=kb.cancel_reply_keyboard())
        await state.set_state(GoogleCalendarFlow.event_start)
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте ДД-ММ-ГГГГ:")

@router.message(GoogleCalendarFlow.event_start)
async def gcal_event_start_entered(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=kb.main_menu())
        return
        
    try:
        datetime.datetime.strptime(message.text, "%H:%M")
        await state.update_data(start_time=message.text)
        await message.answer("Введите время окончания в формате ЧЧ:ММ (например, 15:30):")
        await state.set_state(GoogleCalendarFlow.event_end)
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, используйте ЧЧ:ММ:")

@router.message(GoogleCalendarFlow.event_end)
async def gcal_event_end_entered(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Добавление отменено.", reply_markup=kb.main_menu())
        return
        
    try:
        datetime.datetime.strptime(message.text, "%H:%M")
        data = await state.get_data()
        
        # Verify start < end
        start_dt = datetime.datetime.strptime(data['start_time'], "%H:%M")
        end_dt = datetime.datetime.strptime(message.text, "%H:%M")
        if end_dt <= start_dt:
            await message.answer("Время окончания должно быть позже времени начала. Пожалуйста, введите корректное время окончания:")
            return
            
        import aiosqlite
        # Save to DB
        await db.add_gcal_event(
            psychologist_id=message.from_user.id,
            title=data['title'],
            date=data['date'],
            start_time=data['start_time'],
            end_time=message.text
        )
        
        display_date = "-".join(data['date'].split("-")[::-1])
        await message.answer(
            f"✅ Событие '{data['title']}' на {display_date} с {data['start_time']} до {message.text} добавлено в Google Календарь!",
            reply_markup=kb.main_menu()
        )
        await state.clear()
    except ValueError:
        await message.answer("Неверный формат времени. Пожалуйста, используйте ЧЧ:ММ:")

