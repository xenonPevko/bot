import sqlite3
from datetime import datetime

DB_NAME = "navigator_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            selected_tariff TEXT,
            paid INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица для отслеживания тегов/этапов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_tags (
            user_id INTEGER,
            tag TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, tag)
        )
    ''')
    
    # Таблица для запросов в поддержку
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, email, selected_tariff, paid FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def save_user(user_id, name=None, email=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    existing = get_user(user_id)
    if existing:
        if name:
            cursor.execute("UPDATE users SET name = ? WHERE user_id = ?", (name, user_id))
        if email:
            cursor.execute("UPDATE users SET email = ? WHERE user_id = ?", (email, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, name, email) VALUES (?, ?, ?)", (user_id, name, email))
    
    conn.commit()
    conn.close()

def update_user_tariff(user_id, tariff):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET selected_tariff = ? WHERE user_id = ?", (tariff, user_id))
    conn.commit()
    conn.close()

def mark_paid(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET paid = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_tag(user_id, tag):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO user_tags (user_id, tag) VALUES (?, ?)", (user_id, tag))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Тег уже есть
    conn.close()

def has_tag(user_id, tag):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM user_tags WHERE user_id = ? AND tag = ?", (user_id, tag))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_support_request(user_id, message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO support_requests (user_id, message) VALUES (?, ?)", (user_id, message))
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    return request_id