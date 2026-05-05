# TG Bot (aiogram)

Telegram-бот поддержки на Python. Пользователь пишет в бота, получает автоответ "подождите", а оператор отвечает ему из своего Telegram.

## Что умеет
- Принимает запросы от пользователей
- Автоматически уведомляет, что запрос передан оператору
- Пересылает входящие сообщения оператору
- Оператор отвечает реплаем на запрос или командой `/reply <user_id> <текст>`

## Быстрый старт
1. Установи Python 3.10+.
2. В папке проекта выполни:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
3. Создай `.env` на основе `.env.example` и заполни:
   - `BOT_TOKEN=...`
   - `SUPPORT_ADMIN_ID=...`
4. Запусти:
   - `python bot.py`

## Как получить токен
1. Открой [@BotFather](https://t.me/BotFather)
2. Команда `/newbot`
3. Скопируй токен и вставь в `.env`

## Как узнать SUPPORT_ADMIN_ID
1. Открой [@userinfobot](https://t.me/userinfobot)
2. Нажми `Start`
3. Скопируй свой числовой `Id`
4. Вставь его в `.env` / Render как `SUPPORT_ADMIN_ID`

## Чтобы ничего не запускать локально (Render)
Можно загрузить проект в облако, и бот будет работать там 24/7.

1. Создай репозиторий на GitHub и загрузи туда папку `tg-bot`.
2. Зайди в [Render](https://render.com) -> **New** -> **Blueprint**.
3. Подключи репозиторий: Render прочитает `render.yaml` и создаст web service.
4. В переменных окружения укажи:
   - `BOT_TOKEN=твой_токен`
   - `SUPPORT_ADMIN_ID=твой_telegram_id`
   - `WEBHOOK_URL=https://<имя-сервиса>.onrender.com/webhook`
5. Нажми deploy.

После этого бот работает на серверах Render, а компьютер можно выключать.
