import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiomysql import create_pool
from dotenv import load_dotenv

load_dotenv()

# ================= Настройки ================= #
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "telegram_sales_funnel")
JSON_FILE = "users.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= JSON DB ================= #
class JsonDB:
    def __init__(self, file_path):
        self.file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                json.dump({}, f)

    async def add_user(self, user_data):
        data = await self._read()
        data[str(user_data['user_id'])] = user_data
        await self._write(data)

    async def save_registration_data(self, user_id, text):
        data = await self._read()
        if str(user_id) in data:
            data[str(user_id)]['registration'] = text
            await self._write(data)

    async def _read(self):
        async with asyncio.Lock():
            with open(self.file_path, "r") as f:
                return json.load(f)

    async def _write(self, data):
        async with asyncio.Lock():
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=4)

json_db = JsonDB(JSON_FILE)

# ================= MySQL DB ================= #
class MySQLDB:
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        self.pool = await create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True
        )

    async def add_user(self, user_data):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT IGNORE INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s)",
                    (user_data['user_id'], user_data['username'], user_data['first_name'], user_data['last_name'])
                )

    async def save_registration_data(self, user_id, text):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET registration_data=%s WHERE user_id=%s",
                    (text, user_id)
                )

db = MySQLDB()

# ================= Команды ================= #
@dp.message(Command(commands=["start"]))
async def start(message: types.Message):
    user = message.from_user
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }

    # сохраняем в MySQL и JSON
    await db.add_user(user_data)
    await json_db.add_user(user_data)

    welcome_text = f"👋 Приветствую, {user.first_name}!\nДобро пожаловать в элитное сообщество трейдеров!"

    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🚀 Узнать о VIP преимуществах", callback_data="vip_benefits"))
    await message.answer(welcome_text, reply_markup=keyboard.as_markup())

# ================= Callback ================= #
@dp.callback_query(lambda c: True)
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "vip_benefits":
        await show_vip_benefits(callback)
    elif data == "has_broker":
        await show_has_broker_options(callback)
    elif data == "completed_registration":
        await show_completed_registration(callback)
    elif data == "make_payment":
        await show_payment_instructions(callback)
    elif data == "back_to_start":
        await start(callback.message)

async def show_vip_benefits(callback: types.CallbackQuery):
    vip_text = """🎯 *Преимущества VIP:*
⭐ Копирование сделок по золоту
⭐ Методы торговли
⭐ Поддержка 1:1
💎 Зарегистрируйте торговый счет: https://nmofficialru.com/o2o7sqk1265d
💰 Минимальный депозит: 400$"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton("1️⃣ У меня есть брокер и я не хочу его менять", callback_data="has_broker")
    )
    keyboard.row(
        InlineKeyboardButton("2️⃣ Я сделал регистрацию Готово✅", callback_data="completed_registration")
    )
    keyboard.row(
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
    )
    await callback.message.edit_text(vip_text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

async def show_has_broker_options(callback: types.CallbackQuery):
    text = """📈 VIP группа Скальпинг Золото 🥇
💵 1 мес/150$, 3 мес/300$, 1 год/500$"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton("💳 Хочу сделать оплату ✅", callback_data="make_payment")
    )
    keyboard.row(
        InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")
    )
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

async def show_payment_instructions(callback: types.CallbackQuery):
    text = "💳 Для оплаты напишите менеджеру @Skalpingx"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton("📞 Написать менеджеру", url="https://t.me/Skalpingx")
    )
    keyboard.row(
        InlineKeyboardButton("⬅️ Назад к тарифам", callback_data="has_broker")
    )
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

async def show_completed_registration(callback: types.CallbackQuery):
    text = """После регистрации отправьте мне:
✅ Полное имя
✅ Номер счета
✅ Размер капитала"""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton("⬅️ Назад к преимуществам", callback_data="vip_benefits")
    )
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await bot.send_message(callback.from_user.id, "Привет, место зарезервировано на 24 часа!")
    dp.current_state(chat=callback.from_user.id, user=callback.from_user.id).update_data(awaiting_registration_data=True)

# ================= Messages ================= #
@dp.message(lambda message: True)
async def handle_user_data(message: types.Message):
    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    user_data_state = await state.get_data()
    if user_data_state.get("awaiting_registration_data"):
        await db.save_registration_data(message.from_user.id, message.text)
        await json_db.save_registration_data(message.from_user.id, message.text)
        await state.update_data(awaiting_registration_data=False)
        await message.answer("✅ Данные получены! Менеджер свяжется с вами.")
    else:
        await message.answer("🤖 Я бот для VIP сигналов по золоту. Используйте кнопки меню.")

# ================= Запуск ================= #
async def main():
    await db.init_pool()
    print("🟢 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
