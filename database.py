import os
import mysql.connector
from mysql.connector import Error


class Database:
    def __init__(self):
        self.config = {
            "host": os.getenv("MYSQLHOST"),
            "port": int(os.getenv("MYSQLPORT")),
            "user": os.getenv("MYSQLUSER"),
            "password": os.getenv("MYSQLPASSWORD"),
            "database": os.getenv("MYSQLDATABASE"),
            "charset": "utf8mb4"
        }

        self.create_tables()

    def connect(self):
        return mysql.connector.connect(**self.config)

    def create_tables(self):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT UNIQUE,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    registration_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()

        except Error as e:
            print("Ошибка БД:", e)

    def add_user(self, u):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    first_name = VALUES(first_name),
                    last_name = VALUES(last_name)
            """, (u["user_id"], u["username"], u["first_name"], u["last_name"]))

            conn.commit()
            cursor.close()
            conn.close()

        except Error as e:
            print("Ошибка добавления пользователя:", e)

    def save_registration_data(self, user_id, data):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users
                SET registration_data = %s
                WHERE user_id = %s
            """, (data, user_id))

            conn.commit()
            cursor.close()
            conn.close()

        except Error as e:
            print("Ошибка сохранения данных:", e)


db = Database()
