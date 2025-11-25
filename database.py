# database.py
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        # Конфигурация для Railway
        if os.getenv('RAILWAY_ENVIRONMENT'):
            self.config = {
                'host': os.getenv('MYSQLHOST', 'localhost'),
                'database': os.getenv('MYSQLDATABASE', 'telegram_sales_funnel'),
                'user': os.getenv('MYSQLUSER', 'root'),
                'password': os.getenv('MYSQLPASSWORD', '111111'),
                'port': os.getenv('MYSQLPORT', '3306'),
                'charset': 'utf8mb4',
                'connect_timeout': 30
            }
        else:
            # Локальная конфигурация
            self.config = {
                'host': 'localhost',
                'database': 'telegram_sales_funnel',
                'user': 'root',
                'password': '111111',
                'charset': 'utf8mb4'
            }
    
    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            yield connection
        except Error as e:
            logging.error(f"Ошибка подключения к MySQL: {e}")
            safe_config = self.config.copy()
            safe_config['password'] = '***'
            logging.error(f"Конфигурация БД: {safe_config}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(100),
                        first_name VARCHAR(100),
                        last_name VARCHAR(100),
                        phone VARCHAR(20),
                        email VARCHAR(100),
                        status ENUM('new', 'lead', 'waiting_verification', 'customer', 'rejected') DEFAULT 'new',
                        registration_data TEXT,
                        last_reminder DATETIME,
                        reminders_sent INT DEFAULT 0,
                        source VARCHAR(100) DEFAULT 'start_command',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        action VARCHAR(100) NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS purchases (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        product_name VARCHAR(200) NOT NULL,
                        amount DECIMAL(10,2),
                        status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        reminder_type VARCHAR(50) NOT NULL,
                        scheduled_at DATETIME NOT NULL,
                        sent BOOLEAN DEFAULT FALSE,
                        sent_at DATETIME,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                """)
                
                conn.commit()
                logging.info("✅ Таблицы успешно созданы/проверены")
                
        except Error as e:
            logging.error(f"Ошибка создания таблиц: {e}")
    
    def add_user(self, user_data):
        """Добавление нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO users (user_id, username, first_name, last_name, status, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name),
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
                
        except Error as e:
            logging.error(f"Ошибка добавления пользователя: {e}")
            return None
    
    def log_interaction(self, user_id, action, details=None):
        """Логирование взаимодействия с пользователем"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    INSERT INTO interactions (user_id, action, details)
                    VALUES (%s, %s, %s)
                """
                
                cursor.execute(query, (user_id, action, details))
                conn.commit()
                
        except Error as e:
            logging.error(f"Ошибка логирования взаимодействия: {e}")
    
    def update_user_status(self, user_id, status):
        """Обновление статуса пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "UPDATE users SET status = %s WHERE user_id = %s"
                cursor.execute(query, (status, user_id))
                conn.commit()
                
        except Error as e:
            logging.error(f"Ошибка обновления статуса: {e}")
    
    def save_registration_data(self, user_id, registration_data):
        """Сохранение данных регистрации пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "UPDATE users SET registration_data = %s, status = 'waiting_verification' WHERE user_id = %s"
                cursor.execute(query, (registration_data, user_id))
                conn.commit()
                
        except Error as e:
            logging.error(f"Ошибка сохранения данных регистрации: {e}")
    
    def get_user(self, user_id):
        """Получение данных пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                query = "SELECT * FROM users WHERE user_id = %s"
                cursor.execute(query, (user_id,))
                return cursor.fetchone()
                
        except Error as e:
            logging.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def schedule_reminder(self, user_id, reminder_type, hours_from_now):
        """Планирование напоминания"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                scheduled_at = datetime.now() + timedelta(hours=hours_from_now)
                query = """
                    INSERT INTO reminders (user_id, reminder_type, scheduled_at)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(query, (user_id, reminder_type, scheduled_at))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка планирования напоминания: {e}")
    
    def get_pending_reminders(self):
        """Получение ожидающих напоминаний"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                query = """
                    SELECT r.*, u.first_name, u.username 
                    FROM reminders r 
                    JOIN users u ON r.user_id = u.user_id 
                    WHERE r.sent = FALSE AND r.scheduled_at <= NOW()
                """
                cursor.execute(query)
                return cursor.fetchall()
        except Error as e:
            logging.error(f"Ошибка получения напоминаний: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id):
        """Отметка напоминания как отправленного"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE reminders SET sent = TRUE, sent_at = NOW() WHERE id = %s"
                cursor.execute(query, (reminder_id,))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка отметки напоминания: {e}")

# Глобальный экземпляр базы данных
db = Database()
