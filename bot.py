# bot.py
import logging
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токен из переменных окружения Railway
BOT_TOKEN = os.getenv('BOT_TOKEN', '8288540260:AAF5Mf1U0QU-BHLY7dvhgvBO-wafexMZUaI')

class SimpleDB:
    def __init__(self):
        self.users_file = 'users.json'
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Создаем файлы если их нет"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_data(self, filename):
        """Загружаем данные из файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка загрузки {filename}: {e}")
            return []
    
    def _save_data(self, filename, data):
        """Сохраняем данные в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Ошибка сохранения {filename}: {e}")
    
    def add_user(self, user_data):
        """Добавляем пользователя"""
        users = self._load_data(self.users_file)
        
        # Проверяем нет ли уже такого пользователя
        user_exists = any(user.get('user_id') == user_data.get('user_id') for user in users)
        
        if not user_exists:
            user_data['created_at'] = datetime.now().isoformat()
            users.append(user_data)
            self._save_data(self.users_file, users)
            logging.info(f"✅ Добавлен пользователь: {user_data.get('user_id')}")
            return True
        return False
    
    def save_registration_data(self, user_id, data):
        """Сохраняем данные регистрации"""
        users = self._load_data(self.users_file)
        
        for user in users:
            if user.get('user_id') == user_id:
                user['registration_data'] = data
                user['registration_date'] = datetime.now().isoformat()
                break
        
        self._save_data(self.users_file, users)
        logging.info(f"💾 Сохранены данные регистрации для: {user_id}")

# Создаем экземпляр базы данных
db = SimpleDB()

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    db.add_user(user_data)
    
    welcome_text = f"👋 Приветствую, {user.first_name}!\n\nДобро пожаловать в элитное сообщество трейдеров!\n\nЯ помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
    
    keyboard = [[InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_text, reply_markup=reply_markup)

def show_vip_benefits(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    vip_text = """🎯 *Преимущества VIP:*

⭐ *Копирование сделок по золоту*: получайте от 3 до 7 ежедневных выигрышных сигналов по золоту

⭐ *Методы торговли* - Внедрение наших секретных методов торговли в вашу игру🤫

⭐ *Поддержка 1:1*: наслаждайтесь персонализированной поддержкой

———————————————————

💎 *Зарегистрируйте торговый счет, чтобы присоединиться к VIP прямо сейчас‼*           

https://nmofficialru.com/o2o7sqk1265d                         
———————————————————

💰 *Сделайте пополнение счета минимум от 400$*"""
    
    keyboard = [
        [InlineKeyboardButton("1️⃣ У меня есть брокер и я не хочу его менять", callback_data="has_broker")],
        [InlineKeyboardButton("2️⃣ Я сделал регистрацию Готово✅", callback_data="completed_registration")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(vip_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_has_broker_options(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    broker_text = """📈 *VIP группа Скальпинг Золото* 🥇 3-7 сигналов в день 

💵 *Цена:*

1 месяц / 150$

3 месяца / 300$

1 год / 500$

🎉🎁План на всю жизнь 1000$"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Хочу сделать оплату ✅", callback_data="make_payment")],
        [InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(broker_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_payment_instructions(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    payment_text = """💳 *Для оформления оплаты:*

Напишите мне в личные сообщения:
👉 @Skalpingx

*Укажите в сообщении:*
- Выбранный тариф (1 месяц, 3 месяца, год или план на всю жизнь)

Я отвечу в течение 5-10 минут с реквизитами для оплаты и инструкциями!"""
    
    keyboard = [
        [InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/Skalpingx")],
        [InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="has_broker")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(payment_text, reply_markup=reply_markup, parse_mode='Markdown')

def show_completed_registration(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = update.effective_user
    
    # Первое сообщение с инструкциями
    registration_text = """После регистрации отправьте мне следующую информацию:

✅Полное Имя
✅Номер счета  
✅Размер капитала"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(registration_text, reply_markup=reply_markup)
    
    # Второе сообщение с информацией о резервировании места
    reservation_text = f"Привет, {user.first_name}, просто хочу сообщить тебе, что я зарезервирую для тебя бесплатное место на ближайшие 24 часа!"
    context.bot.send_message(chat_id=query.message.chat_id, text=reservation_text)
    
    context.user_data['awaiting_registration_data'] = True

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    
    if data == "vip_benefits":
        show_vip_benefits(update, context)
    elif data == "has_broker":
        show_has_broker_options(update, context)
    elif data == "completed_registration":
        show_completed_registration(update, context)
    elif data == "make_payment":
        show_payment_instructions(update, context)
    elif data == "back_to_start":
        start(update, context)

def handle_user_data(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data_text = update.message.text
    
    if context.user_data.get('awaiting_registration_data'):
        db.save_registration_data(user_id, user_data_text)
        context.user_data['awaiting_registration_data'] = False
        
        confirmation_text = """✅ *Спасибо! Ваши данные получены!*

Наш менеджер свяжется с вами в течение 15 минут для подтверждения и подключения к VIP сигналам.

⏳ *Ожидайте, пожалуйста!*

Мы зарезервировали для вас место на 24 часа! 🎉"""
        update.message.reply_text(confirmation_text, parse_mode='Markdown')
    else:
        response_text = "🤖 Я бот для подключения к VIP сигналам по золоту.\n\nИспользуйте кнопки меню для навигации или напишите @Skalpingx для связи с менеджером."
        update.message.reply_text(response_text)

def main():
    try:
        # Создаем updater
        updater = Updater(BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        
        # Добавляем обработчики
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CallbackQueryHandler(button_handler))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_data))
        
        print("✅ База данных готова (JSON файлы)")
        print("🟢 Бот запущен и готов к работе!")
        print("🔍 Найдите бота в Telegram и отправьте /start")
        print("👨‍💼 Менеджер: @Skalpingx")
        print("💾 Данные сохраняются в users.json")
        print("\nДля остановки нажмите Ctrl+C")
        
        # Запускаем бота
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        print(f"🔴 Критическая ошибка запуска: {e}")

if __name__ == "__main__":
    main()
