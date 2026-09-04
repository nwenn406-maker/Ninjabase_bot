import os
import logging
import asyncio
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import threading
import time

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado en Render")

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "OSINT Ninja Bot", "version": "4.0"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- COMANDOS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong!")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Función en desarrollo...")

# --- CONFIGURACIÓN DEL BOT ---
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("ping", ping))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIO DEL BOT EN SEGUNDO PLANO ---
def run_bot():
    """Inicia el bot de Telegram en un hilo separado"""
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    telegram_app.run_polling()

# --- INICIALIZACIÓN GLOBAL ---
# Iniciamos el bot en un hilo DAEMON para que no bloquee el servidor web
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    # Si se ejecuta directamente, iniciamos el servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
