import mysql.connector
from mysql.connector import Error
import os
from contextlib import contextmanager
import logging

class Database:
    def __init__(self):
        self.config = {
            'host': os.getenv('MYSQLHOST', 'localhost'),
            'port': int(os.getenv('MYSQLPORT', '3306')),
            'database': os.getenv('MYSQLDATABASE', 'telegram_sales_funnel'),
            'user': os.getenv('MYSQLUSER', 'root'),
            'password': os.getenv('MYSQLPASSWORD', '111111'),
            'charset': 'utf8mb4'
        }
        print(f"🔧 Настройки БД: {self.config['host']}:{self.config['port']}, база: {self.config['database']}")

    @contextmanager
    def get_connection(self):
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            yield connection
        except Error as e:
            logging.error(f"Ошибка подключения к MySQL: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()

    def create_tables(self):
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
                        status VARCHAR(50) DEFAULT 'new',
                        registration_data TEXT,
                        last_reminder DATETIME,
                        reminders_sent INT DEFAULT 0,
                        source VARCHAR(100) DEFAULT 'start_command',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS interactions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        action VARCHAR(100) NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("✅ Таблицы успешно созданы/проверены")
        except Error as e:
            print(f"❌ Ошибка создания таблиц: {e}")
            raise

    def add_user(self, user_data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    INSERT INTO users (user_id, username, first_name, last_name, status, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        username = VALUES(username),
                        first_name = VALUES(first_name),
                        last_name = VALUES(last_name)
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
                return True
        except Error as e:
            print(f"Ошибка добавления пользователя: {e}")
            return False

    def log_interaction(self, user_id, action, details=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "INSERT INTO interactions (user_id, action, details) VALUES (%s, %s, %s)"
                cursor.execute(query, (user_id, action, details))
                conn.commit()
        except Error as e:
            print(f"Ошибка логирования взаимодействия: {e}")

    def save_registration_data(self, user_id, registration_data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE users SET registration_data = %s, status = 'waiting' WHERE user_id = %s"
                cursor.execute(query, (registration_data, user_id))
                conn.commit()
        except Error as e:
            print(f"Ошибка сохранения данных регистрации: {e}")

# глобальный экземпляр базы
db = Database()
