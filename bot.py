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

CLIENT_BOT_TOKEN = os.getenv("BOT_TOKEN")
if not CLIENT_BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавь токен клиентского бота в .env")

SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN")
if not SUPPORT_BOT_TOKEN:
    raise RuntimeError("SUPPORT_BOT_TOKEN не найден. Добавь токен операторского бота в .env")

SUPPORT_ADMIN_ID_RAW = os.getenv("SUPPORT_ADMIN_ID")
if not SUPPORT_ADMIN_ID_RAW:
    raise RuntimeError("SUPPORT_ADMIN_ID не найден. Добавь ID оператора в .env")
try:
    SUPPORT_ADMIN_ID = int(SUPPORT_ADMIN_ID_RAW)
except ValueError as exc:
    raise RuntimeError("SUPPORT_ADMIN_ID должен быть числом.") from exc

CLIENT_WEBHOOK_PATH = "/client-webhook"
SUPPORT_WEBHOOK_PATH = "/support-webhook"
PORT = int(os.getenv("PORT", "10000"))
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")
LEGACY_WEBHOOK_URL = os.getenv("WEBHOOK_URL")
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if not BASE_WEBHOOK_URL and LEGACY_WEBHOOK_URL:
    if LEGACY_WEBHOOK_URL.endswith("/webhook"):
        BASE_WEBHOOK_URL = LEGACY_WEBHOOK_URL[: -len("/webhook")]
    else:
        BASE_WEBHOOK_URL = LEGACY_WEBHOOK_URL.rstrip("/")
if not BASE_WEBHOOK_URL and render_hostname:
    BASE_WEBHOOK_URL = f"https://{render_hostname}"

client_dp = Dispatcher()
support_dp = Dispatcher()
reply_routes: Dict[int, int] = {}
client_bot: Bot | None = None
support_bot: Bot | None = None


def is_operator(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == SUPPORT_ADMIN_ID)


def normalize_message_text(message: Message) -> str:
    if message.text:
        return message.text
    if message.caption:
        return message.caption
    if message.photo:
        return "[Фото]"
    if message.video:
        return "[Видео]"
    if message.document:
        return "[Документ]"
    if message.voice:
        return "[Голосовое сообщение]"
    if message.audio:
        return "[Аудио]"
    if message.sticker:
        return "[Стикер]"
    return "[Неподдерживаемый тип сообщения]"


@client_dp.message(Command("start"))
async def client_start(message: Message) -> None:
    await message.answer(
        "Привет! Я клиентский бот поддержки.\n"
        "Опиши вопрос, и я передам его оператору.\n"
        "Ответ придет в этот чат."
    )


@support_dp.message(Command("start"))
async def support_start(message: Message) -> None:
    if not is_operator(message):
        await message.answer("Этот бот только для оператора поддержки.")
        return
    await message.answer(
        "Операторский бот активен.\n"
        "Отвечай пользователю реплаем на сообщение с заявкой\n"
        "или командой: /reply <user_id> <текст>"
    )


@support_dp.message(Command("help"))
async def support_help(message: Message) -> None:
    if not is_operator(message):
        return
    await message.answer(
        "Команды оператора:\n"
        "/reply <user_id> <текст> - отправить ответ пользователю\n"
        "Реплай на сообщение заявки - быстрый ответ"
    )


@support_dp.message(Command("reply"))
async def support_reply_command(message: Message) -> None:
    global client_bot
    text = message.text or ""
    if not is_operator(message):
        return
    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Формат: /reply <user_id> <текст>")
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("user_id должен быть числом.")
        return

    if client_bot is None:
        await message.answer("Клиентский бот не инициализирован.")
        return
    await client_bot.send_message(chat_id=target_user_id, text=parts[2])
    await message.answer("Ответ отправлен пользователю.")


@client_dp.message(Command("help"))
async def client_help(message: Message) -> None:
    await message.answer("Опиши вопрос в одном сообщении, я передам оператору.")


@client_dp.message()
async def client_incoming(message: Message) -> None:
    global support_bot
    if not message.from_user:
        return

    if support_bot is None:
        await message.answer("Сервис поддержки временно недоступен. Попробуйте позже.")
        return

    user = message.from_user
    await message.answer("Запрос принят. Передал оператору, пожалуйста подождите.")

    username_value = f"@{user.username}" if user.username else "нет"
    content_text = normalize_message_text(message)
    header = (
        "Новый запрос в поддержку:\n"
        f"user_id: {user.id}\n"
        f"name: {user.full_name}\n"
        f"username: {username_value}\n"
        f"Сообщение: {content_text}"
    )
    header_msg = await support_bot.send_message(SUPPORT_ADMIN_ID, header)
    reply_routes[header_msg.message_id] = user.id


@support_dp.message()
async def support_incoming(message: Message) -> None:
    global client_bot
    if not is_operator(message):
        return

    if client_bot is None:
        await message.answer("Клиентский бот не инициализирован.")
        return

    if not message.reply_to_message:
        await message.answer("Ответь реплаем на сообщение заявки или используй /reply.")
        return

    target_user_id = reply_routes.get(message.reply_to_message.message_id)
    if not target_user_id:
        await message.answer("Маршрут не найден. Используй /reply <user_id> <текст>.")
        return

    response_text = normalize_message_text(message)
    if response_text.startswith("[") and response_text.endswith("]"):
        await message.answer("Для ответа пользователю отправь текстовое сообщение.")
        return

    await client_bot.send_message(chat_id=target_user_id, text=response_text)
    await message.answer("Ответ отправлен пользователю.")


def register_webhook_events() -> None:
    global client_bot, support_bot
    if not BASE_WEBHOOK_URL:
        raise RuntimeError(
            "BASE_WEBHOOK_URL не задан. Для Render укажи BASE_WEBHOOK_URL вручную "
            "или используй RENDER_EXTERNAL_HOSTNAME."
        )
    if client_bot is None or support_bot is None:
        raise RuntimeError("Боты не инициализированы.")

    client_webhook_url = f"{BASE_WEBHOOK_URL}{CLIENT_WEBHOOK_PATH}"
    support_webhook_url = f"{BASE_WEBHOOK_URL}{SUPPORT_WEBHOOK_PATH}"

    async def client_startup(bot: Bot) -> None:
        await bot.set_webhook(client_webhook_url)

    async def client_shutdown(bot: Bot) -> None:
        await bot.delete_webhook()

    async def support_startup(bot: Bot) -> None:
        await bot.set_webhook(support_webhook_url)

    async def support_shutdown(bot: Bot) -> None:
        await bot.delete_webhook()

    client_dp.startup.register(client_startup)
    client_dp.shutdown.register(client_shutdown)
    support_dp.startup.register(support_startup)
    support_dp.shutdown.register(support_shutdown)


async def run_polling() -> None:
    global client_bot, support_bot
    if client_bot is None or support_bot is None:
        raise RuntimeError("Боты не инициализированы.")
    import asyncio

    await asyncio.gather(
        client_dp.start_polling(client_bot),
        support_dp.start_polling(support_bot),
    )


def run_webhook() -> None:
    global client_bot, support_bot
    if client_bot is None or support_bot is None:
        raise RuntimeError("Боты не инициализированы.")

    register_webhook_events()
    app = web.Application()
    SimpleRequestHandler(dispatcher=client_dp, bot=client_bot).register(
        app, path=CLIENT_WEBHOOK_PATH
    )
    SimpleRequestHandler(dispatcher=support_dp, bot=support_bot).register(
        app, path=SUPPORT_WEBHOOK_PATH
    )
    setup_application(app, client_dp, bot=client_bot)
    setup_application(app, support_dp, bot=support_bot)
    web.run_app(app, host="0.0.0.0", port=PORT)


def main() -> None:
    global client_bot, support_bot
    logging.basicConfig(level=logging.INFO)
    client_bot = Bot(token=CLIENT_BOT_TOKEN)
    support_bot = Bot(token=SUPPORT_BOT_TOKEN)
    if BASE_WEBHOOK_URL:
        run_webhook()
    else:
        import asyncio

        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
