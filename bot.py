import asyncio
import logging
import mysql.connector
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = '7263777659:AAEoCu2MsnJDkGQDZPk3VHNoywf5Hu6Hoyg'

# Логгирование
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Простое хранилище сессий
sessions = {}

# Подключение к базе
def get_tasks():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root12',
        database='todolist'
    )
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM items")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Напоминалка (фоновая)
async def remind_later(chat_id, task, delay_seconds, user_name):
    await asyncio.sleep(delay_seconds)
    await bot.send_message(
        chat_id,
        f"🔔 Напоминание, {user_name}!\nНе забудь: <b>{task}</b>",
        parse_mode=ParseMode.HTML
    )

# /start
@dp.message(CommandStart())
async def start(message: types.Message):
    sessions[message.chat.id] = {"step": "login"}
    await message.answer("Введите логин:")

# Авторизация и логика
@dp.message(F.text)
async def handle_auth_and_logic(message: types.Message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})

    if session.get("step") == "login":
        session["login"] = message.text.strip()
        session["step"] = "password"
        await message.answer("Введите пароль:")
        return

    if session.get("step") == "password":
        session["password"] = message.text.strip()
        if session["login"] == "admin" and session["password"] == "admin":
            session["authenticated"] = True
            session["step"] = "choose_task"
            tasks = get_tasks()
            session["tasks"] = tasks

            builder = InlineKeyboardBuilder()
            for task_id, text in tasks:
                builder.button(text=text, callback_data=str(task_id))
            builder.adjust(1)  # ОДНА КНОПКА В РЯДУ (в столбик)

            await message.answer("Выберите задачу:", reply_markup=builder.as_markup())

        else:
            await message.answer("Неверный логин или пароль. Попробуйте снова: /start")
            sessions.pop(chat_id, None)
        return

    if session.get("step") == "enter_delay" and message.text.isdigit():
        minutes = int(message.text)
        task = session.get("selected_task")
        user_name = message.from_user.first_name or "пользователь"
        await message.answer(
            f"✅ Напоминание будет через {minutes} мин. о задаче:\n<b>{task}</b>",
            parse_mode=ParseMode.HTML
        )

        # Назначаем напоминание
        asyncio.create_task(remind_later(chat_id, task, minutes * 60, user_name))

        # Сразу возвращаем к выбору задач
        session["step"] = "choose_task"
        tasks = get_tasks()
        session["tasks"] = tasks

        builder = InlineKeyboardBuilder()
        for task_id, text in tasks:
            builder.button(text=text, callback_data=str(task_id))
        builder.adjust(1)  # Кнопки в столбик
        await message.answer("Выберите задачу:", reply_markup=builder.as_markup())

# Выбор задачи
@dp.callback_query()
async def task_chosen(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    session = sessions.get(chat_id, {})

    task_id = int(callback.data)
    task_text = next((t[1] for t in session.get("tasks", []) if t[0] == task_id), None)

    if not task_text:
        await callback.message.answer("Задача не найдена.")
        return

    session["selected_task"] = task_text
    session["step"] = "enter_delay"
    await callback.message.answer(
        f"Через сколько минут напомнить о задаче:\n<b>{task_text}</b>?",
        parse_mode=ParseMode.HTML
    )

# Запуск
if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
