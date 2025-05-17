import logging
import time
import base64
import hmac
import hashlib
import struct
import asyncio
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ⚙️ Настройки
BOT_TOKEN = "token"
ACCOUNTS_FILE = "accounts.txt"

# 🔧 Логирование
logging.basicConfig(level=logging.INFO)

# ✅ Загрузка аккаунтов пользователей
def load_user_accounts(filename=ACCOUNTS_FILE) -> dict:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"Файл {filename} не найден или повреждён.")
        return {}

USER_ACCOUNTS = load_user_accounts()

# 🔐 Генерация Steam Guard кода
def get_steam_guard_code(shared_secret: str) -> str:
    timestamp = int(time.time())
    shared_secret_bytes = base64.b64decode(shared_secret)
    time_buffer = struct.pack(">Q", int(timestamp / 30))
    hmac_sha1 = hmac.new(shared_secret_bytes, time_buffer, hashlib.sha1).digest()
    start = hmac_sha1[19] & 0x0F
    full_code = struct.unpack(">I", hmac_sha1[start:start + 4])[0] & 0x7FFFFFFF

    chars = '23456789BCDFGHJKMNPQRTVWXY'
    code = ''
    for _ in range(5):
        code += chars[full_code % len(chars)]
        full_code //= len(chars)

    return code

# 🔐 Проверка доступа
def get_user_accounts(user_id: int):
    return USER_ACCOUNTS.get(str(user_id), [])

# 📤 Команда /guard
async def guard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    accounts = get_user_accounts(user_id)

    if not accounts:
        await update.message.reply_text("⛔ У тебя нет доступа или не привязаны аккаунты.")
        return

    response = "🔐 Steam Guard коды:\n\n"
    for acc in accounts:
        try:
            code = get_steam_guard_code(acc["shared_secret"])
            response += f"📛 *{acc['name']}*: `{code}`\n"
        except Exception as e:
            response += f"⚠️ Ошибка генерации для *{acc['name']}*\n"

    await update.message.reply_text(response, parse_mode="Markdown")

# 📘 Команда /help
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Команды:\n"
        "/start – Приветствие\n"
        "/guard – Получить Steam Guard коды\n"
        "/help – Показать это сообщение"
    )

# 👋 Команда /start
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я бот для генерации Steam Guard кодов.\nНапиши /help, чтобы увидеть список команд.")

# 🚀 Запуск бота
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("guard", guard_handler))
    app.add_handler(CommandHandler("help", help_handler))
    print("✅ Бот запущен.")
    return app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except RuntimeError as e:
        if str(e).startswith("Cannot close a running event loop"):
            loop = asyncio.get_event_loop()
            loop.create_task(run_bot())
            loop.run_forever()
        else:
            raise
