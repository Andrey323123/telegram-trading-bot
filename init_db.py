# init_db.py
from database import db
import logging

def init_database():
    """Инициализация базы данных - создание таблиц"""
    try:
        db.create_tables()
        print("✅ База данных инициализирована успешно!")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")

if __name__ == "__main__":
    init_database()
