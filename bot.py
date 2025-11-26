# bot.py
import logging
import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from database import db

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получение токена из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', '8288540260:AAF5Mf1U0QU-BHLY7dvhgvBO-wafexMZUaI')
ADMIN_ID = os.getenv('ADMIN_ID', '5067425279')

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class RegistrationStates(StatesGroup):
    awaiting_data = State()

# Создаем Reply-клавиатуру с кнопкой "Начать" (всегда внизу)
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Начать")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False  # Клавиатура всегда видна
)

def escape_markdown(text: str) -> str:
    """Экранирует спецсимволы Markdown"""
    if not text:
        return ""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def send_to_admin(user_info: str, registration_data: str):
    """Отправляем данные админу"""
    try:
        # Экранируем все текстовые данные
        user_info_escaped = escape_markdown(user_info)
        registration_data_escaped = escape_markdown(registration_data)
        
        message_text = f"📥 *НОВЫЕ ДАННЫЕ ОТ ПОЛЬЗОВАТЕЛЯ*\n\n" \
                      f"👤 *Информация о пользователе:*\n{user_info_escaped}\n\n" \
                      f"📋 *Данные регистрации:*\n{registration_data_escaped}\n\n" \
                      f"⏰ *Время получения:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            parse_mode='MarkdownV2'
        )
        logging.info(f"✅ Данные отправлены админу {ADMIN_ID}")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки данных админу: {e}")
        # Пробуем отправить без Markdown
        try:
            plain_text = f"📥 НОВЫЕ ДАННЫЕ ОТ ПОЛЬЗОВАТЕЛЯ\n\n" \
                        f"👤 Информация о пользователе:\n{user_info}\n\n" \
                        f"📋 Данные регистрации:\n{registration_data}\n\n" \
                        f"⏰ Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=plain_text
            )
            logging.info(f"✅ Данные отправлены админу {ADMIN_ID} (без Markdown)")
        except Exception as e2:
            logging.error(f"❌ Ошибка отправки данных админу даже без Markdown: {e2}")

async def show_vip_benefits_from_start(message: types.Message):
    """Показывает VIP преимущества сразу (для возвращающихся пользователей)"""
    vip_text = """🎯 *Преимущества VIP:*

⭐ *Копирование сделок по золоту*: получайте от 3 до 7 ежедневных выигрышных сигналов по золоту

⭐ *Методы торговли* - Внедрение наших секретных методов торговли в вашу игру🤫

⭐ *Поддержка 1:1*: наслаждайтесь персонализированной поддержкой

———————————————————

💎 *Зарегистрируйте торговый счет, чтобы присоединиться к VIP прямо сейчас‼*           

https://nmofficialru.com/o2o7sqk1265d                         
———————————————————

💰 *Сделайте пополнение счета минимум от 400$*"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ У меня есть брокер", callback_data="has_broker")],
        [InlineKeyboardButton(text="2️⃣ Я сделал регистрацию", callback_data="completed_registration")]
    ])
    
    await message.answer(vip_text, reply_markup=keyboard, parse_mode='Markdown')

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await process_start(message)

@dp.message(F.text == "🚀 Начать")
async def handle_start_button(message: types.Message):
    """Обрабатывает нажатие кнопки 'Начать'"""
    await process_start(message)

async def process_start(message: types.Message):
    """Основная логика обработки старта"""
    user = message.from_user
    user_data = {
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'source': 'start_command'
    }
    
    # Проверяем, новый ли пользователь и считаем взаимодействия
    is_new_user = db.add_user(user_data)
    interaction_count = db.get_user_interactions_count(user.id)
    
    db.log_interaction(user.id, 'start_command')
    
    # Если пользователь не новый ИЛИ у него больше 1 взаимодействия, показываем VIP сразу
    if not is_new_user or interaction_count > 1:
        await show_vip_benefits_from_start(message)
        # Всегда показываем кнопку "Начать" после ответа
        await message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)
        return
    
    # Для новых пользователей - стандартное приветствие
    db.schedule_reminder(user.id, "30_hours", 30)
    db.schedule_reminder(user.id, "72_hours", 72)
    
    welcome_text = f"👋 Приветствую, {user.first_name}!\n\nДобро пожаловать в элитное сообщество трейдеров!\n\nЯ помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)
    # Показываем кнопку "Начать" после приветствия
    await message.answer("Используйте кнопку 'Начать' для быстрого доступа к меню:", reply_markup=start_keyboard)

@dp.callback_query(F.data == "vip_benefits")
async def show_vip_benefits(callback: CallbackQuery):
    user_id = callback.from_user.id
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
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ У меня есть брокер", callback_data="has_broker")],
        [InlineKeyboardButton(text="2️⃣ Я сделал регистрацию", callback_data="completed_registration")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(vip_text, reply_markup=keyboard, parse_mode='Markdown')
    # После редактирования сообщения отправляем кнопку "Начать"
    await callback.message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)

@dp.callback_query(F.data == "has_broker")
async def show_has_broker_options(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.log_interaction(user_id, 'selected_has_broker')
    
    broker_text = """📈 *VIP группа Скальпинг Золото* 🥇 3-7 сигналов в день 

💵 *Цена:*

1 месяц / 150$

3 месяца / 300$

1 год / 500$

🎉🎁План на всю жизнь 1000$"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Хочу сделать оплату", callback_data="make_payment")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="vip_benefits")]
    ])
    
    await callback.message.edit_text(broker_text, reply_markup=keyboard, parse_mode='Markdown')
    await callback.message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)

@dp.callback_query(F.data == "make_payment")
async def show_payment_instructions(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.log_interaction(user_id, 'clicked_make_payment')
    
    payment_text = """💳 *Для оформления оплаты:*

Напишите мне в личные сообщения:
👉 @Skalpingx

*Укажите в сообщении:*
- Выбранный тариф (1 месяц, 3 месяца, год или план на всю жизнь)

Я отвечу в течение 5-10 минут с реквизитами для оплаты и инструкциями!"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/Skalpingx")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="has_broker")]
    ])
    
    await callback.message.edit_text(payment_text, reply_markup=keyboard, parse_mode='Markdown')
    await callback.message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)

@dp.callback_query(F.data == "completed_registration")
async def show_completed_registration(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user = callback.from_user
    db.log_interaction(user_id, 'selected_completed_registration')
    
    registration_text = """После регистрации отправьте мне следующую информацию:

✅Полное Имя
✅Номер счета  
✅Размер капитала"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="vip_benefits")]
    ])
    
    await callback.message.edit_text(registration_text, reply_markup=keyboard)
    
    reservation_text = f"Привет, {user.first_name}, просто хочу сообщить тебе, что я зарезервирую для тебя бесплатное место на ближайшие 24 часа!"
    await callback.message.answer(reservation_text)
    
    await state.set_state(RegistrationStates.awaiting_data)
    await callback.message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    await cmd_start(callback.message)

@dp.message(RegistrationStates.awaiting_data)
async def handle_registration_data(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = message.from_user
    user_data_text = message.text
    
    # Сохраняем данные в базу
    db.save_registration_data(user_id, user_data_text)
    db.log_interaction(user_id, 'submitted_registration_data', user_data_text)
    
    # Формируем информацию о пользователе для админа
    user_info = f"ID: {user.id}\n" \
                f"Имя: {user.first_name or 'Не указано'}\n" \
                f"Фамилия: {user.last_name or 'Не указана'}\n" \
                f"Username: @{user.username or 'Не указан'}\n" \
                f"Язык: {user.language_code or 'Не указан'}"
    
    # Отправляем данные админу
    await send_to_admin(user_info, user_data_text)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем подтверждение пользователю
    confirmation_text = """✅ *Спасибо! Ваши данные получены!*

Наш менеджер свяжется с вами в течение 15 минут для подтверждения и подключения к VIP сигналам.

⏳ *Ожидайте, пожалуйста!*

Мы зарезервировали для вас место на 24 часа! 🎉"""
    
    await message.answer(confirmation_text, parse_mode='Markdown')
    await message.answer("Нажмите кнопку ниже для возврата в главное меню:", reply_markup=start_keyboard)

@dp.message()
async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id
    user_data_text = message.text
    
    # Если это не кнопка "Начать", логируем и отвечаем
    if message.text != "🚀 Начать":
        db.log_interaction(user_id, 'sent_message', user_data_text)
        response_text = "🤖 Я бот для подключения к VIP сигналам по золоту.\n\nИспользуйте кнопку 'Начать' для навигации или напишите @Skalpingx для связи с менеджером."
        await message.answer(response_text, reply_markup=start_keyboard)

# Фоновая задача для напоминаний
async def check_reminders():
    while True:
        try:
            reminders = db.get_pending_reminders()
            for reminder in reminders:
                try:
                    user_id = reminder['user_id']
                    reminder_type = reminder['reminder_type']
                    first_name = reminder['first_name']
                    
                    if reminder_type == "30_hours":
                        message_text = f"👋 Привет, {first_name}! Я зарезервировал одно место в VIP, жду ответа 🙏"
                    elif reminder_type == "72_hours":
                        message_text = f"🤝 Привет, {first_name}! Я все еще держу место для тебя, отпишись как будешь готов 🤝"
                    else:
                        continue
                    
                    await bot.send_message(chat_id=user_id, text=message_text)
                    db.mark_reminder_sent(reminder['id'])
                    db.log_interaction(user_id, f"reminder_sent_{reminder_type}")
                    
                    logging.info(f"Отправлено напоминание {reminder_type} пользователю {user_id}")
                    
                except Exception as e:
                    logging.error(f"Ошибка отправки напоминания: {e}")
        except Exception as e:
            logging.error(f"Ошибка в обработчике напоминаний: {e}")
        
        await asyncio.sleep(60)

async def main():
    # Проверяем токен бота
    try:
        bot_info = await bot.get_me()
        print(f"✅ Бот @{bot_info.username} авторизован")
    except Exception as e:
        print(f"❌ Ошибка авторизации бота: {e}")
        return
    
    # Создаем таблицы
    db.create_tables()
    print("✅ База данных готова")
    
    # Запускаем фоновую задачу для напоминаний
    asyncio.create_task(check_reminders())
    
    print("🟢 Бот запущен и готов к работе!")
    print("🔍 Найдите бота в Telegram и отправьте /start или нажмите кнопку 'Начать'")
    print("⏰ Система напоминаний активирована")
    print("⏳ Напоминания: 30ч → 1-е, 72ч → 2-е")
    print("👨‍💼 Менеджер: @Skalpingx")
    print(f"📨 Уведомления админу: {ADMIN_ID}")
    print("🔄 Кнопка 'Начать' всегда доступна внизу экрана")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
