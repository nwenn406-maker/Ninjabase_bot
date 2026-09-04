import os
import logging
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado en Render")

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "OSINT Ninja Bot"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- COMANDOS DEL BOT ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text("🤖 Bot activo! Envía /ping para probar.")

def ping(update: Update, context: CallbackContext):
    update.message.reply_text("🏓 Pong!")

# --- CONFIGURACIÓN DEL BOT ---
def setup_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ping", ping))
    return updater

# --- INICIALIZACIÓN ---
if __name__ == '__main__':
    updater = setup_bot()
    updater.start_polling()
    print("🤖 Bot iniciado en Render")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
