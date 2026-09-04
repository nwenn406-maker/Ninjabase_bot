import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado en Render")

# --- FLASK SERVER (Para que Render no se duerma) ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "OSINT Ninja Bot", "version": "4.0"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- COMANDOS DEL BOT (igual que antes) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo y funcionando correctamente.", parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔍 *Módulo OSINT*\n\n"
            "Comandos disponibles:\n"
            "/dni <dni>\n"
            "/ip <ip>\n"
            "/email <email>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad*\n\n"
            "Comandos disponibles:\n"
            "/scan <URL/IP>\n"
            "/subdomain <URL>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---
# NOTA: No se ejecuta automáticamente. Se usará un Webhook.
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ping", ping))
application.add_handler(CallbackQueryHandler(button_handler))

# --- RUTA DEL WEBHOOK ---
@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    """Maneja las actualizaciones entrantes de Telegram."""
    try:
        update = Update.de_json(request.get_json(), application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logging.error(f"Error en webhook: {e}")
        return "Error", 500

# --- FUNCIÓN PARA CONFIGURAR EL WEBHOOK ---
async def set_webhook():
    """Configura el webhook con la URL pública de la aplicación."""
    # Obtiene la URL pública de Render desde las variables de entorno
    webhook_url = f"https://{os.getenv('RENDER_SERVICE_NAME', 'localhost')}.onrender.com/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook configurado en: {webhook_url}")

# --- INICIALIZACIÓN DEL BOT Y WEBHOOK ---
# Esta parte se ejecuta solo una vez, cuando se inicia el servidor Flask.
# Asegura que el webhook se configure al inicio.
with application:
    # Necesitamos un loop de asyncio para ejecutar la función asíncrona
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(set_webhook())
        logging.info("✅ Bot y Webhook configurados correctamente.")
    except Exception as e:
        logging.error(f"Error al configurar el bot: {e}")
    finally:
        loop.close()

if __name__ == '__main__':
    # Este bloque se ejecuta si ejecutas el script directamente.
    # Útil para pruebas locales, pero Render usará el servidor Flask de arriba.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
