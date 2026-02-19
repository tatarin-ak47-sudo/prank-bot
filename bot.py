import os
import logging
import random
import string
import sqlite3
import threading
import json
import requests
import shutil

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask, send_file, jsonify, request

# ==============================================
#    ТВОИ ДАННЫЕ
# ==============================================

TOKEN = "8512909123:AAH17VTMjpJyx1wK_6IvoPUsBgnd87qy6wg"
ADMIN_ID = 6767617758
SERVER_URL = "https://nfs-prikol-soundtag.netlify.app/"

# ==============================================
#    НАСТРОЙКИ
# ==============================================

DB_NAME = "prank_bot.db"
BASE_DIR = "prank_data"
os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ==============================================
#    БАЗА ДАННЫХ
# ==============================================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  join_date TEXT,
                  is_banned INTEGER DEFAULT 0)''')
    
    # Таблица для розыгрышей
    c.execute('''CREATE TABLE IF NOT EXISTS giveaways
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  creator_id INTEGER,
                  prize TEXT,
                  participants TEXT,
                  status TEXT,
                  created_at TEXT)''')
    
    conn.commit()
    conn.close()

# ==============================================
#    FLASK ПРИЛОЖЕНИЕ
# ==============================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Prank Bot is running!"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# ==============================================
#    TELEGRAM БОТ
# ==============================================

# Создаем приложение бота
application = Application.builder().token(TOKEN).build()

# ==============================================
#    КОМАНДЫ БОТА
# ==============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}!\n"
        f"Я пранк-бот. Что хочешь сделать?"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать\n"
        "/help - Помощь"
    )

# ==============================================
#    ЗАПУСК
# ==============================================

if name == "__main__":
    # Инициализируем базу данных
    init_db()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Порт из переменной окружения (Render дает его автоматически)
    port = int(os.environ.get('PORT', 10000))
    
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)).start()
    
    # Запускаем Telegram бота (polling)
    print("✅ Bot starting...")
    print(f"🌐 Flask server running on port {port}")
    application.run_polling()
