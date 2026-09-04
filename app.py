import os
import logging
import asyncio
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

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
    """Muestra el menú principal con botones interactivos"""
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
        [InlineKeyboardButton("❓ Ayuda", callback_data='help_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Render\n\n"
        "Selecciona una categoría:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde al comando /ping"""
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo y funcionando correctamente.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la ayuda con todos los comandos disponibles"""
    await update.message.reply_text(
        "📖 *Ayuda - OSINT Ninja Bot*\n\n"
        "🔍 *Comandos OSINT:*\n"
        "/dni <dni> - Consulta RENAPER (simulado)\n"
        "/deuda <cuil> - Consulta deudores (simulado)\n"
        "/ip <ip> - Geolocalización (API real)\n"
        "/email <email> - Verificar filtraciones (API real)\n\n"
        "🔧 *Comandos de Red:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Descubrir subdominios\n\n"
        "📌 *Generales:*\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot\n"
        "/help - Esta ayuda",
        parse_mode='Markdown'
    )

# --- FUNCIONES DE OSINT ---

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simula una consulta de DNI"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* Juan Pérez\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* 20-{dni}-4\n"
        f"📅 *Nacimiento:* 15/03/1985\n"
        f"📍 *Domicilio:* Av. Corrientes 1234, CABA\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geolocaliza una IP usando ip-api.com (API real)"""
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
                f"📌 *Coordenadas:* {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}\n"
                f"🔌 *ISP:* {data.get('isp', 'N/A')}\n"
                "📊 *Datos de ip-api.com (API real)*",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ No se pudo geolocalizar la IP.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

# --- FUNCIONES DE RED ---

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Escanea puertos comunes en un host"""
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
            await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en *{target}*.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

# --- MANEJADOR DE BOTONES ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las pulsaciones de los botones del menú"""
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [
            [InlineKeyboardButton("📄 /dni <dni>", callback_data='cmd_dni')],
            [InlineKeyboardButton("📍 /ip <ip>", callback_data='cmd_ip')],
            [InlineKeyboardButton("📧 /email <email>", callback_data='cmd_email')],
            [InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')],
        ]
        await query.edit_message_text(
            "🔍 *Módulo OSINT*\n\n"
            "Selecciona un comando para más información:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'security_menu':
        keyboard = [
            [InlineKeyboardButton("🔎 /scan <URL/IP>", callback_data='cmd_scan')],
            [InlineKeyboardButton("🌐 /subdomain <URL>", callback_data='cmd_subdomain')],
            [InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')],
        ]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad*\n\n"
            "Selecciona un comando para más información:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'help_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "📖 *Ayuda - OSINT Ninja Bot*\n\n"
            "🔍 *Comandos OSINT:*\n"
            "/dni <dni> - Consulta RENAPER (simulado)\n"
            "/deuda <cuil> - Consulta deudores (simulado)\n"
            "/ip <ip> - Geolocalización (API real)\n"
            "/email <email> - Verificar filtraciones (API real)\n\n"
            "🔧 *Comandos de Red:*\n"
            "/scan <URL/IP> - Escaneo de puertos\n"
            "/subdomain <URL> - Descubrir subdominios\n\n"
            "📌 *Generales:*\n"
            "/start - Menú principal\n"
            "/ping - Estado del bot\n"
            "/help - Esta ayuda",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
            [InlineKeyboardButton("❓ Ayuda", callback_data='help_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "🔹 *Servidor:* Render\n\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action.startswith('cmd_'):
        cmd_name = action[4:]
        mensajes = {
            'dni': "📄 `/dni <dni>`\n\nEjemplo: `/dni 12345678`\nConsulta simulada de RENAPER.",
            'ip': "📍 `/ip <dirección_ip>`\n\nEjemplo: `/ip 8.8.8.8`\nGeolocaliza una IP usando ip-api.com (API real).",
            'email': "📧 `/email <email>`\n\nEjemplo: `/email correo@ejemplo.com`\nVerifica si el email apareció en filtraciones (API real).",
            'scan': "🔎 `/scan <URL/IP>`\n\nEjemplo: `/scan google.com`\nEscanea puertos comunes en un host.",
            'subdomain': "🌐 `/subdomain <URL>`\n\nEjemplo: `/subdomain google.com`\nDescubre subdominios de un dominio."
        }
        texto = mensajes.get(cmd_name, "Comando no reconocido")
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='osint_menu' if cmd_name in ['dni', 'ip', 'email'] else 'security_menu')]]
        await query.edit_message_text(
            f"📌 *Ayuda del comando:*\n\n{texto}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("ping", ping))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("dni", dni_command))
telegram_app.add_handler(CommandHandler("ip", ip_command))
telegram_app.add_handler(CommandHandler("scan", scan_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIO DEL BOT CON EVENT LOOP CORRECTO ---
def run_bot():
    """Inicia el bot de Telegram en un hilo separado con su propio event loop"""
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(telegram_app.initialize())
        loop.run_until_complete(telegram_app.start())
        loop.run_until_complete(telegram_app.updater.start_polling())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(telegram_app.shutdown())
        loop.close()

# --- INICIALIZACIÓN GLOBAL ---
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
