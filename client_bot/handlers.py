from aiogram import Router, F, Bot
import os
import datetime
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import RegistrationFlow, BookingFlow, RescheduleFlow, CancelFlow, MessagingFlow, WaitingListFlow

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Check if user exists
    user = await db.get_user(message.from_user.id)
    psych = await db.get_first_psychologist()
    
    psych_info = ""
    if psych:
        psych_info += f"🧑‍⚕️ {psych['name'] or 'Психолог'}\n"
        psych_info += f"📍 Стаж: {psych['experience'] or 'Не указано'}\n"
        psych_info += f"🎓 Образование: {psych['education'] or 'Не указано'}\n"
        psych_info += f"🔹 Направления: {psych['topics'] or 'Не указано'}\n\n"
    
    if user:
        text = (
            f"Здравствуйте, {user['name']}! 👋\n\n"
            f"{psych_info}"
            "📌 Что умеет этот бот\n"
            "* Запись на доступные слоты\n"
            "* Прямая связь с психологом"
        )
        await message.answer(text, reply_markup=kb.main_menu())
    else:
        text = (
            f"Здравствуйте! 👋 Добро пожаловать в бот для записи на консультацию.\n\n"
            "Я - ваш психолог."
            f"{psych_info}"
            "Давайте познакомимся. Как вас зовут?"
        )
        await message.answer(text)
        await state.set_state(RegistrationFlow.entering_name)

# --- Registration Flow ---
@router.message(RegistrationFlow.entering_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько вам лет?")
    await state.set_state(RegistrationFlow.entering_age)

@router.message(RegistrationFlow.entering_age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Чем вы занимаетесь?")
    await state.set_state(RegistrationFlow.entering_occupation)

@router.message(RegistrationFlow.entering_occupation)
async def process_occupation(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data['name']
    age = data['age']
    occupation = message.text
    username = message.from_user.username
    
    await db.create_user(message.from_user.id, username, name, age, occupation)
    
    text = (
        "Спасибо! Ваша анкета сохранена.\n\n"
        "Теперь вы можете записываться на сессии."
    )
    await message.answer(text, reply_markup=kb.main_menu())
    await state.clear()

# --- Booking Flow ---
@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.clear()
    
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("Пожалуйста, сначала зарегистрируйтесь, нажав /start")
        return

    psych = await db.get_first_psychologist()
    if not psych:
        await message.answer("К сожалению, психолог еще не настроил свой профиль.")
        return

    session_types = await db.get_session_types(psych['telegram_id'])
    if not session_types:
        await message.answer("Психолог еще не добавил доступные виды сессий.")
        return
        
    await message.answer("Выберите формат сессии:", reply_markup=kb.session_types_keyboard(session_types))
    await state.set_state(BookingFlow.choosing_session_type)

@router.callback_query(F.data.startswith("stype_"), BookingFlow.choosing_session_type)
async def process_session_type_selection(callback: CallbackQuery, state: FSMContext):
    stype_id = int(callback.data.split("_")[1])
    await state.update_data(session_type_id=stype_id)
    
    state_data = await state.get_data()
    if 'slot_id' in state_data:
        # Proceed directly to request input since slot is already selected
        await callback.message.edit_text("Кратко опишите ваш запрос на сессию (о чем вы хотите поговорить?):")
        await state.set_state(BookingFlow.entering_request)
        await callback.answer()
        return

    psych = await db.get_first_psychologist()
    slots = await db.get_available_slots(psych['telegram_id'])
    stype = await db.get_session_type(stype_id)
    
    # Filter slots based on the selected session format (Online/Offline)
    format_filtered_slots = [s for s in slots if s['format'].lower() == stype['format'].lower()]
    
    # Filter slots based on Google Calendar events (Sprint 5)
    gcal_filtered_slots = await db.filter_slots_by_gcal(psych['telegram_id'], format_filtered_slots, stype['duration'])
    
    final_slots = []
    import datetime
    
    for slot in gcal_filtered_slots:
        # Get confirmed appointments for this slot's date
        conf_apps = await db.get_confirmed_appointments_by_date(psych['telegram_id'], slot['date'])
        
        slot_start = datetime.datetime.strptime(slot['time'], "%H:%M")
        slot_end = slot_start + datetime.timedelta(minutes=stype['duration'])
        
        has_overlap = False
        for app in conf_apps:
            app_start = datetime.datetime.strptime(app['time'], "%H:%M")
            app_end = app_start + datetime.timedelta(minutes=app['duration'])
            
            # Check overlap: max(start1, start2) < min(end1, end2)
            if max(slot_start, app_start) < min(slot_end, app_end):
                has_overlap = True
                break
        
        if not has_overlap:
            final_slots.append(slot)

    if not final_slots:
        await callback.message.edit_text(
            "К сожалению, сейчас нет доступных слотов для записи в этом формате. "
            "Хотите записаться в лист ожидания? Мы сообщим вам, как только появится свободное окно!",
            reply_markup=kb.waiting_list_only_keyboard()
        )
        return
        
    await callback.message.edit_text("Выберите удобное время:", reply_markup=kb.slots_keyboard(final_slots))
    await state.set_state(BookingFlow.choosing_slot)
    await callback.answer()

@router.callback_query(F.data.startswith("slot_"), BookingFlow.choosing_slot)
async def process_slot_selection(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[1])
    await state.update_data(slot_id=slot_id)
    
    await callback.message.edit_text("Кратко опишите ваш запрос на сессию (о чем вы хотите поговорить?):")
    await state.set_state(BookingFlow.entering_request)
    await callback.answer()

@router.message(BookingFlow.entering_request)
async def process_request(message: Message, state: FSMContext):
    await state.update_data(user_request=message.text)
    data = await state.get_data()
    slot_id = data['slot_id']
    slot = await db.get_slot_by_id(slot_id)
    stype = await db.get_session_type(data['session_type_id'])
    
    display_date = "-".join(slot['date'].split("-")[::-1])
    
    # Calculate end time
    start_time = datetime.datetime.strptime(slot['time'], "%H:%M")
    end_time = start_time + datetime.timedelta(minutes=stype['duration'])
    time_range = f"{slot['time']} – {end_time.strftime('%H:%M')}"
    
    text = (
        "📋 <b>ПРЕДВАРИТЕЛЬНЫЕ ДЕТАЛИ ЗАПИСИ</b>\n"
        "--------------------------------\n"
        f"📌 <b>Вид сессии</b>: {stype['name']}\n"
        f"💰 <b>Стоимость</b>: {stype['price']} ₽\n"
        f"📹 <b>Формат</b>: {stype['format']} ({stype['duration']} мин)\n"
        f"⏰ <b>Время</b>: {display_date} {time_range}\n"
        f"📝 <b>Ваш запрос</b>: {message.text}\n"
        "--------------------------------\n"
        "💳 <b>Условия оплаты</b>:\n"
        "Для подтверждения бронирования необходимо произвести оплату (100% стоимости) или внести предоплату (50%). "
        "Оплата производится через встроенный безопасный платежный шлюз. "
        "В случае отмены или переноса встречи менее чем за 24 часа предоплата не возвращается."
    )
    await message.answer(text, reply_markup=kb.confirmation_keyboard(), parse_mode="HTML")
    await state.set_state(BookingFlow.confirming)


@router.callback_query(F.data == "confirm_booking", BookingFlow.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("Ошибка пользователя", show_alert=True)
        return

    app_id = await db.create_appointment(
        user_id=callback.from_user.id,
        slot_id=data['slot_id'],
        session_type_id=data['session_type_id'],
        user_request=data.get('user_request')
    )
    await state.update_data(appointment_id=app_id)
    await callback.message.edit_text("Для завершения записи необходимо произвести оплату.", reply_markup=kb.payment_keyboard(app_id))
    await callback.answer()

@router.callback_query(F.data == "edit_booking", BookingFlow.confirming)
async def edit_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    stype_id = data.get('session_type_id')
    
    psych = await db.get_first_psychologist()
    slots = await db.get_available_slots(psych['telegram_id'])
    stype = await db.get_session_type(stype_id)
    
    format_filtered_slots = [s for s in slots if s['format'].lower() == stype['format'].lower()]
    
    gcal_filtered_slots = await db.filter_slots_by_gcal(psych['telegram_id'], format_filtered_slots, stype['duration'])
    
    final_slots = []
    for slot in gcal_filtered_slots:
        conf_apps = await db.get_confirmed_appointments_by_date(psych['telegram_id'], slot['date'])
        slot_start = datetime.datetime.strptime(slot['time'], "%H:%M")
        slot_end = slot_start + datetime.timedelta(minutes=stype['duration'])
        has_overlap = False
        for app in conf_apps:
            app_start = datetime.datetime.strptime(app['time'], "%H:%M")
            app_end = app_start + datetime.timedelta(minutes=app['duration'])
            if max(slot_start, app_start) < min(slot_end, app_end):
                has_overlap = True
                break
        if not has_overlap:
            final_slots.append(slot)

    await callback.message.edit_text("Выберите удобное время (или оставьте прежнее):", reply_markup=kb.slots_keyboard(final_slots))
    await state.set_state(BookingFlow.choosing_slot)
    await callback.answer()

@router.callback_query(F.data == "cancel_booking", BookingFlow.confirming)
async def cancel_booking_draft(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись отменена.")
    await callback.answer()

# @router.callback_query(F.data == "pay_stub")
# async def process_payment(callback: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     app_id = data.get("appointment_id")
#     if app_id:
#         await db.confirm_appointment(app_id)
#         app = await db.get_appointment(app_id)
#         text = (
#             "✅ Запись подтверждена!\n\n"
#             "Ваша запись\n"
#             f"Тип: {app['session_name']}\n"
#             f"💰 Стоимость: {app['price']} ₽ (Оплачено)\n"
#             f"📹 Формат: {app['session_format']} ({app['duration']} мин)\n"
#             f"⏰ Время: {app['date']} {app['time']}\n"
#         )
#         if app['session_format'].lower() == 'онлайн' and app['platform_online']:
#             text += f"💻 Платформа: {app['platform_online']}\n"
#         elif app['session_format'].lower() == 'очно' and app['address_offline']:
#             text += f"🏠 Адрес: {app['address_offline']}\n"
            
#         await callback.message.edit_text(text)
#         await callback.message.answer("🎉 Благодарим вас за запись! Оплата прошла успешно.")
#         await callback.answer("Благодарим вас за запись! Оплата прошла успешно.", show_alert=True)
#     else:
#         await callback.message.answer("Произошла ошибка при подтверждении записи.")
#         await callback.answer()
#     await state.clear()

@router.callback_query(F.data.startswith("pay_full_"))
@router.callback_query(F.data.startswith("pay_pre_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    is_prepayment = callback.data.startswith("pay_pre_")
    app_id = int(callback.data.split("_")[2])
    
    if app_id:
        if is_prepayment:
            await db.prepay_appointment(app_id)
        else:
            await db.confirm_appointment(app_id)
            
        app = await db.get_appointment(app_id)
        
        # Remove client from waiting list
        await db.remove_from_waiting_list(callback.from_user.id)
        
        # Format and show full meeting card to client
        client_card = db.format_meeting_card(app, for_psychologist=False)
        gcal_link = db.generate_gcal_link(app, for_psychologist=False)
        await callback.message.edit_text(client_card, reply_markup=kb.manage_appointment_keyboard(app_id, app['status'], gcal_link), parse_mode="HTML")
        
        # Send confirmation/thanks
        await callback.message.answer("🎉 Благодарим вас за запись! Оплата прошла успешно.")
        await callback.answer("Благодарим вас за запись! Оплата прошла успешно.", show_alert=True)
        
        # Notify psychologist
        psych_bot_token = os.getenv("PSYCH_BOT_TOKEN")
        if psych_bot_token:
            try:
                async with Bot(token=psych_bot_token) as psych_bot:
                    psych_card = db.format_meeting_card(app, for_psychologist=True)
                    psych_gcal = db.generate_gcal_link(app, for_psychologist=True)
                    await psych_bot.send_message(
                        app['psychologist_id'],
                        f"🎉 <b>Подтверждена новая запись!</b>\n\n{psych_card}",
                        reply_markup=kb.google_calendar_keyboard(psych_gcal),
                        parse_mode="HTML"
                    )
            except Exception as e:
                logging.error(f"Error notifying psychologist: {e}")
    else:
        await callback.message.answer("Произошла ошибка при подтверждении записи.")
        await callback.answer()
    
    await state.clear()

# --- Manage Appointments Flow ---
@router.message(F.text == "📋 Мои записи")
async def my_appointments(message: Message):
    appointments = await db.get_user_appointments(message.from_user.id)
    if not appointments:
        await message.answer("У вас пока нет активных записей.")
        return
    await message.answer("Ваши записи. Выберите запись для управления:", reply_markup=kb.user_appointments_keyboard(appointments, "manage"))

@router.callback_query(F.data.startswith("app_manage_"))
async def manage_appointment(callback: CallbackQuery):
    app_id = int(callback.data.split("_")[2])
    app = await db.get_appointment(app_id)
    if not app:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    
    card_text = db.format_meeting_card(app, for_psychologist=False)
    gcal_link = db.generate_gcal_link(app, for_psychologist=False) if app['status'] != 'pending' else None
    await callback.message.answer(card_text, reply_markup=kb.manage_appointment_keyboard(app_id, app['status'], gcal_link), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("pay_pending_"))
async def pay_pending_appointment(callback: CallbackQuery):
    app_id = int(callback.data.split("_")[2])
    app = await db.get_appointment(app_id)
    if not app:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    await callback.message.edit_text("Для завершения записи необходимо произвести оплату.", reply_markup=kb.payment_keyboard(app_id))
    await callback.answer()

# --- Cancel Existing Appointment ---
@router.callback_query(F.data.startswith("cancel_app_"))
async def cancel_existing_appointment(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[2])
    app = await db.get_appointment(app_id)
    if app:
        await db.cancel_appointment(app_id, reason="Отменено клиентом")
        await callback.message.edit_text("✅ Запись отменена.")
        
        # Notify psychologist
        psych_bot_token = os.getenv("PSYCH_BOT_TOKEN")
        if psych_bot_token:
            try:
                async with Bot(token=psych_bot_token) as psych_bot:
                    display_date = "-".join(app['date'].split("-")[::-1])
                    user_contact = f"@{app['username']}" if app['username'] else "нет"
                    notify_text = (
                        f"❌ <b>Запись отменена клиентом!</b>\n\n"
                        f"👤 <b>Клиент</b>: {app['user_name']} ({user_contact})\n"
                        f"📌 <b>Сессия</b>: {app['session_name']}\n"
                        f"⏰ <b>Было назначено на</b>: {display_date} в {app['time']}\n"
                        f"💰 <b>Стоимость</b>: {app['price']} ₽"
                    )
                    await psych_bot.send_message(app['psychologist_id'], notify_text, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Error notifying psychologist on cancellation: {e}")
    else:
        await callback.message.edit_text("✅ Запись отменена.")
    await callback.answer()

@router.callback_query(F.data.startswith("msg_psych_"))
async def start_messaging_psych(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[2])
    await state.update_data(app_id=app_id)
    await callback.message.answer("Введите сообщение для психолога:")
    from states import MessagingFlow
    await state.set_state(MessagingFlow.writing_message)
    await callback.answer()

@router.message(MessagingFlow.writing_message)
async def send_message_to_psych(message: Message, state: FSMContext):
    data = await state.get_data()
    app_id = data['app_id']
    app = await db.get_appointment(app_id)
    psych = await db.get_psychologist(app['psychologist_id'])
    user = await db.get_user(message.from_user.id)
    
    if psych:
        psych_id = psych['telegram_id']
        msg_text = (
            f"📨 Новое сообщение от клиента: {user['name']}\n"
            f"Запись: {app['date']} {app['time']}\n\n"
            f"Текст: {message.text}\n\n"
            f"Для ответа нажмите: /reply_{message.from_user.id}"
        )
        try:
            # Save to DB
            await db.save_message(message.from_user.id, psych_id, message.text, is_from_psych=False)

            # We use the psych bot token to send the message so it appears in the psych bot
            psych_bot_token = os.getenv("PSYCH_BOT_TOKEN")
            if psych_bot_token:
                async with Bot(token=psych_bot_token) as psych_bot:
                    await psych_bot.send_message(psych_id, msg_text)
                await message.answer(f"Сообщение отправлено, {app['psych_name']} попытается ответить в ближайшее время. ✅")
            else:
                raise Exception("Token not found")
        except Exception:
            # Fallback to current bot if psych bot fails
            try:
                await message.bot.send_message(psych_id, msg_text)
                await message.answer(f"Сообщение отправлено, {app['psych_name']} попытается ответить в ближайшее время. ✅")
            except Exception:
                await message.answer("❌ Не удалось отправить сообщение.")
            
    await state.clear()

# Reschedule flow is a bit complex since it requires selecting session type again, or assuming same type.
# For simplicity, if they reschedule, they should just select a new slot for the same session type.
@router.callback_query(F.data.startswith("reschedule_"))
async def reschedule_appointment(callback: CallbackQuery, state: FSMContext):
    app_id = int(callback.data.split("_")[1])
    await state.update_data(app_id=app_id)
    
    app = await db.get_appointment(app_id)
    psych_id = app['psychologist_id']
    
    slots = await db.get_available_slots(psych_id)
    
    # Filter slots based on the current session format and check for overlaps
    import datetime
    
    format_filtered = [s for s in slots if s['format'].lower() == app['session_format'].lower()]
    
    gcal_filtered_slots = await db.filter_slots_by_gcal(psych_id, format_filtered, app['duration'])
    
    final_slots = []
    for slot in gcal_filtered_slots:
        conf_apps = await db.get_confirmed_appointments_by_date(psych_id, slot['date'])
        slot_start = datetime.datetime.strptime(slot['time'], "%H:%M")
        slot_end = slot_start + datetime.timedelta(minutes=app['duration'])
        
        has_overlap = False
        for ca in conf_apps:
            # Important: skip the current appointment we are rescheduling
            # (Actually, confirm_appointment deletes slots, but pending ones might exist. 
            # Confirmed ones definitely shouldn't overlap except for the one we're moving)
            # But the slot we are currently occupying is already 'booked' or deleted.
            
            ca_start = datetime.datetime.strptime(ca['time'], "%H:%M")
            ca_end = ca_start + datetime.timedelta(minutes=ca['duration'])
            
            if max(slot_start, ca_start) < min(slot_end, ca_end):
                has_overlap = True
                break
        
        if not has_overlap:
            final_slots.append(slot)
            
    if not final_slots:
        await callback.message.answer("К сожалению, нет других доступных слотов для переноса в этом формате.")
        return
        
    await callback.message.edit_text("Выберите новое время:", reply_markup=kb.slots_keyboard(final_slots, show_cancel=True))
    await state.set_state(RescheduleFlow.choosing_new_slot)
    await callback.answer()

@router.callback_query(F.data == "cancel_reschedule", RescheduleFlow.choosing_new_slot)
async def cancel_reschedule(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Перенос отменен.")
    await callback.answer()

@router.callback_query(F.data.startswith("slot_"), RescheduleFlow.choosing_new_slot)
async def process_reschedule_slot(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    app_id = data['app_id']
    
    old_app = await db.get_appointment(app_id)
    
    # Cancel old appointment
    await db.cancel_appointment(app_id, reason="Перенос клиентом")
    
    # Create new appointment
    new_app_id = await db.create_appointment(
        user_id=callback.from_user.id,
        slot_id=slot_id,
        session_type_id=old_app['session_type_id'],
        user_request=old_app['user_request']
    )
    # Confirm it immediately
    await db.confirm_appointment(new_app_id)
    
    new_app = await db.get_appointment(new_app_id)
    client_card = db.format_meeting_card(new_app, for_psychologist=False)
    gcal_link = db.generate_gcal_link(new_app, for_psychologist=False)
    
    await callback.message.answer(
        f"✅ <b>Запись успешно перенесена!</b>\n\n{client_card}",
        reply_markup=kb.manage_appointment_keyboard(new_app_id, new_app['status'], gcal_link),
        parse_mode="HTML"
    )
    
    # Notify psychologist
    psych_bot_token = os.getenv("PSYCH_BOT_TOKEN")
    if psych_bot_token:
        try:
            async with Bot(token=psych_bot_token) as psych_bot:
                old_date_display = "-".join(old_app['date'].split("-")[::-1])
                psych_card = db.format_meeting_card(new_app, for_psychologist=True)
                psych_gcal = db.generate_gcal_link(new_app, for_psychologist=True)
                notify_text = (
                    f"🔄 <b>Запись перенесена клиентом!</b>\n"
                    f"Прежняя дата/время: {old_date_display} в {old_app['time']}\n\n"
                    f"📋 <b>Новые детали встречи:</b>\n{psych_card}"
                )
                await psych_bot.send_message(
                    new_app['psychologist_id'],
                    notify_text,
                    reply_markup=kb.google_calendar_keyboard(psych_gcal),
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.error(f"Error notifying psychologist on rescheduling: {e}")

    await state.clear()
    await callback.answer()


# --- Waiting List Flow ---
@router.callback_query(F.data == "join_waiting_list")
async def start_waiting_list(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Выберите желаемый формат сессии в листе ожидания:",
        reply_markup=kb.wl_formats_keyboard()
    )
    await state.set_state(WaitingListFlow.choosing_format)
    await callback.answer()

@router.callback_query(F.data == "cancel_wl", WaitingListFlow.choosing_format)
@router.callback_query(F.data == "cancel_wl", WaitingListFlow.choosing_days)
@router.callback_query(F.data == "cancel_wl", WaitingListFlow.choosing_time)
async def cancel_wl(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Запись в лист ожидания отменена.")
    await callback.answer()

@router.callback_query(F.data.startswith("wl_fmt_"), WaitingListFlow.choosing_format)
async def process_wl_format(callback: CallbackQuery, state: FSMContext):
    fmt = callback.data.split("_")[2] # 'online', 'offline', 'any'
    await state.update_data(wl_format=fmt)
    
    await callback.message.edit_text(
        "Выберите предпочтительные дни для сессий:",
        reply_markup=kb.wl_days_keyboard()
    )
    await state.set_state(WaitingListFlow.choosing_days)
    await callback.answer()

@router.callback_query(F.data.startswith("wl_days_"), WaitingListFlow.choosing_days)
async def process_wl_days(callback: CallbackQuery, state: FSMContext):
    days = callback.data.split("_")[2] # 'weekdays', 'weekends', 'any'
    await state.update_data(wl_days=days)
    
    await callback.message.edit_text(
        "Выберите предпочтительное время дня:",
        reply_markup=kb.wl_time_keyboard()
    )
    await state.set_state(WaitingListFlow.choosing_time)
    await callback.answer()

@router.callback_query(F.data.startswith("wl_time_"), WaitingListFlow.choosing_time)
async def process_wl_time(callback: CallbackQuery, state: FSMContext):
    time_pref = callback.data.split("_")[2] # 'morning', 'afternoon', 'evening', 'any'
    
    data = await state.get_data()
    fmt = data['wl_format']
    days = data['wl_days']
    
    await db.add_to_waiting_list(callback.from_user.id, fmt, days, time_pref)
    
    # Text translation for user
    fmt_ru = "Онлайн" if fmt == 'online' else "Очно" if fmt == 'offline' else "Любой"
    days_ru = "Будни" if days == 'weekdays' else "Выходные" if days == 'weekends' else "Любые дни"
    time_ru = "Утро" if time_pref == 'morning' else "День" if time_pref == 'afternoon' else "Вечер" if time_pref == 'evening' else "Любое время"
    
    text = (
        "✅ <b>Вы успешно добавлены в лист ожидания!</b>\n\n"
        "📝 <b>Ваши пожелания:</b>\n"
        f"📹 Формат: {fmt_ru}\n"
        f"📅 Дни: {days_ru}\n"
        f"⏰ Время: {time_ru}\n\n"
        "Мы свяжемся с вами в этом чате, как только психолог предложит вам подходящий слот!"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await state.clear()
    await callback.answer()

# --- Waiting List Offer Booking ---
@router.callback_query(F.data.startswith("wl_offer_book_"))
async def process_wl_offer_book(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split("_")[3])
    slot = await db.get_slot_by_id(slot_id)
    
    if not slot or slot['is_booked']:
        await callback.message.edit_text("К сожалению, это время уже забронировано другим клиентом.")
        await callback.answer()
        return
        
    psych = await db.get_first_psychologist()
    session_types = await db.get_session_types(psych['telegram_id'])
    
    # Filter session types to match slot format
    matching_types = [st for st in session_types if st['format'].lower() == slot['format'].lower()]
    
    if not matching_types:
        await callback.message.edit_text("К сожалению, у психолога нет видов сессий, подходящих под формат этого слота.")
        await callback.answer()
        return
        
    await state.clear()
    await state.update_data(slot_id=slot_id)
    
    await callback.message.edit_text("Выберите тип сессии для записи:", reply_markup=kb.session_types_keyboard(matching_types))
    await state.set_state(BookingFlow.choosing_session_type)
    await callback.answer()

@router.callback_query(F.data.startswith("wl_offer_decline_"))
async def process_wl_offer_decline(callback: CallbackQuery):
    await callback.message.edit_text("Вы отказались от предложенного времени. Мы продолжим искать для вас удобные слоты!")
    await callback.answer()
