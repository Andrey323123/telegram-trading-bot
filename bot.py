import os
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from database import db

# Логирование
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(TOKEN)
app = Flask(__name__)

# Создаём dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)

# ---------------------------------------------------------------------
#                            ОБРАБОТЧИКИ
# ---------------------------------------------------------------------

def start(update, context):
    user = update.effective_user

    db.add_user({
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name
    })

    welcome = f"👋 Приветствую, {user.first_name}!\n\n" \
              f"Добро пожаловать в элитное сообщество трейдеров!"

    keyboard = [
        [InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]
    ]
    update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))


def vip_benefits(update, context):
    q = update.callback_query
    q.answer()

    text = """🎯 *Преимущества VIP:*

⭐ 3–7 сигналов о сделках по золоту ежедневно  
⭐ Внедрение секретных методов торговли  
⭐ Персональная поддержка 1:1  

💎 Для доступа к VIP необходимо зарегистрировать торговый счёт:

https://nmofficialru.com/o2o7sqk1265d

И пополнить его минимум на 400$.
"""

    keyboard = [
        [InlineKeyboardButton("У меня есть брокер", callback_data="has_broker")],
        [InlineKeyboardButton("Я зарегистрировался", callback_data="completed_registration")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_start")]
    ]

    q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def has_broker(update, context):
    q = update.callback_query
    q.answer()

    text = """📈 *VIP группа Скальпинг Золото*

💵 *Цены:*
1 месяц — 150$
3 месяца — 300$
1 год — 500$
Пожизненно — 1000$
"""

    keyboard = [
        [InlineKeyboardButton("💳 Хочу оплатить", callback_data="make_payment")],
        [InlineKeyboardButton("⬅ Назад", callback_data="vip_benefits")]
    ]

    q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def make_payment(update, context):
    q = update.callback_query
    q.answer()

    text = """💳 *Для оплаты пишите менеджеру:*

👉 @Skalpingx

Укажите тариф, и получите реквизиты для оплаты.
"""

    keyboard = [
        [InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/Skalpingx")],
        [InlineKeyboardButton("⬅ Назад", callback_data="has_broker")]
    ]

    q.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


def completed_registration(update, context):
    q = update.callback_query
    q.answer()
    user = update.effective_user

    text = """После регистрации брокера отправьте:

✅ Полное имя  
✅ Номер торгового счёта  
✅ Размер капитала  
"""

    q.edit_message_text(text)

    bot.send_message(user.id, f"Привет, {user.first_name}! Я зарезервировал для тебя место на 24 часа ❤️‍🔥")

    context.user_data["await_reg"] = True


def text_handler(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    if context.user_data.get("await_reg"):
        db.save_registration_data(user_id, text)
        context.user_data["await_reg"] = False

        update.message.reply_text(
            "✅ Спасибо! Данные получены.\nМенеджер свяжется с вами в течение 15 минут."
        )
    else:
        update.message.reply_text(
            "🤖 Используйте кнопки меню.\n"
            "Для связи с менеджером — @Skalpingx"
        )


def button_router(update, context):
    data = update.callback_query.data

    if data == "vip_benefits":
        vip_benefits(update, context)

    elif data == "has_broker":
        has_broker(update, context)

    elif data == "make_payment":
        make_payment(update, context)

    elif data == "completed_registration":
        completed_registration(update, context)

    elif data == "back_start":
        start(update, context)


# ---------------------------------------------------------------------
#                         РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
# ---------------------------------------------------------------------

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CallbackQueryHandler(button_router))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

# ---------------------------------------------------------------------
#                         WEBHOOK ДЛЯ RAILWAY
# ---------------------------------------------------------------------

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def index():
    bot.delete_webhook()
    bot.set_webhook(f"{WEBHOOK_URL}/webhook/{TOKEN}")
    return "Webhook установлен!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
