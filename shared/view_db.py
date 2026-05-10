import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "psy_bot.db"))

def view_database():
    if not os.path.exists(DB_PATH):
        print(f"Файл {DB_PATH} не найден. Сначала запустите бота!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=== ТАБЛИЦА users (Пользователи) ===")
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    for u in users:
        print(u)
    if not users: print("Пусто\n")
    else: print()

    print("=== ТАБЛИЦА psychologists (Психологи) ===")
    cursor.execute("SELECT * FROM psychologists")
    psychs = cursor.fetchall()
    for p in psychs:
        print(p)
    if not psychs: print("Пусто\n")
    else: print()

    print("=== ТАБЛИЦА slots (Доступные слоты) ===")
    cursor.execute("SELECT * FROM slots")
    slots = cursor.fetchall()
    for s in slots:
        # s is (id, psych_id, datetime, is_booked)
        print(s)
    if not slots: print("Пусто\n")
    else: print()

    print("=== ТАБЛИЦА appointments (Записи клиентов) ===")
    cursor.execute("SELECT * FROM appointments")
    apps = cursor.fetchall()
    for a in apps:
        print(a)
    if not apps: print("Пусто\n")
    else: print()

    conn.close()

if __name__ == "__main__":
    view_database()
