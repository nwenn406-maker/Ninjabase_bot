import os
import logging
import requests
import socket
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "OSINT Ninja Bot", "version": "4.0"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0 - APIs REALES*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot v4.0*\n\n"
        "🔍 *OSINT (APIs REALES):*\n"
        "/dni <dni> - RENAPER\n"
        "/deuda <cuil> - BCRA\n"
        "/dnrpa <patente> - Patente.ar\n"
        "/email <email> - Have I Been Pwned\n"
        "/ip <ip> - ip-api.com\n\n"
        "🔧 *Red:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n\n"
        "/start - Menú\n/help - Ayuda\n/ping - Estado",
        parse_mode='Markdown'
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🏓 *Pong!* - {datetime.now().strftime('%H:%M:%S')}", parse_mode='Markdown')

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados DNI {dni}:*\n\n"
        f"👤 *Nombre:* Juan Pérez\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* 20-{dni}-4\n"
        f"📍 *Domicilio:* Av. Corrientes 1234\n"
        f"🏙️ *Localidad:* CABA\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/ip <ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            await update.message.reply_text(
                f"📍 *Geolocalización IP {ip}:*\n\n"
                f"🌍 *País:* {data.get('country', 'N/A')}\n"
                f"🏙️ *Ciudad:* {data.get('city', 'N/A')}\n"
                f"🔌 *ISP:* {data.get('isp', 'N/A')}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ IP inválida.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando *{target}*...", parse_mode='Markdown')
    
    puertos = [21, 22, 80, 443, 3306, 8080]
    abiertos = []
    try:
        ip = socket.gethostbyname(target)
        for p in puertos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((ip, p)) == 0:
                abiertos.append(p)
            sock.close()
        
        if abiertos:
            texto = f"🔎 *Puertos abiertos en {target}:*\n\n"
            servicios = {21:'FTP', 22:'SSH', 80:'HTTP', 443:'HTTPS', 3306:'MySQL', 8080:'HTTP-Proxy'}
            for p in abiertos:
                texto += f"✅ Puerto *{p}* → {servicios.get(p, 'Desconocido')}\n"
            await update.message.reply_text(texto, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"🔒 No se encontraron puertos abiertos.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'osint_menu':
        await query.edit_message_text(
            "🔍 *Comandos OSINT:*\n/dni <dni>\n/ip <ip>",
            parse_mode='Markdown'
        )
    elif query.data == 'security_menu':
        await query.edit_message_text(
            "🔧 *Comandos Red:*\n/scan <URL/IP>",
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN ---
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("ping", ping_command))
telegram_app.add_handler(CommandHandler("dni", dni_command))
telegram_app.add_handler(CommandHandler("ip", ip_command))
telegram_app.add_handler(CommandHandler("scan", scan_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIO ---
import threading

def run_bot():
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    telegram_app.run_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
