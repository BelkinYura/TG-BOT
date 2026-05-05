# TG Bot (aiogram)

Простой Telegram-бот на Python. Локально работает через polling, в Render - через webhook.

## Что умеет
- Команды: `/start`, `/help`, `/menu`
- Inline-кнопки
- Echo-ответ на обычные сообщения

## Быстрый старт
1. Установи Python 3.10+.
2. В папке проекта выполни:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
3. Создай `.env` на основе `.env.example` и вставь токен:
   - `BOT_TOKEN=...`
4. Запусти:
   - `python bot.py`

## Как получить токен
1. Открой [@BotFather](https://t.me/BotFather)
2. Команда `/newbot`
3. Скопируй токен и вставь в `.env`

## Чтобы ничего не запускать локально (Render)
Можно загрузить проект в облако, и бот будет работать там 24/7.

1. Создай репозиторий на GitHub и загрузи туда папку `tg-bot`.
2. Зайди в [Render](https://render.com) -> **New** -> **Blueprint**.
3. Подключи репозиторий: Render прочитает `render.yaml` и создаст web service.
4. В переменных окружения укажи:
   - `BOT_TOKEN=твой_токен`
   - `WEBHOOK_URL=https://<имя-сервиса>.onrender.com/webhook`
5. Нажми deploy.

После этого бот работает на серверах Render, а компьютер можно выключать.
