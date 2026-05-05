import logging
import os
from typing import Dict

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import Message
from aiohttp import web
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавь токен в .env")

SUPPORT_ADMIN_ID_RAW = os.getenv("SUPPORT_ADMIN_ID")
if not SUPPORT_ADMIN_ID_RAW:
    raise RuntimeError("SUPPORT_ADMIN_ID не найден. Добавь ID оператора в .env")
try:
    SUPPORT_ADMIN_ID = int(SUPPORT_ADMIN_ID_RAW)
except ValueError as exc:
    raise RuntimeError("SUPPORT_ADMIN_ID должен быть числом.") from exc

WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if not WEBHOOK_URL and render_hostname:
    WEBHOOK_URL = f"https://{render_hostname}{WEBHOOK_PATH}"

dp = Dispatcher()
reply_routes: Dict[int, int] = {}


def is_operator(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == SUPPORT_ADMIN_ID)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if is_operator(message):
        await message.answer(
            "Режим оператора активен.\n"
            "Отвечай пользователю реплаем на пересланный запрос "
            "или командой: /reply <user_id> <текст>"
        )
        return
    await message.answer(
        "Привет! Я бот поддержки.\n"
        "Опиши вопрос, и я передам его оператору.\n"
        "Ответ придет в этот чат."
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if is_operator(message):
        await message.answer(
            "Операторские команды:\n"
            "/reply <user_id> <текст> - ответ пользователю\n"
            "Реплай на пересланный запрос - быстрый ответ"
        )
        return
    await message.answer("Напиши сообщение в чат, и оператор скоро ответит.")


@dp.message(Command("reply"))
async def cmd_reply(message: Message) -> None:
    if not is_operator(message):
        return

    text = message.text or ""
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: /reply <user_id> <текст>")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return

    await message.bot.send_message(chat_id=target_user_id, text=parts[2])
    await message.answer("Ответ отправлен пользователю.")


@dp.message()
async def relay_message(message: Message) -> None:
    if not message.from_user:
        return

    if is_operator(message):
        if message.reply_to_message:
            target_user_id = reply_routes.get(message.reply_to_message.message_id)
            if not target_user_id:
                await message.answer(
                    "Не вижу маршрут для этого реплая. "
                    "Используй /reply <user_id> <текст>."
                )
                return

            await message.copy_to(chat_id=target_user_id)
            await message.answer("Отправлено пользователю.")
        return

    user = message.from_user
    waiting_text = "Запрос принят. Передал оператору, пожалуйста подождите."
    await message.answer(waiting_text)

    username_value = f"@{user.username}" if user.username else "нет"
    header = (
        "Новый запрос в поддержку:\n"
        f"user_id: {user.id}\n"
        f"name: {user.full_name}\n"
        f"username: {username_value}"
    )
    header_msg = await message.bot.send_message(SUPPORT_ADMIN_ID, header)
    reply_routes[header_msg.message_id] = user.id

    copied_msg = await message.copy_to(chat_id=SUPPORT_ADMIN_ID)
    reply_routes[copied_msg.message_id] = user.id


def register_webhook_events() -> None:
    if not WEBHOOK_URL:
        raise RuntimeError(
            "WEBHOOK_URL не задан. Для Render укажи WEBHOOK_URL вручную "
            "или используй RENDER_EXTERNAL_HOSTNAME."
        )

    async def on_startup(bot: Bot) -> None:
        await bot.set_webhook(WEBHOOK_URL)

    async def on_shutdown(bot: Bot) -> None:
        await bot.delete_webhook()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)


async def run_polling(bot: Bot) -> None:
    await dp.start_polling(bot)


def run_webhook(bot: Bot) -> None:
    register_webhook_events()
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=PORT)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    if WEBHOOK_URL:
        run_webhook(bot)
    else:
        import asyncio

        asyncio.run(run_polling(bot))


if __name__ == "__main__":
    main()
