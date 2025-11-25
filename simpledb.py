import json
import os
from datetime import datetime
import logging

class SimpleDB:
    def __init__(self):
        self.users_file = 'users.json'
        self._ensure_files_exist()

    def _ensure_files_exist(self):
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _load_data(self):
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки {self.users_file}: {e}")
            return []

    def _save_data(self, data):
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Ошибка сохранения {self.users_file}: {e}")

    def add_user(self, user_data):
        users = self._load_data()
        if not any(u.get('user_id') == user_data.get('user_id') for u in users):
            user_data['created_at'] = datetime.now().isoformat()
            users.append(user_data)
            self._save_data(users)
            logging.info(f"✅ Добавлен пользователь: {user_data.get('user_id')}")
            return True
        return False

    def save_registration_data(self, user_id, data):
        users = self._load_data()
        for user in users:
            if user.get('user_id') == user_id:
                user['registration_data'] = data
                user['registration_date'] = datetime.now().isoformat()
                break
        self._save_data(users)
        logging.info(f"💾 Сохранены данные регистрации для: {user_id}")

# глобальный экземпляр JSON
json_db = SimpleDB()
