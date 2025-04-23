import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Инициализация бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словари для хранения данных
user_last_action = {}
user_valentines_count = {}

# Состояния FSM
class ValentineStates(StatesGroup):
    waiting_for_sender_name = State()  # Как представиться получателю
    waiting_for_recipient_username = State()  # @username получателя
    waiting_for_recipient_fullname = State()  # Имя Фамилия получателя
    waiting_for_text = State()  # Текст Кожанки

# Клавиатура главного меню
def get_main_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="💌 Создать Кожанку"))
    builder.add(types.KeyboardButton(text="📋 Правила"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

# Проверка на спам (10 секунд)
def is_too_fast(user_id):
    now = datetime.now()
    last_action_time = user_last_action.get(user_id)
    if last_action_time and (now - last_action_time) < timedelta(seconds=1):
        return True
    user_last_action[user_id] = now
    return False

# Проверка лимита Кожанок
def check_valentine_limit(user_id):
    return user_valentines_count.get(user_id, 0) < 2

# Получение username пользователя
def get_user_username(user: types.User):
    if user.username:
        return f"@{user.username}"
    return "нет username"

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
💘 <b>Kozhan Bot</b> 💘

Отправь анонимную Кожанку другу или знакомому!

✨ <b>Как это работает:</b>
1. Ты пишешь сообщение
2. Указываешь получателя
3. Мы доставляем Кожанку
4. Получатель радуется!

<b>Всё полностью анонимно!</b> Твое имя никто не узнает.
"""
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())

# Обработчик кнопки "Создать Кожанку"
@dp.message(F.text.lower() == "💌 создать кожанку")
async def create_valentine(message: types.Message, state: FSMContext):
    if is_too_fast(message.from_user.id):
        await message.answer("⏳ Подожди немного перед следующим действием. Чтобы избежать спама, между сообщениями должен быть интервал 1 секунда.")
        return
    
    if not check_valentine_limit(message.from_user.id):
        await message.answer("❌ Ты уже отправил(а) максимальное количество Кожанок (2).")
        return
    
    info_text = """
✏️ <b>Шаг 1 из 4:</b> Как тебя назвать в Кожанке?

📝 Примеры:
• "Твой тайный поклонник"
• "Анонимный друг"
• "Кто-то из группы"

ℹ️ <i>Именно это имя увидит получатель вместо твоего реального!</i>
"""
    await message.answer(info_text, reply_markup=ReplyKeyboardRemove())
    await state.set_state(ValentineStates.waiting_for_sender_name)

# Обработчик имени отправителя
@dp.message(ValentineStates.waiting_for_sender_name)
async def process_sender_name(message: types.Message, state: FSMContext):
    if is_too_fast(message.from_user.id):
        await message.answer("⏳ Подожди 1 секунду перед следующим действием.")
        return
    
    if len(message.text) > 50:
        await message.answer("❌ Слишком длинное имя (максимум 50 символов). Придумай что-то покороче.")
        return
    
    await state.update_data(sender_name=message.text)
    
    info_text = """
✏️ <b>Шаг 2 из 4:</b> Введи @username получателя

📝 Пример: @username или просто username

ℹ️ Если не знаешь username, можешь написать "не знаю" и перейти к следующему шагу.
"""
    await message.answer(info_text)
    await state.set_state(ValentineStates.waiting_for_recipient_username)

# Обработчик username получателя
@dp.message(ValentineStates.waiting_for_recipient_username)
async def process_recipient_username(message: types.Message, state: FSMContext):
    if is_too_fast(message.from_user.id):
        await message.answer("⏳ Подожди 1 секунду перед следующим действием.")
        return
    
    username = message.text.replace("@", "") if message.text.lower() != "не знаю" else "не указан"
    await state.update_data(recipient_username=username)
    
    info_text = """
✏️ <b>Шаг 3 из 4:</b> Введи имя и фамилию получателя

📝 Примеры:
• "Анна Петрова"
• "Иван Иванов"
• "Мария" (если не знаешь фамилию)

ℹ️ Это нужно для точной доставки Кожанки.
"""
    await message.answer(info_text)
    await state.set_state(ValentineStates.waiting_for_recipient_fullname)

# Обработчик ФИО получателя
@dp.message(ValentineStates.waiting_for_recipient_fullname)
async def process_recipient_fullname(message: types.Message, state: FSMContext):
    if is_too_fast(message.from_user.id):
        await message.answer("⏳ Подожди 1 секунду перед следующим действием.")
        return
    
    if len(message.text) > 100:
        await message.answer("❌ Слишком длинное имя (максимум 100 символов). Пожалуйста, сократи.")
        return
    
    await state.update_data(recipient_fullname=message.text)
    
    info_text = """
✏️ <b>Шаг 4 из 4:</b> Напиши текст Кожанки

📝 Пример:
"Привет! Хочу сказать, что ты замечательный человек! Удачи на экзаменах!"

⚠️ Ограничения:
- Максимум 500 символов
- Без оскорблений
"""
    await message.answer(info_text)
    await state.set_state(ValentineStates.waiting_for_text)

# Обработчик текста Кожанки
@dp.message(ValentineStates.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    if is_too_fast(message.from_user.id):
        await message.answer("⏳ Подожди 1 секунду перед следующим действием.")
        return
    
    if len(message.text) > 500:
        await message.answer("❌ Текст слишком длинный (максимум 500 символов). Сократи его и попробуй снова.")
        return
    
    user_data = await state.get_data()
    await state.clear()
    
    # Увеличиваем счетчик Кожанок
    user_id = message.from_user.id
    user_valentines_count[user_id] = user_valentines_count.get(user_id, 0) + 1
    
    # Получаем username отправителя
    sender_username = get_user_username(message.from_user)
    
    # Формируем сообщение для админа
    admin_message = (
        f"💌 Новая Кожанка!\n\n"
        f"📩 Отправитель: {sender_username}\n"
        f"👤 Имя отправителя в Кожанке: {user_data['sender_name']}\n"
        f"🎯 Получатель: {user_data['recipient_fullname']}\n"
        f"📱 Username получателя: @{user_data['recipient_username']}\n"
        f"✉️ Текст:\n<i>{message.text}</i>\n\n"
        f"📊 Всего Кожанок от пользователя: {user_valentines_count[user_id]}/2"
    )
    
    try:
        await bot.send_message(ADMIN_CHAT_ID, admin_message)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        await message.answer("❌ Ошибка отправки. Попробуй позже.")
        return
    
    # Сообщение пользователю
    remaining = 2 - user_valentines_count[user_id]
    success_text = f"""
🎉 <b>Кожанка отправлена!</b>

<b>Твое имя в Кожанке:</b> {user_data['sender_name']}
<b>Получатель:</b> {user_data['recipient_fullname']}
<b>Username получателя:</b> @{user_data['recipient_username']}

📜 <b>Текст:</b>
<i>{message.text}</i>

💌 Кожанка будет доставлена в ближайшее время.
🔄 Осталось Кожанок: {remaining}/2
"""
    await message.answer(success_text, reply_markup=get_main_menu_keyboard())

# Обработчик всех других сообщений
@dp.message()
async def handle_other_messages(message: types.Message):
    if is_too_fast(message.from_user.id):
        return
    
    await message.answer(
        "Используй кнопки меню или команду /help",
        reply_markup=get_main_menu_keyboard()
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Starting bot...")
    import asyncio
    asyncio.run(main())