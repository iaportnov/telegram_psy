import aiosqlite
import os
import datetime

import shutil

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "psy_bot.db"))

async def init_db():
    # Automatically seed the database volume with the packaged DB if it doesn't exist yet
    default_db = os.path.join(os.path.dirname(__file__), "psy_bot.db")
    if DB_PATH != default_db and not os.path.exists(DB_PATH) and os.path.exists(default_db):
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            shutil.copy2(default_db, DB_PATH)
            logging = sys = None
            try:
                import logging
            except ImportError:
                pass
            if logging:
                logging.info(f"Initialized database volume by copying default database to {DB_PATH}")
            else:
                print(f"Initialized database volume by copying default database to {DB_PATH}")
        except Exception as e:
            print(f"Error copying initial database: {e}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                name TEXT NOT NULL,
                age TEXT NOT NULL,
                occupation TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS psychologists (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT,
                experience TEXT,
                education TEXT,
                topics TEXT,
                address_offline TEXT,
                platform_online TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS session_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                name TEXT NOT NULL,
                format TEXT NOT NULL,
                duration INTEGER NOT NULL,
                price INTEGER NOT NULL,
                FOREIGN KEY(psychologist_id) REFERENCES psychologists(telegram_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                psychologist_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                format TEXT NOT NULL,
                is_booked BOOLEAN DEFAULT 0,
                FOREIGN KEY(psychologist_id) REFERENCES psychologists(telegram_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                session_type_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                user_request TEXT,
                reason TEXT,
                FOREIGN KEY(slot_id) REFERENCES slots(id),
                FOREIGN KEY(session_type_id) REFERENCES session_types(id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                is_from_psych INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS waiting_list (
                user_id INTEGER PRIMARY KEY,
                format TEXT NOT NULL,
                preferred_days TEXT NOT NULL,
                preferred_time TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        await db.commit()

# --- Users ---
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id: int, username: str, name: str, age: str, occupation: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, name, age, occupation) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, name, age, occupation)
        )
        await db.commit()

# --- Psychologists ---
async def get_psychologist(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM psychologists WHERE telegram_id = ?", (telegram_id,)) as cursor:
            return await cursor.fetchone()

async def get_first_psychologist():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM psychologists LIMIT 1") as cursor:
            return await cursor.fetchone()

async def update_psychologist(telegram_id: int, data: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        # Enforce single psychologist: delete others if this is a new one
        await db.execute("DELETE FROM psychologists WHERE telegram_id != ?", (telegram_id,))
        # Create if not exists
        await db.execute("INSERT OR IGNORE INTO psychologists (telegram_id) VALUES (?)", (telegram_id,))
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values())
        values.append(telegram_id)
        
        await db.execute(f"UPDATE psychologists SET {set_clause} WHERE telegram_id = ?", values)
        await db.commit()

# --- Session Types ---
async def get_session_types(psychologist_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM session_types WHERE psychologist_id = ?", (psychologist_id,)) as cursor:
            return await cursor.fetchall()

async def get_session_type(session_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM session_types WHERE id = ?", (session_id,)) as cursor:
            return await cursor.fetchone()

async def add_session_type(psychologist_id: int, name: str, format: str, duration: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO session_types (psychologist_id, name, format, duration, price) VALUES (?, ?, ?, ?, ?)",
            (psychologist_id, name, format, duration, price)
        )
        await db.commit()

async def clear_session_types(psychologist_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM session_types WHERE psychologist_id = ?", (psychologist_id,))
        await db.commit()

# --- Slots ---
async def add_slot(psychologist_id: int, date: str, time: str, format: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO slots (psychologist_id, date, time, format, is_booked) VALUES (?, ?, ?, ?, 0)",
            (psychologist_id, date, time, format)
        )
        await db.commit()

async def save_message(sender_id: int, receiver_id: int, text: str, is_from_psych: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (sender_id, receiver_id, text, is_from_psych) VALUES (?, ?, ?, ?)",
            (sender_id, receiver_id, text, 1 if is_from_psych else 0)
        )
        await db.commit()

async def get_available_slots(psychologist_id: int = None):
    # If we have multiple psychologists, we can filter by ID. For now, we can just return all or filter by the first one.
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM slots WHERE is_booked = 0 AND date >= ?"
        params = [datetime.date.today().strftime('%Y-%m-%d')]
        if psychologist_id:
            query += " AND psychologist_id = ?"
            params.append(psychologist_id)
        query += " ORDER BY date ASC, time ASC"
        
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

async def delete_slot(slot_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
        await db.commit()

async def get_all_slots(psychologist_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM slots WHERE psychologist_id = ? ORDER BY date ASC, time ASC", (psychologist_id,)) as cursor:
            return await cursor.fetchall()

async def get_slot_by_id(slot_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM slots WHERE id = ?", (slot_id,)) as cursor:
            return await cursor.fetchone()

# --- Appointments ---
async def create_appointment(user_id: int, slot_id: int, session_type_id: int, user_request: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "INSERT INTO appointments (user_id, slot_id, session_type_id, status, user_request) VALUES (?, ?, ?, 'pending', ?)",
            (user_id, slot_id, session_type_id, user_request)
        ) as cursor:
            appointment_id = cursor.lastrowid
        await db.commit()
        return appointment_id

async def confirm_appointment(appointment_id: int):
    import datetime
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.id, s.psychologist_id, s.date, s.time, st.duration 
            FROM appointments a 
            JOIN slots s ON a.slot_id = s.id 
            JOIN session_types st ON a.session_type_id = st.id
            WHERE a.id = ?
        """, (appointment_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                slot_id = row['id']
                psych_id = row['psychologist_id']
                date = row['date']
                start_time_str = row['time']
                duration_mins = row['duration']
                
                await db.execute("UPDATE appointments SET status = 'confirmed' WHERE id = ?", (appointment_id,))
                await db.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))
                
                # Remove overlapping unbooked slots
                async with db.execute("SELECT id, time FROM slots WHERE psychologist_id = ? AND date = ? AND is_booked = 0", (psych_id, date)) as slots_cursor:
                    other_slots = await slots_cursor.fetchall()
                    start_time = datetime.datetime.strptime(start_time_str, "%H:%M")
                    end_time = start_time + datetime.timedelta(minutes=duration_mins)
                    
                    for os_row in other_slots:
                        os_time = datetime.datetime.strptime(os_row['time'], "%H:%M")
                        # If a slot falls within the booked session time, delete it
                        if start_time <= os_time < end_time:
                            await db.execute("DELETE FROM slots WHERE id = ?", (os_row['id'],))
                            
                await db.commit()

async def prepay_appointment(appointment_id: int):
    import datetime
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT s.id, s.psychologist_id, s.date, s.time, st.duration 
            FROM appointments a 
            JOIN slots s ON a.slot_id = s.id 
            JOIN session_types st ON a.session_type_id = st.id
            WHERE a.id = ?
        """, (appointment_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                slot_id = row['id']
                psych_id = row['psychologist_id']
                date = row['date']
                start_time_str = row['time']
                duration_mins = row['duration']
                
                await db.execute("UPDATE appointments SET status = 'prepaid' WHERE id = ?", (appointment_id,))
                await db.execute("UPDATE slots SET is_booked = 1 WHERE id = ?", (slot_id,))
                
                # Remove overlapping unbooked slots
                async with db.execute("SELECT id, time FROM slots WHERE psychologist_id = ? AND date = ? AND is_booked = 0", (psych_id, date)) as slots_cursor:
                    other_slots = await slots_cursor.fetchall()
                    start_time = datetime.datetime.strptime(start_time_str, "%H:%M")
                    end_time = start_time + datetime.timedelta(minutes=duration_mins)
                    
                    for os_row in other_slots:
                        os_time = datetime.datetime.strptime(os_row['time'], "%H:%M")
                        if start_time <= os_time < end_time:
                            await db.execute("DELETE FROM slots WHERE id = ?", (os_row['id'],))
                            
                await db.commit()

async def cancel_appointment(appointment_id: int, reason: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT slot_id FROM appointments WHERE id = ?", (appointment_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                slot_id = row[0]
                await db.execute("UPDATE appointments SET status = 'cancelled', reason = ? WHERE id = ?", (reason, appointment_id))
                await db.execute("UPDATE slots SET is_booked = 0 WHERE id = ?", (slot_id,))
                await db.commit()

async def get_appointment(appointment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, s.date, s.time, s.format as slot_format, s.psychologist_id, p.name as psych_name, 
                   p.platform_online, p.address_offline,
                   st.name as session_name, st.duration, st.price, st.format as session_format,
                   u.name as user_name, u.username, u.age, u.occupation
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN session_types st ON a.session_type_id = st.id
            LEFT JOIN psychologists p ON s.psychologist_id = p.telegram_id
            JOIN users u ON a.user_id = u.user_id
            WHERE a.id = ?
        """
        async with db.execute(query, (appointment_id,)) as cursor:
            return await cursor.fetchone()

async def get_user_appointments(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, s.date, s.time, s.format as slot_format, p.name as psych_name, st.name as session_name, st.duration, st.price
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN session_types st ON a.session_type_id = st.id
            JOIN psychologists p ON s.psychologist_id = p.telegram_id
            WHERE a.user_id = ? AND a.status IN ('pending', 'confirmed', 'prepaid', 'rescheduled')
            ORDER BY s.date ASC, s.time ASC
        """
        async with db.execute(query, (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_confirmed_appointments_by_date(psychologist_id: int, date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT s.time, st.duration
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN session_types st ON a.session_type_id = st.id
            WHERE s.psychologist_id = ? AND s.date = ? AND a.status IN ('confirmed', 'prepaid')
        """
        async with db.execute(query, (psychologist_id, date)) as cursor:
            return await cursor.fetchall()

async def get_psychologist_appointments(psychologist_id: int, date: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, s.date, s.time, s.format as slot_format, st.name as session_name, st.duration, st.price,
                   u.name as user_name, u.username, u.age, u.occupation,
                   p.platform_online, p.address_offline, p.name as psych_name
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN session_types st ON a.session_type_id = st.id
            JOIN users u ON a.user_id = u.user_id
            LEFT JOIN psychologists p ON s.psychologist_id = p.telegram_id
            WHERE s.psychologist_id = ? AND a.status IN ('confirmed', 'prepaid')
        """
        params = [psychologist_id]
        if date:
            query += " AND s.date = ?"
            params.append(date)
            
        query += " ORDER BY s.date ASC, s.time ASC"
        
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


def format_meeting_card(app: dict, for_psychologist: bool = False) -> str:
    import datetime
    
    if not app:
        app = {}
    elif not isinstance(app, dict):
        try:
            app = dict(app)
        except Exception:
            app = {}
            
    # Extract date & time
    date_val = app.get('date') or '---'
    time_val = app.get('time') or '---'
    duration = app.get('duration') or 0
    
    # 1. Date and Time range formatting
    display_date = "-".join(date_val.split("-")[::-1])
    
    try:
        start_time = datetime.datetime.strptime(time_val, "%H:%M")
        end_time = start_time + datetime.timedelta(minutes=int(duration))
        time_range = f"{time_val} – {end_time.strftime('%H:%M')}"
    except Exception:
        time_range = time_val

    # 2. Format / Location details
    fmt = app.get('session_format') or app.get('slot_format') or "Онлайн"
    location_details = ""
    if fmt.lower() == 'онлайн':
        platform = app.get('platform_online')
        if not platform or not (platform.startswith('http://') or platform.startswith('https://')):
            platform = "https://zoom.us/j/1234567890"
        location_details = f"🔗 <b>Ссылка на Zoom/платформу</b>: <a href='{platform}'>{platform}</a>"
    else:
        addr = app.get('address_offline') or 'Не указан'
        location_details = f"📍 <b>Адрес</b>: {addr}"

    # 3. Payment status
    status = app.get('status') or 'pending'
    if status == 'confirmed':
        payment_status_text = "Оплачено полностью (100%) ✅"
    elif status == 'prepaid':
        payment_status_text = "Внесена предоплата (50%) ⚠️"
    elif status == 'pending':
        payment_status_text = "Ожидает оплаты ⏳"
    elif status == 'cancelled':
        payment_status_text = "Отменена ❌"
    else:
        payment_status_text = f"{status}"

    # 4. Rules
    rules = (
        "⚠️ <b>Правила переноса и отмены сессии</b>:\n"
        "Вы можете бесплатно отменить или перенести встречу не позднее чем за 24 часа до её начала. "
        "При отмене или переносе менее чем за 24 часа оплата не возвращается и сессия считается пройденной."
    )

    # 5. Build card text
    lines = []
    lines.append("📋 <b>ДЕТАЛИ ВСТРЕЧИ</b>")
    lines.append("--------------------------------")
    
    if for_psychologist:
        user_name = app.get('user_name') or 'Клиент'
        username = app.get('username')
        user_contact = f"@{username}" if username else "нет"
        age = app.get('age') or 'не указан'
        occupation = app.get('occupation') or 'не указана'
        request = app.get('user_request')
        
        lines.append(f"👤 <b>Клиент</b>: {user_name} ({user_contact})")
        lines.append(f"🎂 <b>Возраст</b>: {age}")
        lines.append(f"💼 <b>Деятельность</b>: {occupation}")
        if request:
            lines.append(f"📝 <b>Запрос</b>: {request}")
        lines.append("--------------------------------")
    else:
        psych_name = app.get('psych_name') or 'Психолог'
        lines.append(f"🧑‍⚕️ <b>Психолог</b>: {psych_name}")
    
    lines.append(f"📌 <b>Вид сессии</b>: {app.get('session_name') or 'Консультация'}")
    lines.append(f"⏰ <b>Дата и время</b>: {display_date} в {time_range} ({duration} мин)")
    lines.append(f"📹 <b>Формат</b>: {fmt}")
    lines.append(location_details)
    lines.append(f"💰 <b>Стоимость</b>: {app.get('price') or 0} ₽")
    lines.append(f"💳 <b>Статус оплаты</b>: {payment_status_text}")
    lines.append("--------------------------------")
    lines.append(rules)

    return "\n".join(lines)


def generate_gcal_link(app: dict, for_psychologist: bool = False) -> str:
    import datetime
    import urllib.parse
    
    # Convert Row to dict if needed
    if not isinstance(app, dict):
        try:
            app = dict(app)
        except Exception:
            pass
            
    date_val = app.get('date') or '2026-01-01'
    time_val = app.get('time') or '12:00'
    duration = app.get('duration') or 50
    
    try:
        date_obj = datetime.datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M")
        end_obj = date_obj + datetime.timedelta(minutes=int(duration))
    except Exception:
        date_obj = datetime.datetime.now()
        end_obj = date_obj + datetime.timedelta(minutes=50)
        
    start_str = date_obj.strftime("%Y%m%dT%H%M%S")
    end_str = end_obj.strftime("%Y%m%dT%H%M%S")
    
    if for_psychologist:
        user_name = app.get('user_name') or 'Клиент'
        text = urllib.parse.quote(f"Сессия с {user_name}")
        details = urllib.parse.quote(f"Возраст: {app.get('age')}, Деятельность: {app.get('occupation')}")
    else:
        psych_name = app.get('psych_name') or 'Психолог'
        text = urllib.parse.quote(f"Сессия с психологом {psych_name}")
        details = urllib.parse.quote(f"Платформа: {app.get('platform_online') or 'Zoom'}")
        
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={text}&dates={start_str}/{end_str}&details={details}"


# --- Waiting List ---
async def add_to_waiting_list(user_id: int, format_pref: str, days_pref: str, time_pref: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO waiting_list (user_id, format, preferred_days, preferred_time) VALUES (?, ?, ?, ?)",
            (user_id, format_pref, days_pref, time_pref)
        )
        await db.commit()

async def get_waiting_list_entry(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM waiting_list WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def remove_from_waiting_list(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM waiting_list WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_all_waiting_list():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT wl.*, u.name as user_name, u.username, u.age, u.occupation
            FROM waiting_list wl
            JOIN users u ON wl.user_id = u.user_id
            ORDER BY wl.created_at ASC
        """
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def get_matching_waiting_list(slot_id: int):
    slot = await get_slot_by_id(slot_id)
    if not slot:
        return []
        
    slot_date_str = slot['date'] # YYYY-MM-DD
    slot_time_str = slot['time'] # HH:MM
    slot_format = slot['format'].lower() # 'онлайн' or 'очно'
    
    import datetime
    try:
        date_obj = datetime.datetime.strptime(slot_date_str, "%Y-%m-%d")
        is_weekend = date_obj.weekday() in (5, 6)
        slot_days = "weekends" if is_weekend else "weekdays"
    except Exception:
        slot_days = "any"
        
    try:
        time_hour = int(slot_time_str.split(":")[0])
        if 10 <= time_hour < 14:
            slot_time_pref = "morning"
        elif 14 <= time_hour < 18:
            slot_time_pref = "afternoon"
        elif 18 <= time_hour < 22:
            slot_time_pref = "evening"
        else:
            slot_time_pref = "any"
    except Exception:
        slot_time_pref = "any"

    all_entries = await get_all_waiting_list()
    
    matching_entries = []
    for entry in all_entries:
        # Match format
        fmt_pref = entry['format'].lower() # 'online', 'offline', 'any'
        if fmt_pref != 'any':
            if slot_format == 'онлайн' and fmt_pref != 'online':
                continue
            if slot_format == 'очно' and fmt_pref != 'offline':
                continue
                
        # Match days
        days_pref = entry['preferred_days'].lower() # 'weekdays', 'weekends', 'any'
        if days_pref != 'any' and slot_days != 'any':
            if days_pref != slot_days:
                continue
                
        # Match time of day
        time_pref = entry['preferred_time'].lower() # 'morning', 'afternoon', 'evening', 'any'
        if time_pref != 'any' and slot_time_pref != 'any':
            if time_pref != slot_time_pref:
                continue
                
        matching_entries.append(entry)
        
    return matching_entries
