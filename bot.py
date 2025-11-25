import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
from simpledb import json_db
from database import db

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv("BOT_TOKEN")  # Укажи токен через Railway Secret

# ================= Команды ================= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }

    # сохраняем в MySQL и JSON
    db.add_user(user_data)
    json_db.add_user(user_data)

    welcome_text = f"👋 Приветствую, {user.first_name}!\nДобро пожаловать в элитное сообщество трейдеров!"

    keyboard = [[InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# ================ Обработка кнопок ================= #
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "vip_benefits":
        await show_vip_benefits(query)
    elif data == "has_broker":
        await show_has_broker_options(query)
    elif data == "completed_registration":
        await show_completed_registration(query, context)
    elif data == "make_payment":
        await show_payment_instructions(query)
    elif data == "back_to_start":
        await start(update, context)

async def show_vip_benefits(query):
    vip_text = """🎯 *Преимущества VIP:*
⭐ Копирование сделок по золоту
⭐ Методы торговли
⭐ Поддержка 1:1
💎 Зарегистрируйте торговый счет: https://nmofficialru.com/o2o7sqk1265d
💰 Минимальный депозит: 400$"""
    keyboard = [
        [InlineKeyboardButton("1️⃣ У меня есть брокер и я не хочу его менять", callback_data="has_broker")],
        [InlineKeyboardButton("2️⃣ Я сделал регистрацию Готово✅", callback_data="completed_registration")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(vip_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_has_broker_options(query):
    broker_text = """📈 VIP группа Скальпинг Золото 🥇
💵 1 мес/150$, 3 мес/300$, 1 год/500$"""
    keyboard = [
        [InlineKeyboardButton("💳 Хочу сделать оплату ✅", callback_data="make_payment")],
        [InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(broker_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_payment_instructions(query):
    payment_text = """💳 Для оплаты напишите менеджеру @Skalpingx"""
    keyboard = [
        [InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/Skalpingx")],
        [InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="has_broker")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(payment_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_completed_registration(query, context):
    registration_text = """После регистрации отправьте мне:
✅ Полное имя
✅ Номер счета
✅ Размер капитала"""
    keyboard = [[InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(registration_text, reply_markup=reply_markup)

    await context.bot.send_message(chat_id=query.message.chat_id,
                                   text=f"Привет, {query.from_user.first_name}, место зарезервировано на 24 часа!")

    context.user_data['awaiting_registration_data'] = True

# ================== Обработка сообщений ================== #
async def handle_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get('awaiting_registration_data'):
        # сохраняем и в MySQL, и в JSON
        db.save_registration_data(user_id, text)
        json_db.save_registration_data(user_id, text)
        context.user_data['awaiting_registration_data'] = False

        confirmation_text = "✅ Данные получены! Менеджер свяжется с вами."
        await update.message.reply_text(confirmation_text)
    else:
        await update.message.reply_text("🤖 Я бот для VIP сигналов по золоту. Используйте кнопки меню.")

# ================= Запуск ================= #
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_data))

    print("🟢 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
