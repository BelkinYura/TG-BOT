import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавь токен в .env")


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="О боте", callback_data="about")],
            [InlineKeyboardButton(text="Помощь", callback_data="help")],
        ]
    )


dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Я Telegram-бот.\n\n"
        "Доступные команды:\n"
        "/start - запуск\n"
        "/help - помощь\n"
        "/menu - показать меню"
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я отвечаю на команды и кнопки.\n"
        "Попробуй /menu или просто отправь сообщение."
    )


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Вот меню:", reply_markup=main_menu())


@dp.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery) -> None:
    await callback.message.answer("Это базовый шаблон бота на aiogram.")
    await callback.answer()


@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.answer("Нужны новые функции? Напиши, что добавить.")
    await callback.answer()


@dp.message()
async def echo(message: Message) -> None:
    await message.answer(f"Ты написал: {message.text}")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
