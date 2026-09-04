import os
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN no configurado")

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot activo. Envía /ping para probar.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong!")

# --- CONFIGURACIÓN ---
bot_app = Application.builder().token(TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("ping", ping))

# --- INICIO ---
if __name__ == '__main__':
    import threading
    def run_bot():
        print("🤖 Bot iniciado")
        bot_app.run_polling()
    
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
