# bot.py
import logging
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токен из переменных окружения Railway
BOT_TOKEN = os.getenv('BOT_TOKEN', '8288540260:AAF5Mf1U0QU-BHLY7dvhgvBO-wafexMZUaI')

async def send_reminders(update: Update):
    """Умные напоминания (30 часов и 72 часа)"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id
        first_name = user.first_name or "друг"
        
        # Первое напоминание через 30 часов
        await asyncio.sleep(108000)  # 30 часов в секундах
        await update.get_bot().send_message(
            chat_id=chat_id,
            text=f"👋 Привет, {first_name}! Я зарезервировал одно место в VIP, жду ответа 🙏"
        )
        
        # Второе напоминание через 72 часа
        await asyncio.sleep(151200)  # +42 часа = 72 часа от старта
        await update.get_bot().send_message(
            chat_id=chat_id,
            text=f"🤝 Привет, {first_name}! Я все еще держу место для тебя, отпишись как будешь готов 🤝"
        )
            
    except Exception as e:
        print(f"Ошибка в напоминаниях: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    db.add_user(user_data)
    db.log_interaction(user.id, 'start_command')
    
    welcome_text = f"👋 Приветствую, {user.first_name}!\n\nДобро пожаловать в элитное сообщество трейдеров!\n\nЯ помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
    
    keyboard = [[InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    # Запускаем умные напоминания
    asyncio.create_task(send_reminders(update))

async def show_vip_benefits(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def show_has_broker_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def show_completed_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "vip_benefits":
        await show_vip_benefits(update, context)
    elif data == "has_broker":
        await show_has_broker_options(update, context)
    elif data == "completed_registration":
        await show_completed_registration(update, context)
    elif data == "make_payment":
        await show_payment_instructions(update, context)
    elif data == "back_to_start":
        await start(update, context)

async def handle_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

def main():
    try:
        # Инициализируем базу данных
        from init_db import init_database
        init_database()
        
        # Создаем приложение БЕЗ JobQueue
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_data))
        
        print("✅ База данных готова")
        print("🟢 Бот запущен и готов к работе!")
        print("🔍 Найдите бота в Telegram и отправьте /start")
        print("⏰ Умные напоминания активированы")
        print("⏳ Напоминания: 30ч → 1-е, 72ч → 2-е")
        print("👨‍💼 Менеджер: @Skalpingx")
        print("\nДля остановки нажмите Ctrl+C")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"🔴 Критическая ошибка запуска: {e}")
        print("💡 Проверьте настройки базы данных в Railway")

if __name__ == "__main__":
    main()
