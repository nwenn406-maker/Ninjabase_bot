import os
import logging
import asyncio
import threading
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import nest_asyncio

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
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Ayuda*\n\n"
        "/start - Menú\n"
        "/ping - Estado\n"
        "/dni <dni>\n"
        "/ip <ip>\n"
        "/scan <URL/IP>",
        parse_mode='Markdown'
    )

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados DNI {dni}:*\n\n"
        f"👤 *Nombre:* Juan Pérez\n"
        f"🆔 *DNI:* {dni}\n"
        f"📍 *Domicilio:* Av. Corrientes 1234, CABA\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/ip <dirección_ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')
    
    try:
        import requests
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            await update.message.reply_text(
                f"📍 *Geolocalización IP {ip}:*\n\n"
                f"🌍 *País:* {data.get('country', 'N/A')}\n"
                f"🗺️ *Región:* {data.get('regionName', 'N/A')}\n"
                f"🏙️ *Ciudad:* {data.get('city', 'N/A')}\n"
                f"🔌 *ISP:* {data.get('isp', 'N/A')}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ No se pudo geolocalizar.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    
    try:
        import socket
        puertos = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
        abiertos = []
        ip = socket.gethostbyname(target)
        for p in puertos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((ip, p)) == 0:
                abiertos.append(p)
            sock.close()
        
        servicios = {21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS', 80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP', 443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S', 1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL', 5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'}
        
        if abiertos:
            resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
            for p in abiertos:
                servicio = servicios.get(p, 'Desconocido')
                resultado += f"✅ Puerto *{p}* → {servicio}\n"
            await update.message.reply_text(resultado, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"🔒 No se encontraron puertos abiertos.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

# --- MANEJADOR DE BOTONES ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔍 *Módulo OSINT*\n\n"
            "/dni <dni>\n"
            "/ip <ip>\n"
            "/email <email>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red*\n\n"
            "/scan <URL/IP>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red", callback_data='security_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---
telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("ping", ping))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("dni", dni_command))
telegram_app.add_handler(CommandHandler("ip", ip_command))
telegram_app.add_handler(CommandHandler("scan", scan_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIAR EL BOT CON POLLING ---
def run_bot():
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    telegram_app.run_polling()

# --- INICIALIZACIÓN ---
if __name__ == '__main__':
    # Iniciamos el bot en un hilo separado
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    # Iniciamos el servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
