# bot.py — полный рабочий файл для python-telegram-bot v20+ и Railway (Python 3.13+)
import os
import logging
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Попытка импортировать database (ожидается файл database.py с объектом db)
try:
    from database import db
    DB_AVAILABLE = True
except Exception as e:
    db = None
    DB_AVAILABLE = False
    # БД может быть временно недоступна — бот будет логировать ошибки, но работать.
    # В production обязательно подключить MySQL и проверить database.py.
    print(f"[WARN] Database module import failed: {e}")

# ========== CONFIG ==========
TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")
# WEBHOOK_URL должен быть вида https://<your-app>.railway.app
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if WEBHOOK_URL and not WEBHOOK_URL.startswith("http"):
    WEBHOOK_URL = "https://" + WEBHOOK_URL
if WEBHOOK_URL and WEBHOOK_URL.endswith("/"):
    WEBHOOK_URL = WEBHOOK_URL[:-1]

# full webhook endpoint (application will accept POST at /webhook/<TOKEN>)
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_FULL_URL = f"{WEBHOOK_URL}{WEBHOOK_PATH}" if WEBHOOK_URL else None

# Flask app for webhook
app = Flask(__name__)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Telegram application (async)
application = Application.builder().token(TOKEN).build()

# Simple in-memory fallback for user "awaiting registration" state if context.user_data lost
# (prefer using per-chat user_data, but this helps between restarts if no DB)
AWAITING_REGISTRATIONS = {}  # chat_id -> expiry datetime

AWAITING_TIMEOUT = timedelta(hours=24)  # reserved place valid 24h


# ========== Utilities ==========
def mark_awaiting_registration(chat_id: int):
    AWAITING_REGISTRATIONS[chat_id] = datetime.utcnow() + AWAITING_TIMEOUT


def is_awaiting_registration(chat_id: int) -> bool:
    exp = AWAITING_REGISTRATIONS.get(chat_id)
    if not exp:
        return False
    if datetime.utcnow() > exp:
        del AWAITING_REGISTRATIONS[chat_id]
        return False
    return True


async def safe_add_user(user_obj: dict):
    """Try to add user to DB; if DB missing, log and skip."""
    if not DB_AVAILABLE:
        logger.warning("DB not available — skipping add_user")
        return
    try:
        db.add_user(user_obj)
        logger.info(f"User saved to DB: {user_obj.get('user_id')}")
    except Exception as e:
        logger.exception(f"Failed to add user to DB: {e}")


async def safe_save_registration(user_id: int, registration_text: str):
    if not DB_AVAILABLE:
        logger.warning("DB not available — skipping save_registration_data")
        return
    try:
        db.save_registration_data(user_id, registration_text)
        logger.info(f"Registration data saved for {user_id}")
    except Exception as e:
        logger.exception(f"Failed to save registration data: {e}")


# ========== Handlers ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    # Save user to DB (best-effort)
    user_data = {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "source": "start_command"
    }
    await safe_add_user(user_data)

    welcome_text = (
        f"👋 Приветствую, {user.first_name}!\n\n"
        "Добро пожаловать в элитное сообщество трейдеров!\n\n"
        "Я помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
    )
    keyboard = [
        [InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — запуск бота\n/help — помощь\n"
        "Используйте кнопки для навигации по тарифам и оплате."
    )


# Show VIP benefits
async def show_vip_benefits_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    vip_text = (
        "🎯 *Преимущества VIP:*\n\n"
        "⭐ *Копирование сделок по золоту*: получайте от 3 до 7 ежедневных сигналов по золоту\n\n"
        "⭐ *Методы торговли* — внедрение наших секретных методов торговли\n\n"
        "⭐ *Поддержка 1:1*: персональная поддержка\n\n"
        "———————————————————\n\n"
        "💎 *Зарегистрируйте торговый счет, чтобы присоединиться к VIP прямо сейчас‼*\n\n"
        "https://nmofficialru.com/o2o7sqk1265d\n\n"
        "———————————————————\n\n"
        "💰 *Сделайте пополнение счета минимум от 400$*"
    )
    keyboard = [
        [InlineKeyboardButton("1️⃣ У меня есть брокер и я не хочу его менять", callback_data="has_broker")],
        [InlineKeyboardButton("2️⃣ Я сделал регистрацию Готово✅", callback_data="completed_registration")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
    ]
    await query.edit_message_text(text=vip_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# Has broker -> show tariffs
async def show_has_broker_options_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    broker_text = (
        "📈 *VIP группа Скальпинг Золото* 🥇 3-7 сигналов в день\n\n"
        "💵 *Цена:*\n\n"
        "1 месяц / 150$\n\n"
        "3 месяца / 300$\n\n"
        "1 год / 500$\n\n"
        "🎉🎁План на всю жизнь 1000$"
    )
    keyboard = [
        [InlineKeyboardButton("💳 Хочу сделать оплату ✅", callback_data="make_payment")],
        [InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]
    ]
    await q.edit_message_text(text=broker_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# Payment instructions
async def show_payment_instructions_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    payment_text = (
        "💳 *Для оформления оплаты:*\n\n"
        "Напишите мне в личные сообщения:\n👉 @Skalpingx\n\n"
        "*Укажите в сообщении:*\n- Выбранный тариф (1 месяц, 3 месяца, год или план на всю жизнь)\n\n"
        "Я отвечу в течение 5-10 минут с реквизитами для оплаты и инструкциями!"
    )
    keyboard = [
        [InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/Skalpingx")],
        [InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="has_broker")]
    ]
    await q.edit_message_text(text=payment_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# Completed registration flow
async def show_completed_registration_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = update.effective_user
    registration_text = (
        "После регистрации отправьте мне следующую информацию:\n\n"
        "✅ Полное Имя\n"
        "✅ Номер счета\n"
        "✅ Размер капитала"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")]]
    await q.edit_message_text(text=registration_text, reply_markup=InlineKeyboardMarkup(keyboard))

    # send reservation message
    try:
        await context.bot.send_message(chat_id=q.message.chat_id,
                                       text=f"Привет, {user.first_name}, просто хочу сообщить тебе, что я зарезервирую для тебя бесплатное место на ближайшие 24 часа!")
    except Exception:
        # if bot can't message directly to user (e.g., private chat not allowed), ignore
        logger.exception("Could not send reservation DM to the user")

    # mark awaiting for registration both in context.user_data and fallback
    context.user_data['awaiting_registration_data'] = True
    mark_awaiting_registration(q.message.chat_id)


# Back to start -> re-run start content (edit or send new)
async def back_to_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # Simpler to call start flow: edit text with start content
    start_text = "👋 Вернулись в начало."
    keyboard = [[InlineKeyboardButton("🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]]
    await q.edit_message_text(text=start_text, reply_markup=InlineKeyboardMarkup(keyboard))


# Generic callback router
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # map data to handler functions
    routes = {
        "vip_benefits": show_vip_benefits_cb,
        "has_broker": show_has_broker_options_cb,
        "make_payment": show_payment_instructions_cb,
        "completed_registration": show_completed_registration_cb,
        "back_to_start": back_to_start_cb,
    }

    handler = routes.get(data)
    if handler:
        await handler(update, context)
    else:
        # unknown callback: acknowledge
        await query.answer()


# Text messages handler — handles registration responses and generic chats
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text.strip()

    awaiting_flag = context.user_data.get('awaiting_registration_data') or is_awaiting_registration(chat_id)

    if awaiting_flag:
        # Save registration data
        await safe_save_registration(user.id, text)

        # Clear awaiting flags
        context.user_data['awaiting_registration_data'] = False
        if chat_id in AWAITING_REGISTRATIONS:
            del AWAITING_REGISTRATIONS[chat_id]

        confirmation_text = (
            "✅ *Спасибо! Ваши данные получены!*\n\n"
            "Наш менеджер свяжется с вами в течение 15 минут для подтверждения и подключения к VIP сигналам.\n\n"
            "Мы зарезервировали для вас место на 24 часа! 🎉"
        )
        await update.message.reply_text(confirmation_text, parse_mode="Markdown")
    else:
        # Not awaiting registration — provide help / menu
        reply = (
            "🤖 Я бот для подключения к VIP сигналам по золоту.\n\n"
            "Используйте кнопки меню для навигации или напишите @Skalpingx для связи с менеджером."
        )
        await update.message.reply_text(reply)


# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # Optionally inform the user
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="⚠️ Произошла ошибка на сервере. Администратор уведомлён.")
    except Exception:
        logger.exception("Failed to notify user about error.")


# Health check route for Railway (or any host)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# Webhook receiver (Telegram will POST updates here)
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook_receiver():
    """Receives update via POST from Telegram and pushes it into the PTB application queue."""
    if request.headers.get("content-type") != "application/json":
        # Accept also other content types but insist on JSON ideally
        pass
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200


# Startup helper: set webhook and optionally create DB tables
async def on_startup(app_obj):
    logger.info("Bot starting up — on_startup called")
    # Set webhook if WEBHOOK_FULL_URL provided
    try:
        if WEBHOOK_FULL_URL:
            await application.bot.delete_webhook(drop_pending_updates=True)
            set_ok = await application.bot.set_webhook(url=WEBHOOK_FULL_URL)
            logger.info(f"Set webhook to {WEBHOOK_FULL_URL}: {set_ok}")
        else:
            logger.warning("WEBHOOK_FULL_URL not set — you must set WEBHOOK_URL env to use webhook mode")
    except Exception:
        logger.exception("Failed to set webhook on startup")

    # Try to ensure DB tables exist (best-effort)
    if DB_AVAILABLE:
        try:
            # If database.py exposes create_tables, call it
            if hasattr(db, "create_tables"):
                db.create_tables()
                logger.info("Ensured DB tables (create_tables called)")
        except Exception:
            logger.exception("Failed to create DB tables on startup")


# Graceful shutdown tasks (optional)
async def on_shutdown(app_obj):
    logger.info("Bot shutting down — on_shutdown called")
    try:
        await application.bot.delete_webhook()
        logger.info("Webhook deleted on shutdown")
    except Exception:
        logger.exception("Failed to delete webhook on shutdown")


# ========== Register handlers into application ==========
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CallbackQueryHandler(callback_router))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
application.add_error_handler(error_handler)

# Attach startup/shutdown to application lifecycle
application.post_init(on_startup)
application.post_shutdown(on_shutdown)


# ========== Run (if launched directly) ==========
if __name__ == "__main__":
    # If running locally without webhook, you can run long polling:
    RUN_POLLER = os.environ.get("RUN_POLLING")  # set to "1" to use polling instead of webhook (not recommended for Railway)
    if RUN_POLLER:
        logger.info("Starting bot in long-polling mode (RUN_POLLING=1)")
        application.run_polling()
    else:
        # Run Flask built-in server to receive webhook posts; PTB application queue will process updates
        # For production on Railway, the container should expose port from env or default 5000
        port = int(os.environ.get("PORT", "5000"))
        logger.info(f"Starting Flask app for webhook receiver on 0.0.0.0:{port}, webhook path: {WEBHOOK_PATH}")
        # When using this approach, make sure Railway sends requests to WEBHOOK_FULL_URL
        app.run(host="0.0.0.0", port=port, debug=False)
