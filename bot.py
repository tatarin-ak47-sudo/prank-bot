import os
import logging
import random
import string
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
import shutil
from flask import Flask, send_file, jsonify, request
import threading
import json

# ============================================
# ============ ТВОИ ДАННЫЕ ==================
# ============================================
TOKEN = "8512909123:AAHI7VTmjpJyx1wK_G1voPUsBgnd87qy6wg"
ADMIN_ID = 6767617758
SERVER_URL = "https://nfs-prikol-soundtag.netlify.app/"

# ============================================
# ============ НАСТРОЙКИ =====================
# ============================================
DB_NAME = "prank_bot.db"
BASE_DIR = "prank_data"
os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ============ БАЗА ДАННЫХ ===================
# ============================================
def init_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS tags
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tag_id TEXT UNIQUE,
                  password TEXT,
                  is_activated BOOLEAN DEFAULT 0,
                  owner_id INTEGER,
                  created_by INTEGER,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (tag_id TEXT PRIMARY KEY,
                  detonation_enabled BOOLEAN DEFAULT 0,
                  updated_at TEXT)''')
    
    conn.commit()
    conn.close()

def generate_tag_id():
    letters = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"metka_{letters}"

def generate_password():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choices(chars, k=8))

def create_tags(count, admin_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    tags = []
    for _ in range(count):
        tag_id = generate_tag_id()
        password = generate_password()
        created_at = datetime.now().isoformat()
        
        try:
            c.execute("INSERT INTO tags (tag_id, password, created_by, created_at) VALUES (?, ?, ?, ?)",
                     (tag_id, password, admin_id, created_at))
            c.execute("INSERT INTO settings (tag_id, detonation_enabled, updated_at) VALUES (?, ?, ?)",
                     (tag_id, 0, created_at))
            tags.append((tag_id, password))
        except:
            continue
    
    conn.commit()
    conn.close()
    return tags

def activate_tag(tag_id, password, user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT * FROM tags WHERE tag_id = ? AND password = ? AND is_activated = 0", 
              (tag_id, password))
    tag = c.fetchone()
    
    if tag:
        c.execute("UPDATE tags SET is_activated = 1, owner_id = ? WHERE tag_id = ?",
                  (user_id, tag_id))
        
        user_folder = os.path.join(BASE_DIR, str(user_id))
        os.makedirs(user_folder, exist_ok=True)
        
        default_image = os.path.join(BASE_DIR, "default_image.jpg")
        default_sound = os.path.join(BASE_DIR, "default_sound.mp3")
        
        if os.path.exists(default_image):
            shutil.copy(default_image, os.path.join(user_folder, "current_image.jpg"))
        if os.path.exists(default_sound):
            shutil.copy(default_sound, os.path.join(user_folder, "current_sound.mp3"))
        
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def get_user_tags(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT tag_id FROM tags WHERE owner_id = ?", (user_id,))
    tags = c.fetchall()
    conn.close()
    return [tag[0] for tag in tags]

def get_owner_by_tag(tag_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT owner_id FROM tags WHERE tag_id = ? AND is_activated = 1", (tag_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def set_detonation(tag_id, enabled):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE settings SET detonation_enabled = ?, updated_at = ? WHERE tag_id = ?",
              (1 if enabled else 0, datetime.now().isoformat(), tag_id))
    conn.commit()
    conn.close()

def get_detonation(tag_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT detonation_enabled FROM settings WHERE tag_id = ?", (tag_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else False

# ============================================
# ============ ВЕБ-СЕРВЕР ====================
# ============================================
app = Flask(__name__)

@app.route('/get_image/<tag_id>')
def get_image(tag_id):
    owner_id = get_owner_by_tag(tag_id)
    
    if owner_id:
        image_path = os.path.join(BASE_DIR, str(owner_id), "current_image.jpg")
        if os.path.exists(image_path):
            return send_file(image_path)
    
    default = os.path.join(BASE_DIR, "default_image.jpg")
    if os.path.exists(default):
        return send_file(default)
    return "No image", 404

@app.route('/get_sound/<tag_id>')
def get_sound(tag_id):
    owner_id = get_owner_by_tag(tag_id)
    
    if owner_id:
        sound_path = os.path.join(BASE_DIR, str(owner_id), "current_sound.mp3")
        if os.path.exists(sound_path):
            return send_file(sound_path)
    
    default = os.path.join(BASE_DIR, "default_sound.mp3")
    if os.path.exists(default):
        return send_file(default)
    return "No sound", 404

@app.route('/detonation_status/<tag_id>')
def detonation_status(tag_id):
    enabled = get_detonation(tag_id)
    return jsonify({"enabled": enabled})

@app.route('/click/<tag_id>', methods=['POST'])
def click(tag_id):
    print(f"Клик по метке {tag_id}")
    return jsonify({"status": "ok"})

@app.route('/trigger/<tag_id>', methods=['POST'])
def trigger(tag_id):
    print(f"Детонация для метки {tag_id}!")
    return jsonify({"status": "detonation_sent"})

@app.route('/health')
def health():
    return jsonify({"status": "alive"})
def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


# ============================================
# ============ БОТ ===========================
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("🔌 Подключить метку", callback_data="connect")],
    ]
    
    tags = get_user_tags(user_id)
    if tags:
        for tag in tags[:5]:
            keyboard.append([InlineKeyboardButton(f"🎮 Метка {tag}", callback_data=f"manage_{tag}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Добро пожаловать в PrankMaster!\n\n"
        "У тебя есть NFC-метка? Подключи её по логину и паролю с бумажки.",
        reply_markup=reply_markup
    )

async def admin_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора!")
        return
    
    try:
        count = int(context.args[0]) if context.args else 15
        if count > 100:
            await update.message.reply_text("Максимум 100 меток за раз")
            return
    except:
        await update.message.reply_text("Использование: /create 15")
        return
    
    tags = create_tags(count, ADMIN_ID)
    
    result = f"✅ Создано {len(tags)} новых меток!\n\n"
    result += "📋 Данные для печати:\n\n"
    
    for i, (tag_id, password) in enumerate(tags, 1):
        result += f"Метка #{i}\n"
        result += f"Логин: {tag_id}\n"
        result += f"Пароль: {password}\n"
        result += f"Ссылка: {SERVER_URL}/?tag={tag_id}\n\n"
    
    result += "⚠️ После печати УДАЛИ ЭТО СООБЩЕНИЕ!"
    
    await update.message.reply_text(result)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "connect":
        await query.edit_message_text(
            "🔌 Введи логин и пароль с бумажки через пробел:\n\n"
            "Например: `metka_A7F3 2xR9#kP5`",
            parse_mode="Markdown"
        )
        context.user_data['waiting_for'] = 'activation'
    
    elif data.startswith("manage_"):
        tag_id = data.replace("manage_", "")
        await show_tag_menu(query, tag_id, context)
    
    elif data.startswith("det_"):
        tag_id = data.replace("det_", "")
        await show_detonation_menu(query, tag_id, context)
    
    elif data.startswith("det_on_"):
        tag_id = data.replace("det_on_", "")
        set_detonation(tag_id, True)
        await query.edit_message_text(f"✅ Детонация для {tag_id} ВКЛЮЧЕНА")
    
    elif data.startswith("det_off_"):
        tag_id = data.replace("det_off_", "")
        set_detonation(tag_id, False)
        await query.edit_message_text(f"✅ Детонация для {tag_id} ВЫКЛЮЧЕНА")
    
    elif data.startswith("trigger_"):
        tag_id = data.replace("trigger_", "")
        requests.post(f"http://localhost:5000/trigger/{tag_id}")
        await query.edit_message_text(f"💣 БАБАХ! Детонация для {tag_id} отправлена!")

async def show_tag_menu(query, tag_id, context):
    keyboard = [
        [InlineKeyboardButton("🖼 Сменить картинку", callback_data=f"img_{tag_id}")],
        [InlineKeyboardButton("🔊 Сменить звук", callback_data=f"snd_{tag_id}")],
        [InlineKeyboardButton("🔄 Сбросить картинку", callback_data=f"reset_img_{tag_id}")],
        [InlineKeyboardButton("🔄 Сбросить звук", callback_data=f"reset_snd_{tag_id}")],
        [InlineKeyboardButton("💣 Настройки детонации", callback_data=f"det_{tag_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"🎮 Управление меткой {tag_id}:", reply_markup=reply_markup)

async def show_detonation_menu(query, tag_id, context):
    current = get_detonation(tag_id)
    status = "ВКЛ" if current else "ВЫКЛ"
    
    keyboard = [
        [InlineKeyboardButton(f"🔴 Включить детонацию", callback_data=f"det_on_{tag_id}")],
        [InlineKeyboardButton(f"⚪ Выключить детонацию", callback_data=f"det_off_{tag_id}")],
        [InlineKeyboardButton(f"💥 Запустить детонацию СЕЙЧАС", callback_data=f"trigger_{tag_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"manage_{tag_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"💣 Детонация для {tag_id}\n"
        f"Текущий статус: {status}\n\n"
        f"• Если детонация ВКЛ - звук не играет сразу, только по команде\n"
        f"• Если детонация ВЫКЛ - звук играет сразу при клике",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_for') == 'activation':
        text = update.message.text.strip()
        parts = text.split()
        
        if len(parts) == 2:
            tag_id, password = parts
            
            if activate_tag(tag_id, password, user_id):
                await update.message.reply_text(
                    f"✅ Метка {tag_id} успешно активирована!\n\n"
                    f"Теперь ты можешь управлять ей через меню."
                )
            else:
                await update.message.reply_text(
                    "❌ Неверный логин/пароль или метка уже активирована!"
                )
        else:
            await update.message.reply_text("Нужно ввести логин и пароль через пробел")
        
        context.user_data['waiting_for'] = None
        return
    
    waiting_for = context.user_data.get('waiting_for')
    if waiting_for and waiting_for.startswith('img_'):
        tag_id = waiting_for.replace('img_', '')
        owner_id = get_owner_by_tag(tag_id)
        
        if owner_id and owner_id == user_id:
            if update.message.photo:
                file = await update.message.photo[-1].get_file()
                user_folder = os.path.join(BASE_DIR, str(user_id))
                await file.download_to_drive(os.path.join(user_folder, "current_image.jpg"))
                await update.message.reply_text("✅ Картинка обновлена!")
            elif update.message.document:
                file = await update.message.document.get_file()
                user_folder = os.path.join(BASE_DIR, str(user_id))
                await file.download_to_drive(os.path.join(user_folder, "current_image.jpg"))
                await update.message.reply_text("✅ Картинка обновлена!")
            else:
                await update.message.reply_text("Пришли картинку как фото или файл")
        
        context.user_data['waiting_for'] = None
    
    elif waiting_for and waiting_for.startswith('snd_'):
        tag_id = waiting_for.replace('snd_', '')
        owner_id = get_owner_by_tag(tag_id)
        
        if owner_id and owner_id == user_id:
            if update.message.document:
                file = await update.message.document.get_file()
                user_folder = os.path.join(BASE_DIR, str(user_id))
                await file.download_to_drive(os.path.join(user_folder, "current_sound.mp3"))
                await update.message.reply_text("✅ Звук обновлён!")
            else:
                await update.message.reply_text("Пришли звук как файл MP3")
        
        context.user_data['waiting_for'] = None

# ============================================
# ============ ЗАПУСК ========================
# ============================================
def main():
    init_database()
    os.makedirs(BASE_DIR, exist_ok=True)
    
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("🌐 Веб-сервер запущен")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("create", admin_create))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL | filters.TEXT, handle_message))
    
    print("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
