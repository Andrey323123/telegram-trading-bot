# database.py
import sqlite3
import logging
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='bot_database.db'):
        self.db_path = db_path
        self.conn = None
        self.connect()
    
    def connect(self):
        """Подключаемся к базе данных"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logger.info("✅ Подключение к SQLite установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к SQLite: {e}")
    
    def create_tables(self):
        """Создаем таблицы если их нет"""
        try:
            cursor = self.conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    source TEXT,
                    registration_data TEXT,
                    registration_date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица взаимодействий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    data TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица напоминаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    reminder_type TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    sent BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            logger.info("✅ SQLite таблицы созданы/проверены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
    
    def add_user(self, user_data):
        """Добавляем пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, first_name, last_name, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('source', 'start_command'),
                datetime.now().isoformat()
            ))
            
            is_new = cursor.rowcount > 0
            self.conn.commit()
            
            if is_new:
                logger.info(f"✅ Добавлен новый пользователь: {user_data['user_id']}")
            else:
                logger.info(f"ℹ️ Пользователь уже существует: {user_data['user_id']}")
                
            return is_new
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления пользователя: {e}")
            return False
    
    def log_interaction(self, user_id, action, data=None):
        """Логируем взаимодействие"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO interactions (user_id, action, data, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (user_id, action, data, datetime.now().isoformat()))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка логирования взаимодействия: {e}")
    
    def save_registration_data(self, user_id, data):
        """Сохраняем данные регистрации"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET registration_data = ?, registration_date = ?
                WHERE user_id = ?
            ''', (data, datetime.now().isoformat(), user_id))
            self.conn.commit()
            logger.info(f"💾 Сохранены данные регистрации для: {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных регистрации: {e}")
    
    def schedule_reminder(self, user_id, reminder_type, hours_later):
        """Планируем напоминание"""
        try:
            scheduled_time = datetime.now() + timedelta(hours=hours_later)
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (user_id, reminder_type, scheduled_time)
                VALUES (?, ?, ?)
            ''', (user_id, reminder_type, scheduled_time.isoformat()))
            self.conn.commit()
            logger.info(f"⏰ Запланировано напоминание {reminder_type} для {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка планирования напоминания: {e}")
    
    def get_pending_reminders(self):
        """Получаем ожидающие напоминания"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT r.*, u.first_name 
                FROM reminders r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.sent = FALSE AND r.scheduled_time <= ?
            ''', (datetime.now().isoformat(),))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения напоминаний: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id):
        """Отмечаем напоминание как отправленное"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE reminders SET sent = TRUE WHERE id = ?
            ''', (reminder_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"❌ Ошибка отметки напоминания: {e}")
    
    def get_user_interactions_count(self, user_id):
        """Получаем количество взаимодействий пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM interactions 
                WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ Ошибка получения количества взаимодействий: {e}")
            return 0
    
    def check_user_exists(self, user_id):
        """Проверяет существование пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"❌ Ошибка проверки пользователя: {e}")
            return False

    def get_today_stats(self, date):
        """Получаем статистику за сегодня"""
        try:
            cursor = self.conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Новые пользователи за сегодня
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE DATE(created_at) = DATE(?)
            ''', (date,))
            new_users = cursor.fetchone()[0]
            
            # Всего действий за сегодня
            cursor.execute('''
                SELECT COUNT(*) FROM interactions 
                WHERE DATE(timestamp) = DATE(?)
            ''', (date,))
            total_actions = cursor.fetchone()[0]
            
            # Топ действий за сегодня
            cursor.execute('''
                SELECT action, COUNT(*) as count 
                FROM interactions 
                WHERE DATE(timestamp) = DATE(?)
                GROUP BY action 
                ORDER BY count DESC
            ''', (date,))
            top_actions = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Последние активности
            cursor.execute('''
                SELECT i.*, u.first_name, u.username 
                FROM interactions i
                LEFT JOIN users u ON i.user_id = u.user_id
                WHERE DATE(i.timestamp) = DATE(?)
                ORDER BY i.timestamp DESC
                LIMIT 10
            ''', (date,))
            recent_activities = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_users': total_users,
                'new_users': new_users,
                'total_actions': total_actions,
                'top_actions': top_actions,
                'recent_activities': recent_activities
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_users': 0,
                'new_users': 0,
                'total_actions': 0,
                'top_actions': [],
                'recent_activities': []
            }

    def get_user_today_stats(self, user_id, date):
        """Получаем статистику пользователя за сегодня"""
        try:
            cursor = self.conn.cursor()
            
            # Информация о пользователе
            cursor.execute('''
                SELECT first_name, username FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            user_row = cursor.fetchone()
            
            if not user_row:
                return None
            
            user_info = {
                'first_name': user_row[0],
                'username': user_row[1]
            }
            
            # Всего действий пользователя за сегодня
            cursor.execute('''
                SELECT COUNT(*) FROM interactions 
                WHERE user_id = ? AND DATE(timestamp) = DATE(?)
            ''', (user_id, date))
            total_actions = cursor.fetchone()[0]
            
            # Действия пользователя за сегодня
            cursor.execute('''
                SELECT action, data, timestamp 
                FROM interactions 
                WHERE user_id = ? AND DATE(timestamp) = DATE(?)
                ORDER BY timestamp
            ''', (user_id, date))
            actions = [dict(row) for row in cursor.fetchall()]
            
            return {
                'user_info': user_info,
                'total_actions': total_actions,
                'actions': actions
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики пользователя: {e}")
            return None

    def get_new_users_today(self, date):
        """Получаем новых пользователей за сегодня"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT user_id, first_name, username, created_at 
                FROM users 
                WHERE DATE(created_at) = DATE(?)
                ORDER BY created_at DESC
            ''', (date,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения новых пользователей: {e}")
            return []

# Создаем глобальный экземпляр базы данных
db = Database()
