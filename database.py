# database.py
import sqlite3
import logging
from datetime import datetime, timedelta
import os
from contextlib import contextmanager

class Database:
    def __init__(self):
        self.db_path = os.getenv('DB_PATH', 'sales_bot.db')
    
    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            yield connection
        except Exception as e:
            logging.error(f"Ошибка подключения к SQLite: {e}")
            raise
        finally:
            if connection:
                connection.close()
    
    def create_tables(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE NOT NULL,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        phone TEXT,
                        email TEXT,
                        status TEXT DEFAULT 'new',
                        registration_data TEXT,
                        last_reminder DATETIME,
                        reminders_sent INTEGER DEFAULT 0,
                        source TEXT DEFAULT 'start_command',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        product_name TEXT NOT NULL,
                        amount REAL,
                        status TEXT DEFAULT 'pending',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        reminder_type TEXT NOT NULL,
                        scheduled_at DATETIME NOT NULL,
                        sent BOOLEAN DEFAULT FALSE,
                        sent_at DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                conn.commit()
                logging.info("✅ SQLite таблицы созданы/проверены")
                
        except Exception as e:
            logging.error(f"Ошибка создания таблиц: {e}")
    
    def add_user(self, user_data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO users (user_id, username, first_name, last_name, status, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    updated_at = CURRENT_TIMESTAMP
                """
                
                cursor.execute(query, (
                    user_data['user_id'],
                    user_data['username'],
                    user_data['first_name'],
                    user_data['last_name'],
                    'new',
                    user_data.get('source', 'start_command')
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logging.error(f"Ошибка добавления пользователя: {e}")
            return None
    
    def log_interaction(self, user_id, action, details=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "INSERT INTO interactions (user_id, action, details) VALUES (?, ?, ?)"
                cursor.execute(query, (user_id, action, details))
                conn.commit()
                
        except Exception as e:
            logging.error(f"Ошибка логирования взаимодействия: {e}")
    
    def update_user_status(self, user_id, status):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE users SET status = ? WHERE user_id = ?"
                cursor.execute(query, (status, user_id))
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка обновления статуса: {e}")
    
    def save_registration_data(self, user_id, registration_data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE users SET registration_data = ?, status = 'waiting_verification' WHERE user_id = ?"
                cursor.execute(query, (registration_data, user_id))
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка сохранения данных регистрации: {e}")
    
    def get_user(self, user_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM users WHERE user_id = ?"
                cursor.execute(query, (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logging.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def schedule_reminder(self, user_id, reminder_type, hours_from_now):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                scheduled_at = datetime.now() + timedelta(hours=hours_from_now)
                query = "INSERT INTO reminders (user_id, reminder_type, scheduled_at) VALUES (?, ?, ?)"
                cursor.execute(query, (user_id, reminder_type, scheduled_at))
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка планирования напоминания: {e}")
    
    def get_pending_reminders(self):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT r.*, u.first_name, u.username 
                    FROM reminders r 
                    JOIN users u ON r.user_id = u.user_id 
                    WHERE r.sent = 0 AND r.scheduled_at <= datetime('now')
                """
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logging.error(f"Ошибка получения напоминаний: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE reminders SET sent = 1, sent_at = datetime('now') WHERE id = ?"
                cursor.execute(query, (reminder_id,))
                conn.commit()
        except Exception as e:
            logging.error(f"Ошибка отметки напоминания: {e}")

# Глобальный экземпляр базы данных
db = Database()
