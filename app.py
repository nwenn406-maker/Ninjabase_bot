import os
import logging
import random
import requests
import socket
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading
import asyncio

# --- CONFIGURACIÓN ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# --- FLASK SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "online", "bot": "OSINT Ninja Bot", "version": "5.0"})

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# --- FUNCIONES DE APIS ---
def geolocalizar_ip(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {'pais': data.get('country'), 'region': data.get('regionName'), 'ciudad': data.get('city'), 'isp': data.get('isp')}
        return None
    except: return None

def verificar_email_breach(email):
    try:
        response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', timeout=10)
        if response.status_code == 200:
            return [b.get('Name') for b in response.json()]
        elif response.status_code == 404:
            return []
        return None
    except: return None

def consultar_deuda_bcra(cuil):
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        response = requests.get(f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}', timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                resultado = data['results']
                return {
                    'denominacion': resultado.get('denominacion', 'N/A'),
                    'periodo': resultado.get('periodo', 'N/A'),
                    'situacion': resultado.get('situacion', 'N/A'),
                    'monto': resultado.get('monto', 0),
                    'entidades': resultado.get('entidades', [])
                }
        return None
    except: return None

def escanear_puertos(host):
    puertos = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
    abiertos = []
    try:
        ip = socket.gethostbyname(host)
        for puerto in puertos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((ip, puerto)) == 0:
                abiertos.append(puerto)
            sock.close()
        return abiertos
    except: return []

def descubrir_subdominios(dominio):
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop']
    encontrados = []
    for sub in subdominios_comunes:
        if random.random() > 0.5:
            encontrados.append(f"{sub}.{dominio}")
    return encontrados[:8]

# --- DATOS SIMULADOS ---
NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía']
APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez']
CIUDADES = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán']
PROVINCIAS = ['Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza']
COMPANIAS = ['Movistar', 'Claro', 'Personal', 'Tuenti']

def generar_dni(): return f"{random.randint(10000000, 99999999)}"
def generar_cuil(dni=None):
    if not dni: dni = generar_dni()
    return f"20-{dni}-{random.randint(0, 9)}"
def generar_nombre_completo(): return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
def generar_domicilio(): return f"{random.choice(['Av.', 'Calle'])} {random.choice(['Corrientes', 'Santa Fe', 'San Martín', '9 de Julio'])} {random.randint(100, 5000)}"

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
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
        "🔍 *OSINT:*\n"
        "/dni <dni> - RENAPER (simulado)\n"
        "/deuda <cuil> - BCRA (API real)\n"
        "/email <email> - Have I Been Pwned\n"
        "/ip <ip> - ip-api.com\n"
        "/titular <tel> - OSINT teléfono\n"
        "/dnrpa <patente> - DNRPA (simulado)\n\n"
        "🔧 *Red y Seguridad:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* {generar_cuil(dni)}\n"
        f"📍 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/deuda <cuil>`", parse_mode='Markdown')
        return
    cuil = context.args[0]
    await update.message.reply_text(f"💰 Consultando BCRA para CUIL *{cuil}*...", parse_mode='Markdown')
    
    resultado = consultar_deuda_bcra(cuil)
    if not resultado:
        await update.message.reply_text("❌ No se pudo obtener información del BCRA.", parse_mode='Markdown')
        return
    
    situacion_map = {'1': 'Normal', '2': 'Riesgo bajo', '3': 'Riesgo medio', '4': 'Alto riesgo', '5': 'Irrecuperable'}
    situacion_texto = situacion_map.get(str(resultado.get('situacion', '')), 'N/A')
    
    await update.message.reply_text(
        f"📊 *Central de Deudores BCRA - CUIL {cuil}:*\n\n"
        f"👤 *Titular:* {resultado.get('denominacion', 'N/A')}\n"
        f"📈 *Situación:* {situacion_texto}\n"
        f"💸 *Monto:* $ {resultado.get('monto', 0):,}\n"
        f"📅 *Periodo:* {resultado.get('periodo', 'N/A')}\n\n"
        "📊 *Fuente: BCRA - API pública*",
        parse_mode='Markdown'
    )

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/email <email>`", parse_mode='Markdown')
        return
    email = context.args[0]
    await update.message.reply_text(f"📧 Verificando *{email}*...", parse_mode='Markdown')
    
    breaches = verificar_email_breach(email)
    if breaches is None:
        await update.message.reply_text("❌ Error al verificar.", parse_mode='Markdown')
        return
    
    if breaches:
        texto = f"🔴 *{email}* apareció en {len(breaches)} filtraciones:\n\n"
        for b in breaches[:10]:
            texto += f"• {b}\n"
        await update.message.reply_text(texto, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/ip <ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')
    
    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ No se pudo geolocalizar.", parse_mode='Markdown')
        return
    
    await update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"🔌 *ISP:* {datos['isp']}",
        parse_mode='Markdown'
    )

async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/titular <tel>`", parse_mode='Markdown')
        return
    telefono = context.args[0]
    await update.message.reply_text(
        f"📱 *Datos Teléfono {telefono}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {generar_dni()}\n"
        f"📶 *Compañía:* {random.choice(COMPANIAS)}\n"
        f"📍 *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    
    puertos = escanear_puertos(target)
    servicios = {21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS', 80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP', 443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S', 1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL', 5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'}
    
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos.", parse_mode='Markdown')
        return
    
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/subdomain <URL>`", parse_mode='Markdown')
        return
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    subdominios = descubrir_subdominios(domain)
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in subdominios:
        resultado += f"🔹 {sub}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dnrpa <patente>`", parse_mode='Markdown')
        return
    patente = context.args[0].upper()
    await update.message.reply_text(
        f"🚘 *Datos DNRPA - Patente {patente}:*\n\n"
        f"🏭 *Marca:* {random.choice(['Toyota', 'Volkswagen', 'Ford'])}\n"
        f"🚗 *Modelo:* {random.choice(['Corolla', 'Golf', 'Focus'])}\n"
        f"📅 *Año:* {random.randint(2000, 2025)}\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"📍 *Radicación:* {random.choice(CIUDADES)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

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
            "/deuda <cuil>\n"
            "/email <email>\n"
            "/ip <ip>\n"
            "/titular <tel>\n"
            "/dnrpa <patente>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad*\n\n"
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
            "🕵️ *OSINT Ninja Bot v5.0*\n\n"
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
telegram_app.add_handler(CommandHandler("deuda", deuda_command))
telegram_app.add_handler(CommandHandler("dnrpa", dnrpa_command))
telegram_app.add_handler(CommandHandler("email", email_command))
telegram_app.add_handler(CommandHandler("ip", ip_command))
telegram_app.add_handler(CommandHandler("titular", titular_command))
telegram_app.add_handler(CommandHandler("scan", scan_command))
telegram_app.add_handler(CommandHandler("subdomain", subdomain_command))
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# --- INICIO DEL BOT ---
def run_bot():
    print("🤖 OSINT Ninja Bot v5.0 iniciado en Fly.io")
    telegram_app.run_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
