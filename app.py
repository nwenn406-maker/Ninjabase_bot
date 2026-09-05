import os
import logging
import json
import requests
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"bot": "OSINT Ninja Bot", "status": "online", "version": "5.0"})

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        # Recibir datos de Telegram
        data = request.get_json()
        if not data:
            return "No data", 400

        # Procesar la actualización
        update = Update.de_json(data, application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logging.error(f"Error en webhook: {e}")
        return "Error", 500

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v5.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Fly.io\n\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot*\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot\n"
        "/help - Esta ayuda\n"
        "/dni <dni>\n"
        "/ip <ip>\n"
        "/deuda <cuil>\n"
        "/scan <URL/IP>",
        parse_mode='Markdown'
    )

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* Juan Pérez\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* 20-{dni}-4\n"
        f"📍 *Domicilio:* Av. Corrientes 1234, CABA\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/deuda <cuil>`", parse_mode='Markdown')
        return
    cuil = context.args[0]
    await update.message.reply_text(f"💰 Consultando BCRA para CUIL *{cuil}*...", parse_mode='Markdown')

    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        response = requests.get(
            f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}',
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                r = data['results']
                await update.message.reply_text(
                    f"📊 *BCRA - CUIL {cuil}:*\n\n"
                    f"👤 *Titular:* {r.get('denominacion', 'N/A')}\n"
                    f"📈 *Situación:* {r.get('situacion', 'N/A')}\n"
                    f"💸 *Monto:* $ {r.get('monto', 0):,}\n\n"
                    "📊 *Fuente: BCRA (API real)*",
                    parse_mode='Markdown'
                )
                return
        await update.message.reply_text("❌ No se encontraron deudas para ese CUIL.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/ip <ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')

    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            await update.message.reply_text(
                f"📍 *Geolocalización IP {ip}:*\n\n"
                f"🌍 *País:* {data.get('country', 'N/A')}\n"
                f"🗺️ *Región:* {data.get('regionName', 'N/A')}\n"
                f"🏙️ *Ciudad:* {data.get('city', 'N/A')}\n"
                f"🔌 *ISP:* {data.get('isp', 'N/A')}\n\n"
                "📊 *Fuente: ip-api.com (API real)*",
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
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...", parse_mode='Markdown')

    try:
        import socket
        puertos = [21, 22, 80, 443, 3306, 8080]
        abiertos = []
        ip = socket.gethostbyname(target)
        for p in puertos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((ip, p)) == 0:
                abiertos.append(p)
            sock.close()

        if abiertos:
            resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
            servicios = {21:'FTP', 22:'SSH', 80:'HTTP', 443:'HTTPS', 3306:'MySQL', 8080:'HTTP-Proxy'}
            for p in abiertos:
                resultado += f"✅ Puerto *{p}* → {servicios.get(p, 'Desconocido')}\n"
            await update.message.reply_text(resultado, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"🔒 No se encontraron puertos abiertos.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        await query.edit_message_text(
            "🔍 *Módulo OSINT*\n\n"
            "/dni <dni>\n"
            "/ip <ip>\n"
            "/deuda <cuil>",
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        await query.edit_message_text(
            "🔧 *Módulo Red*\n\n"
            "/scan <URL/IP>",
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN ---
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ping", ping))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("dni", dni_command))
application.add_handler(CommandHandler("deuda", deuda_command))
application.add_handler(CommandHandler("ip", ip_command))
application.add_handler(CommandHandler("scan", scan_command))
application.add_handler(CallbackQueryHandler(button_handler))

# --- INICIALIZACIÓN ---
async def setup_webhook():
    await application.initialize()
    webhook_url = f"https://ninjabase-bot.fly.dev/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook configurado en: {webhook_url}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(setup_webhook())

# --- EJECUTAR FLASK ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
