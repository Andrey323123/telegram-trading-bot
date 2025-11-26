# bot.py
import logging
import asyncio
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

class AdminStates(StatesGroup):
    in_dialog = State()

# Хранилище активных диалогов {user_id: admin_id}
active_dialogs = {}

# Создаем Reply-клавиатуру с кнопкой "Начать" (всегда внизу)
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Начать")]
    ],
    resize_keyboard=True,
    is_persistent=True,  # Клавиатура всегда видна
    one_time_keyboard=False  # Не скрывается после нажатия
)

def escape_markdown(text: str) -> str:
    """Экранирует спецсимволы Markdown"""
    if not text:
        return ""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def send_to_admin(user_info: str, registration_data: str, user_id: int):
    """Отправляем данные админу с кнопкой ответа"""
    try:
        # Экранируем все текстовые данные
        user_info_escaped = escape_markdown(user_info)
        registration_data_escaped = escape_markdown(registration_data)
        
        message_text = f"📥 *НОВЫЕ ДАННЫЕ ОТ ПОЛЬЗОВАТЕЛЯ*\n\n" \
                      f"👤 *Информация о пользователе:*\n{user_info_escaped}\n\n" \
                      f"📋 *Данные регистрации:*\n{registration_data_escaped}\n\n" \
                      f"⏰ *Время получения:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Клавиатура с кнопкой "Ответить"
        reply_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать диалог", callback_data=f"start_dialog_{user_id}")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"close_dialog_{user_id}")]
        ])
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=message_text,
            reply_markup=reply_keyboard,
            parse_mode='MarkdownV2'
        )
        logging.info(f"✅ Данные отправлены админу {ADMIN_ID} с кнопкой диалога")
    except Exception as e:
        logging.error(f"❌ Ошибка отправки данных админу: {e}")
        # Пробуем отправить без Markdown
        try:
            plain_text = f"📥 НОВЫЕ ДАННЫЕ ОТ ПОЛЬЗОВАТЕЛЯ\n\n" \
                        f"👤 Информация о пользователе:\n{user_info}\n\n" \
                        f"📋 Данные регистрации:\n{registration_data}\n\n" \
                        f"⏰ Время получения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            reply_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Начать диалог", callback_data=f"start_dialog_{user_id}")],
                [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"close_dialog_{user_id}")]
            ])
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=plain_text,
                reply_markup=reply_keyboard
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
    # Сразу показываем кнопку "Начать"
    await message.answer(
        "👋 Добро пожаловать! Используйте кнопку ниже для навигации:",
        reply_markup=start_keyboard
    )
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
        return
    
    # Для новых пользователей - стандартное приветствие
    db.schedule_reminder(user.id, "30_hours", 30)
    db.schedule_reminder(user.id, "72_hours", 72)
    
    welcome_text = f"👋 Приветствую, {user.first_name}!\n\nДобро пожаловать в элитное сообщество трейдеров!\n\nЯ помогу вам получить доступ к VIP сигналам по золоту и премиум обучению."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Узнать о VIP преимуществах", callback_data="vip_benefits")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard)

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

@dp.callback_query(F.data == "make_payment")
async def show_payment_instructions(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.log_interaction(user_id, 'clicked_make_payment')
    
    payment_text = """💳 *Для оформления оплаты:*

Напишите мне в личные сообщения:
👉 https://t.me/m/XCFTGFzeNzVi

*Укажите в сообщении:*
- Выбранный тариф (1 месяц, 3 месяца, год или план на всю жизнь)

Я отвечу в течение 5-10 минут с реквизитами для оплаты и инструкциями!"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/m/XCFTGFzeNzVi")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="has_broker")]
    ])
    
    await callback.message.edit_text(payment_text, reply_markup=keyboard, parse_mode='Markdown')

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

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    # При возврате к старту показываем кнопку "Начать"
    await callback.message.answer(
        "👋 Возвращаемся в главное меню:",
        reply_markup=start_keyboard
    )
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
    
    # Отправляем данные админу С КНОПКОЙ ДИАЛОГА
    await send_to_admin(user_info, user_data_text, user_id)
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем подтверждение пользователю
    confirmation_text = """✅ *Спасибо! Ваши данные получены!*

Наш менеджер свяжется с вами в течение 15 минут для подтверждения и подключения к VIP сигналам.

⏳ *Ожидайте, пожалуйста!*

Мы зарезервировали для вас место на 24 часа! 🎉"""
    
    await message.answer(confirmation_text, parse_mode='Markdown')

# Обработка кнопки "Начать диалог" от админа
@dp.callback_query(F.data.startswith("start_dialog_"))
async def handle_start_dialog(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Начать диалог' админом"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    user_id = int(callback.data.replace("start_dialog_", ""))
    
    # Начинаем диалог
    active_dialogs[user_id] = ADMIN_ID
    await state.set_state(AdminStates.in_dialog)
    await state.update_data(target_user_id=user_id)
    
    # Уведомляем админа
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"💬 *Диалог начат с пользователем {user_id}*\n\n"
        f"Теперь все ваши сообщения будут отправляться этому пользователю от имени бота.\n"
        f"И все сообщения от пользователя будут приходить вам.\n\n"
        f"Используйте команду /stop_dialog чтобы завершить диалог.",
        parse_mode='Markdown'
    )
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            chat_id=user_id,
            text="💬 *Менеджер подключился к чату*\n\nТеперь вы можете общаться напрямую!",
            parse_mode='Markdown'
        )
    except Exception as e:
        await callback.message.answer(f"❌ Не удалось уведомить пользователя: {e}")
    
    await callback.answer("Диалог начат!")

# Обработка кнопки "Закрыть" от админа
@dp.callback_query(F.data.startswith("close_dialog_"))
async def handle_close_dialog(callback: CallbackQuery):
    """Обрабатывает нажатие кнопки 'Закрыть' админом"""
    if str(callback.from_user.id) != ADMIN_ID:
        await callback.answer("❌ У вас нет прав для этого действия", show_alert=True)
        return
    
    user_id = int(callback.data.replace("close_dialog_", ""))
    
    # Закрываем диалог
    if user_id in active_dialogs:
        del active_dialogs[user_id]
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Диалог с пользователем {user_id} закрыт")
    await callback.answer("Диалог закрыт")

# Команда для завершения диалога
@dp.message(Command("stop_dialog"))
async def stop_dialog_command(message: types.Message, state: FSMContext):
    """Завершает текущий диалог"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    current_state = await state.get_state()
    
    # Проверяем есть ли активный диалог
    active_dialog_user_id = None
    for user_id, admin_id in active_dialogs.items():
        if str(admin_id) == ADMIN_ID:
            active_dialog_user_id = user_id
            break
    
    if not active_dialog_user_id and current_state != AdminStates.in_dialog:
        await message.answer("❌ Сейчас нет активного диалога")
        return
    
    # Получаем ID пользователя из состояния или из активных диалогов
    data = await state.get_data()
    target_user_id = data.get('target_user_id') or active_dialog_user_id
    
    if target_user_id and target_user_id in active_dialogs:
        del active_dialogs[target_user_id]
    
    await state.clear()
    
    # Уведомляем пользователя С КНОПКОЙ "НАЧАТЬ"
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="💬 *Диалог с менеджером завершен*\n\nСпасибо за общение! Если у вас остались вопросы, используйте кнопку 'Начать'.",
            parse_mode='Markdown',
            reply_markup=start_keyboard
        )
    except Exception as e:
        logging.error(f"Ошибка уведомления пользователя: {e}")
    
    await message.answer(f"✅ Диалог с пользователем {target_user_id} завершен")

# Обработка сообщений админа в режиме диалога
@dp.message(AdminStates.in_dialog)
async def handle_admin_dialog_message(message: types.Message, state: FSMContext):
    """Обрабатывает сообщения админа в режиме диалога"""
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    # Если админ отправил команду /stop_dialog во время диалога
    if message.text == "/stop_dialog":
        await stop_dialog_command(message, state)
        return
    
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    
    if not target_user_id or target_user_id not in active_dialogs:
        await message.answer("❌ Диалог не активен. Используйте /stop_dialog для выхода.")
        return
    
    try:
        # Отправляем сообщение пользователю от имени бота
        await bot.send_message(
            chat_id=target_user_id,
            text=message.text
        )
        
        # Логируем сообщение админа
        db.log_interaction(target_user_id, 'admin_message', message.text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки сообщения: {e}")

# Обработка сообщений пользователей (пересылка админу если есть активный диалог)
@dp.message()
async def handle_user_messages(message: types.Message):
    user_id = message.from_user.id
    user_data_text = message.text
    
    # Если это кнопка "Начать" - обрабатываем как старт
    if message.text == "🚀 Начать":
        await handle_start_button(message)
        return
    
    # Если у пользователя активный диалог с админом
    if user_id in active_dialogs:
        # Пересылаем сообщение админу
        user_info = f"👤 Пользователь: {message.from_user.first_name} (ID: {user_id})"
        if message.from_user.username:
            user_info += f" @{message.from_user.username}"
        
        admin_message = f"💬 *Сообщение от пользователя:*\n\n{user_data_text}\n\n{user_info}"
        
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            
            # Логируем сообщение пользователя
            db.log_interaction(user_id, 'user_message_dialog', user_data_text)
            
        except Exception as e:
            logging.error(f"Ошибка пересылки сообщения админу: {e}")
    
    else:
        # Стандартная обработка для пользователей без активного диалога
        db.log_interaction(user_id, 'sent_message', user_data_text)
        response_text = "🤖 Я бот для подключения к VIP сигналам по золоту.\n\nИспользуйте кнопку 'Начать' для навигации."
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
                    
                    await bot.send_message(chat_id=user_id, text=message_text, reply_markup=start_keyboard)
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
    print("👨‍💼 Менеджер: https://t.me/m/XCFTGFzeNzVi")
    print(f"📨 Уведомления админу: {ADMIN_ID}")
    print("🔄 Кнопка 'Начать' всегда доступна внизу экрана")
    print("💬 Система диалогов активирована")
    print("📝 Команды для админа: /stop_dialog - завершить диалог")
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
