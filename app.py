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

# ⚠️ IMPORTANTE: El token se lee desde Render, NO está fijo en el código
TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado en Render")

# --- FLASK SERVER (Para mantener Render activo) ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "bot": "OSINT Ninja Bot",
        "version": "4.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- FUNCIONES ---

def geolocalizar_ip(ip):
    """Geolocaliza una IP usando ip-api.com (API real)"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'pais': data.get('country', 'N/A'),
                'region': data.get('regionName', 'N/A'),
                'ciudad': data.get('city', 'N/A'),
                'lat': data.get('lat', 'N/A'),
                'lon': data.get('lon', 'N/A'),
                'isp': data.get('isp', 'N/A'),
                'org': data.get('org', 'N/A'),
                'timezone': data.get('timezone', 'N/A'),
                'zip': data.get('zip', 'N/A')
            }
        return None
    except Exception as e:
        logging.error(f"Error en geolocalizar_ip: {e}")
        return None

def escanear_puertos(host):
    """Escanea puertos comunes en un host usando socket"""
    puertos = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 
               993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
    abiertos = []
    try:
        ip = socket.gethostbyname(host)
        for puerto in puertos:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                result = sock.connect_ex((ip, puerto))
                if result == 0:
                    abiertos.append(puerto)
                sock.close()
            except:
                continue
        return abiertos
    except Exception as e:
        logging.error(f"Error en escanear_puertos: {e}")
        return []

# --- DATOS SIMULADOS ---

NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía', 'Diego', 'Valentina']
APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez', 'García', 'Gómez', 'Díaz', 'Romero']
CIUDADES = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán', 'Mar del Plata', 'Santa Fe']
PROVINCIAS = ['Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza', 'Tucumán', 'Chaco', 'Neuquén', 'Salta']

def generar_dni():
    return f"{__import__('random').randint(10000000, 99999999)}"

def generar_cuil(dni=None):
    if not dni:
        dni = generar_dni()
    return f"20-{dni}-{__import__('random').randint(0, 9)}"

def generar_nombre_completo():
    return f"{__import__('random').choice(NOMBRES)} {__import__('random').choice(APELLIDOS)}"

def generar_domicilio():
    return f"{__import__('random').choice(['Av.', 'Calle'])} {__import__('random').choice(['Corrientes', 'Santa Fe', 'San Martín', '9 de Julio', 'Libertador', 'Belgrano'])} {__import__('random').randint(100, 5000)}"

# --- COMANDOS DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
        [InlineKeyboardButton("ℹ️ Info", callback_data='info_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Render\n"
        "🔹 *APIs integradas:*\n"
        "  • ip-api.com (geolocalización)\n"
        "  • Escaneo de puertos\n\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot*\n\n"
        "🔍 *OSINT:*\n"
        "/dni <dni> - Consulta RENAPER (simulado)\n"
        "/deuda <cuil> - Consulta deudores (simulado)\n"
        "/dnrpa <patente> - Buscar patente (simulado)\n"
        "/email <email> - Verificar filtraciones (API real)\n"
        "/ip <ip> - Geolocalización (API real)\n"
        "/titular <tel> - OSINT de teléfono (simulado)\n\n"
        "🔧 *Red y Seguridad:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios (simulado)\n\n"
        "📌 *Generales:*\n"
        "/start - Menú principal\n"
        "/help - Esta ayuda\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🏓 *Pong!*\n\n"
        f"🔹 Estado: 🟢 Activo\n"
        f"🔹 Servidor: Render\n"
        f"🔹 Hora: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode='Markdown'
    )

# --- COMANDOS OSINT ---

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    nombre = generar_nombre_completo()
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* {nombre}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* {generar_cuil(dni)}\n"
        f"📅 *Nacimiento:* {__import__('random').randint(1, 28)}/{__import__('random').randint(1, 12)}/{__import__('random').randint(1960, 2005)}\n"
        f"📍 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {__import__('random').choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {__import__('random').choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/deuda <cuil>`", parse_mode='Markdown')
        return
    cuil = context.args[0]
    await update.message.reply_text(
        f"📊 *Reporte Crediticio - CUIL {cuil}:*\n\n"
        f"📈 *Score:* {__import__('random').randint(300, 850)}\n"
        f"💸 *Deuda Total:* $ {__import__('random').randint(0, 500000):,}\n"
        f"🏦 *Entidades:* {__import__('random').choice(['Banco Nación', 'Banco Galicia', 'Banco Santander'])}\n"
        f"📊 *Situación:* {__import__('random').choice(['Normal', 'Riesgo bajo', 'Riesgo medio', 'Alto riesgo'])}\n"
        f"📅 *Actualización:* {datetime.now().strftime('%d/%m/%Y')}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/dnrpa <patente>`", parse_mode='Markdown')
        return
    patente = context.args[0].upper()
    await update.message.reply_text(
        f"🚘 *Datos DNRPA - Patente {patente}:*\n\n"
        f"🏭 *Marca:* {__import__('random').choice(['Toyota', 'Volkswagen', 'Ford', 'Chevrolet', 'Fiat', 'Peugeot'])}\n"
        f"🚗 *Modelo:* {__import__('random').choice(['Corolla', 'Golf', 'Focus', 'Cruze', 'Palio', '308'])}\n"
        f"📅 *Año:* {__import__('random').randint(2000, 2025)}\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI Titular:* {generar_dni()}\n"
        f"📍 *Radicación:* {__import__('random').choice(CIUDADES)}\n"
        f"🛡️ *Seguro:* {__import__('random').choice(['San Cristóbal', 'La Caja', 'Mapfre'])}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/email <email>`", parse_mode='Markdown')
        return
    email = context.args[0]
    await update.message.reply_text(f"📧 Verificando *{email}* en filtraciones...", parse_mode='Markdown')
    
    try:
        response = requests.get(
            f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
            timeout=10
        )
        if response.status_code == 200:
            breaches = response.json()
            texto = f"🔴 *{email}* apareció en {len(breaches)} filtraciones:\n\n"
            for b in breaches[:10]:
                texto += f"• *{b.get('Name', 'N/A')}* - {b.get('BreachDate', 'N/A')}\n"
            await update.message.reply_text(texto, parse_mode='Markdown')
        elif response.status_code == 404:
            await update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Error al consultar Have I Been Pwned.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/ip <dirección_ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')

    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ No se pudo geolocalizar la IP.", parse_mode='Markdown')
        return

    await update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"📌 *Coordenadas:* {datos['lat']}, {datos['lon']}\n"
        f"🔌 *ISP:* {datos['isp']}\n"
        f"🏢 *Organización:* {datos['org']}\n"
        f"🕐 *Zona Horaria:* {datos['timezone']}\n"
        "📊 *Datos de ip-api.com (API real)*",
        parse_mode='Markdown'
    )

async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/titular <número>`", parse_mode='Markdown')
        return
    telefono = context.args[0]
    await update.message.reply_text(
        f"📱 *Datos OSINT - Teléfono {telefono}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {generar_dni()}\n"
        f"📶 *Compañía:* {__import__('random').choice(['Movistar', 'Claro', 'Personal', 'Tuenti'])}\n"
        f"📍 *Provincia:* {__import__('random').choice(PROVINCIAS)}\n"
        f"🌐 *Redes asociadas (simuladas):*\n"
        f"  • WhatsApp: ✅ Sí\n"
        f"  • Instagram: @usuario\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

# --- COMANDOS DE RED Y SEGURIDAD ---

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')

    puertos = escanear_puertos(target)
    servicios = {
        21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
        80: 'HTTP', 110: 'POP3', 135: 'RPC', 139: 'NetBIOS', 143: 'IMAP',
        443: 'HTTPS', 445: 'SMB', 993: 'IMAPS', 995: 'POP3S',
        1723: 'PPTP', 3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL',
        5900: 'VNC', 8080: 'HTTP-Proxy', 8443: 'HTTPS-Alt'
    }

    if not puertos:
        await update.message.reply_text(
            f"🔒 No se encontraron puertos abiertos en *{target}*.",
            parse_mode='Markdown'
        )
        return

    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Uso: `/subdomain <URL>`", parse_mode='Markdown')
        return
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    subdominios = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog']
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in subdominios:
        resultado += f"🔹 {sub}.{domain}\n"
    resultado += "\n⚠️ *Datos simulados*"
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- MANEJADOR DE BOTONES ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔍 *Comandos OSINT:*\n\n"
            "/dni <dni>\n"
            "/deuda <cuil>\n"
            "/dnrpa <patente>\n"
            "/email <email>\n"
            "/ip <ip>\n"
            "/titular <tel>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Comandos Red y Seguridad:*\n\n"
            "/scan <URL/IP>\n"
            "/subdomain <URL>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'info_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "ℹ️ *Información del Bot*\n\n"
            "🔹 *Nombre:* OSINT Ninja Bot\n"
            "🔹 *Versión:* 4.0\n"
            "🔹 *Servidor:* Render\n"
            "🔹 *Estado:* 🟢 Activo\n\n"
            "📊 *APIs integradas:*\n"
            "✅ ip-api.com (geolocalización)\n"
            "✅ Have I Been Pwned (filtraciones)\n\n"
            "⚖️ *Bot 100% legal y educativo*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
            [InlineKeyboardButton("ℹ️ Info", callback_data='info_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "🔹 *Servidor:* Render\n\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---

telegram_app = ApplicationBuilder().token(TOKEN).build()

# Comandos
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("ping", ping_command))
telegram_app.add_handler(CommandHandler("dni", dni_command))
telegram_app.add_handler(CommandHandler("deuda", deuda_command))
telegram_app.add_handler(CommandHandler("dnrpa", dnrpa_command))
telegram_app.add_handler(CommandHandler("email", email_command))
telegram_app.add_handler(CommandHandler("ip", ip_command))
telegram_app.add_handler(CommandHandler("titular", titular_command))
telegram_app.add_handler(CommandHandler("scan", scan_command))
telegram_app.add_handler(CommandHandler("subdomain", subdomain_command))

# Manejador de botones
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIAR EL BOT EN SEGUNDO PLANO ---

import threading

def run_bot():
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    telegram_app.run_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
