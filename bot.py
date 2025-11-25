# bot_with_reminders.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from contextlib import contextmanager
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Ваш токен
BOT_TOKEN = "8288540260:AAF5Mf1U0QU-BHLY7dvhgvBO-wafexMZUaI"

# Класс для работы с MySQL базой данных
class Database:
    def __init__(self):
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
                        status ENUM('new', 'lead', 'waiting_verification', 'customer', 'rejected') DEFAULT 'new',
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
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reminders (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        reminder_type VARCHAR(50) NOT NULL,
                        scheduled_at DATETIME NOT NULL,
                        sent BOOLEAN DEFAULT FALSE,
                        sent_at DATETIME,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                print("✅ Таблицы базы данных созданы/проверены")
        except Error as e:
            logging.error(f"Ошибка создания таблиц: {e}")
    
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
                return cursor.lastrowid
        except Error as e:
            logging.error(f"Ошибка добавления пользователя: {e}")
            return None
    
    def log_interaction(self, user_id, action, details=None):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "INSERT INTO interactions (user_id, action, details) VALUES (%s, %s, %s)"
                cursor.execute(query, (user_id, action, details))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка логирования взаимодействия: {e}")
    
    def update_user_status(self, user_id, status):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE users SET status = %s WHERE user_id = %s"
                cursor.execute(query, (status, user_id))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка обновления статуса: {e}")
    
    def save_registration_data(self, user_id, registration_data):
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE users SET registration_data = %s, status = 'waiting_verification' WHERE user_id = %s"
                cursor.execute(query, (registration_data, user_id))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка сохранения данных регистрации: {e}")
    
    def schedule_reminder(self, user_id, reminder_type, hours_from_now):
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
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "UPDATE reminders SET sent = TRUE, sent_at = NOW() WHERE id = %s"
                cursor.execute(query, (reminder_id,))
                conn.commit()
        except Error as e:
            logging.error(f"Ошибка отметки напоминания: {e}")

# Создаем экземпляр базы данных
db = Database()

class TradingBot:
    def __init__(self, token):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        self.is_running = False
        
    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_user_data))
        
        # Добавляем job для напоминаний
        self.application.job_queue.run_repeating(
            self.check_and_send_reminders,
            interval=60,  # Проверяем каждую минуту
            first=10      # Первая проверка через 10 секунд
        )
    
    async def check_and_send_reminders(self, context: ContextTypes.DEFAULT_TYPE):
        """Проверка и отправка напоминаний"""
        try:
            reminders = db.get_pending_reminders()
            for reminder in reminders:
                try:
                    user_id = reminder['user_id']
                    reminder_type = reminder['reminder_type']
                    first_name = reminder['first_name']
                    
                    if reminder_type == "30_hours":
                        message = f"👋 Привет, {first_name}! Я зарезервировал одно место в VIP, жду ответа 🙏"
                    elif reminder_type == "72_hours":
                        message = f"🤝 Привет, {first_name}! Я все еще держу место для тебя, отпишись как будешь готов 🤝"
                    else:
                        continue
                    
                    # Отправляем сообщение
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message
                    )
                    
                    # Помечаем как отправленное
                    db.mark_reminder_sent(reminder['id'])
                    db.log_interaction(user_id, f"reminder_sent_{reminder_type}")
                    
                    logging.info(f"Отправлено напоминание {reminder_type} пользователю {user_id}")
                    
                except Exception as e:
                    logging.error(f"Ошибка отправки напоминания {reminder['id']}: {e}")
        except Exception as e:
            logging.error(f"Ошибка в обработчике напоминаний: {e}")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'source': 'start_command'
        }
        db.add_user(user_data)
        db.log_interaction(user.id, 'start_command')
        
        # Планируем напоминания
        db.schedule_reminder(user.id, "30_hours", 30)  # Через 30 часов
        db.schedule_reminder(user.id, "72_hours", 72)  # Через 72 часов
        
        welcome_text = f"👋 Приветствую, {user.first_name}!\n\nДобро пожаловать в элитное сообщество трейдеров!\n\nЯ помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
        
        keyboard = [[InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def show_vip_benefits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db.log_interaction(user_id, 'viewed_vip_benefits')
        
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
        
        if hasattr(update, 'callback_query'):
            await update.callback_query.edit_message_text(vip_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(vip_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_has_broker_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        db.log_interaction(user_id, 'selected_has_broker')
        
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
        await update.callback_query.edit_message_text(broker_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_payment_instructions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = update.effective_user
        db.log_interaction(user_id, 'clicked_make_payment')
        
        payment_text = f"""💳 *Для оформления оплаты:*

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
        await update.callback_query.edit_message_text(payment_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_completed_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = update.effective_user
        db.log_interaction(user_id, 'selected_completed_registration')
        
        # Первое сообщение с инструкциями
        registration_text = """После регистрации отправьте мне следующую информацию:

✅Полное Имя
✅Номер счета  
✅Размер капитала"""
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(registration_text, reply_markup=reply_markup)
        
        # Второе сообщение с информацией о резервировании места
        reservation_text = f"Привет, {user.first_name}, просто хочу сообщить тебе, что я зарезервирую для тебя бесплатное место на ближайшие 24 часа!"
        await update.callback_query.message.reply_text(reservation_text)
        
        context.user_data['awaiting_registration_data'] = True
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data == "vip_benefits":
            await self.show_vip_benefits(update, context)
        elif data == "has_broker":
            await self.show_has_broker_options(update, context)
        elif data == "completed_registration":
            await self.show_completed_registration(update, context)
        elif data == "make_payment":
            await self.show_payment_instructions(update, context)
        elif data == "back_to_start":
            await self.start(update, context)
    
    async def handle_user_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data_text = update.message.text
        
        if context.user_data.get('awaiting_registration_data'):
            db.save_registration_data(user_id, user_data_text)
            db.log_interaction(user_id, 'submitted_registration_data', user_data_text)
            context.user_data['awaiting_registration_data'] = False
            
            confirmation_text = """✅ *Спасибо! Ваши данные получены!*

Наш менеджер свяжется с вами в течение 15 минут для подтверждения и подключения к VIP сигналам.

⏳ *Ожидайте, пожалуйста!*

Мы зарезервировали для вас место на 24 часа! 🎉"""
            await update.message.reply_text(confirmation_text, parse_mode='Markdown')
        else:
            db.log_interaction(user_id, 'sent_message', user_data_text)
            response_text = "🤖 Я бот для подключения к VIP сигналам по золоту.\n\nИспользуйте кнопки меню для навигации или напишите @Skalpingx для связи с менеджером."
            await update.message.reply_text(response_text)
    
    def run(self):
        """Запуск бота"""
        try:
            db.create_tables()
            print("✅ База данных готова")
            
            print("🟢 Бот запущен и готов к работе!")
            print("🔍 Найдите бота в Telegram и отправьте /start")
            print("⏰ Система напоминаний активирована")
            print("⏳ Напоминания: 30ч → 1-е, 72ч → 2-е")
            print("👨‍💼 Менеджер: @Skalpingx")
            print("\nДля остановки нажмите Ctrl+C")
            
            # Простой запуск polling
            self.application.run_polling()
            
        except Exception as e:
            print(f"🔴 Ошибка запуска бота: {e}")

def main():
    bot = TradingBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()