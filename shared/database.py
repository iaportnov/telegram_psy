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
            JOIN psychologists p ON s.psychologist_id = p.telegram_id
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
            WHERE a.user_id = ? AND a.status IN ('pending', 'confirmed', 'rescheduled')
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
            WHERE s.psychologist_id = ? AND s.date = ? AND a.status = 'confirmed'
        """
        async with db.execute(query, (psychologist_id, date)) as cursor:
            return await cursor.fetchall()

async def get_psychologist_appointments(psychologist_id: int, date: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT a.*, s.date, s.time, s.format as slot_format, st.name as session_name, st.duration, st.price,
                   u.name as user_name, u.username, u.age, u.occupation
            FROM appointments a
            JOIN slots s ON a.slot_id = s.id
            JOIN session_types st ON a.session_type_id = st.id
            JOIN users u ON a.user_id = u.user_id
            WHERE s.psychologist_id = ? AND a.status = 'confirmed'
        """
        params = [psychologist_id]
        if date:
            query += " AND s.date = ?"
            params.append(date)
            
        query += " ORDER BY s.date ASC, s.time ASC"
        
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()
