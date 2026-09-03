import os
import logging
import random
import requests
import socket
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== CONFIGURACIÓN ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado en Render")

# ==================== FLASK SERVER ====================
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "bot": "Ninjabase Bot",
        "version": "4.0",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

# ==================== FUNCIONES AUXILIARES ====================

def geolocalizar_ip(ip):
    """Geolocaliza una IP usando ip-api.com"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'pais': data.get('country', 'N/A'),
                'region': data.get('regionName', 'N/A'),
                'ciudad': data.get('city', 'N/A'),
                'isp': data.get('isp', 'N/A'),
                'org': data.get('org', 'N/A')
            }
        return None
    except:
        return None

def verificar_breach(email):
    """Verifica filtraciones usando Have I Been Pwned"""
    try:
        response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', timeout=10)
        if response.status_code == 200:
            return [b.get('Name', 'Desconocido') for b in response.json()]
        elif response.status_code == 404:
            return []
        return None
    except:
        return None

def escanear_puertos(host):
    """Escanea puertos comunes usando socket"""
    puertos = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
    abiertos = []
    try:
        ip = socket.gethostbyname(host)
        for p in puertos:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            if sock.connect_ex((ip, p)) == 0:
                abiertos.append(p)
            sock.close()
        return abiertos
    except:
        return []

# ==================== DATOS SIMULADOS ====================
NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía', 'Diego', 'Valentina']
APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez', 'García', 'Gómez', 'Díaz', 'Romero']
CIUDADES = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán', 'Mar del Plata', 'Santa Fe']
PROVINCIAS = ['Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza', 'Tucumán', 'Chaco', 'Neuquén', 'Salta']
EMPRESAS = ['Toyota', 'Volkswagen', 'Ford', 'Chevrolet', 'Fiat', 'Peugeot', 'Renault', 'Nissan']
MODELOS = ['Corolla', 'Golf', 'Focus', 'Cruze', 'Palio', '308', 'Sandero', 'Sentra']
COMPANIAS = ['Movistar', 'Claro', 'Personal', 'Tuenti']
SERVICIOS_PUERTOS = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS',
    80: 'HTTP', 110: 'POP3', 139: 'NetBIOS', 143: 'IMAP',
    443: 'HTTPS', 445: 'SMB', 993: 'IMAPS', 995: 'POP3S',
    1723: 'PPTP', 3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL',
    5900: 'VNC', 8080: 'HTTP-Proxy', 8443: 'HTTPS-Alt'
}

def generar_dni():
    return f"{random.randint(10000000, 99999999)}"

def generar_cuil(dni=None):
    if not dni:
        dni = generar_dni()
    return f"20-{dni}-{random.randint(0, 9)}"

def generar_nombre():
    return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"

def generar_domicilio():
    return f"{random.choice(['Av.', 'Calle'])} {random.choice(['Corrientes', 'Santa Fe', 'San Martín', '9 de Julio', 'Libertador', 'Belgrano'])} {random.randint(100, 5000)}"

def generar_patente():
    if random.choice([True, False]):
        return f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}"
    else:
        return f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(10, 99)}"

# ==================== COMANDOS DEL BOT ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Menú principal"""
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
        [InlineKeyboardButton("ℹ️ Info del Bot", callback_data='info_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *Ninjabase Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Render\n"
        "🔹 *Comandos disponibles:* /help\n\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Lista de comandos"""
    await update.message.reply_text(
        "🕵️ *Ninjabase Bot - Comandos:*\n\n"
        "🔍 *OSINT:*\n"
        "/dni <dni> - Consultar DNI\n"
        "/deuda <cuil> - Consultar deudas\n"
        "/dnrpa <patente> - Consultar patente\n"
        "/email <email> - Verificar filtraciones\n"
        "/ip <ip> - Geolocalizar IP\n"
        "/titular <tel> - OSINT teléfono\n\n"
        "🔧 *Red:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
        "📌 *Generales:*\n"
        "/start - Menú principal\n"
        "/help - Esta ayuda\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ping - Verificar estado"""
    await update.message.reply_text(
        f"🏓 *Pong!*\n\n"
        f"🔹 Estado: 🟢 Activo\n"
        f"🔹 Servidor: Render\n"
        f"🔹 Hora: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode='Markdown'
    )

# --- MÓDULO OSINT ---

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dni <dni> - Consulta DNI (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    nombre = generar_nombre()
    await update.message.reply_text(
        f"📄 *Resultados DNI {dni}:*\n\n"
        f"👤 *Nombre:* {nombre}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* {generar_cuil(dni)}\n"
        f"📅 *Nacimiento:* {random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(1960, 2005)}\n"
        f"📍 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados - Demostración educativa*",
        parse_mode='Markdown'
    )

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/deuda <cuil> - Consulta deudas (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/deuda <cuil>`", parse_mode='Markdown')
        return
    cuil = context.args[0]
    await update.message.reply_text(
        f"📊 *Reporte Crediticio - CUIL {cuil}:*\n\n"
        f"📈 *Score:* {random.randint(300, 850)}\n"
        f"💸 *Deuda Total:* $ {random.randint(0, 500000):,}\n"
        f"🏦 *Entidades:* {random.choice(['Banco Nación', 'Banco Galicia', 'Banco Santander'])}\n"
        f"📊 *Situación:* {random.choice(['Normal', 'Riesgo bajo', 'Riesgo medio', 'Alto riesgo'])}\n"
        f"📅 *Actualización:* {datetime.now().strftime('%d/%m/%Y')}\n\n"
        "⚠️ *Datos simulados - Demostración educativa*",
        parse_mode='Markdown'
    )

async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/dnrpa <patente> - Consulta patente (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/dnrpa <patente>`", parse_mode='Markdown')
        return
    patente = context.args[0].upper()
    await update.message.reply_text(
        f"🚘 *Datos DNRPA - Patente {patente}:*\n\n"
        f"🏭 *Marca:* {random.choice(EMPRESAS)}\n"
        f"🚗 *Modelo:* {random.choice(MODELOS)}\n"
        f"📅 *Año:* {random.randint(2000, 2025)}\n"
        f"👤 *Titular:* {generar_nombre()}\n"
        f"🆔 *DNI Titular:* {generar_dni()}\n"
        f"📍 *Radicación:* {random.choice(CIUDADES)}\n"
        f"🛡️ *Seguro:* {random.choice(['San Cristóbal', 'La Caja', 'Mapfre', 'Sancor', 'Rivadavia'])}\n\n"
        "⚠️ *Datos simulados - Demostración educativa*",
        parse_mode='Markdown'
    )

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/email <email> - Verificar filtraciones (API real)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/email <email>`", parse_mode='Markdown')
        return
    email = context.args[0]
    await update.message.reply_text(f"📧 Verificando *{email}* en filtraciones...\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')

    breaches = verificar_breach(email)
    if breaches is None:
        await update.message.reply_text("❌ Error al verificar el email. Verifica tu conexión o prueba más tarde.")
        return
    if breaches:
        texto = f"🔴 *{email}* apareció en {len(breaches)} filtraciones:\n\n"
        for b in breaches[:5]:
            texto += f"• {b}\n"
        texto += f"\n💡 Recomendación: Cambia tu contraseña en estas plataformas y activa 2FA."
        await update.message.reply_text(texto, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"✅ *{email}* no se encontró en filtraciones conocidas.\n\n"
            "📊 *Datos de Have I Been Pwned (API real)*",
            parse_mode='Markdown'
        )

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/ip <ip> - Geolocalización (API real)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/ip <dirección_ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')

    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ No se pudo geolocalizar la IP. Verifica que sea una IP válida.")
        return

    await update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"🔌 *ISP:* {datos['isp']}\n"
        f"🏢 *Organización:* {datos['org']}\n\n"
        "📊 *Datos de ip-api.com (API real)*",
        parse_mode='Markdown'
    )

async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/titular <tel> - OSINT teléfono (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/titular <número>`", parse_mode='Markdown')
        return
    telefono = context.args[0]
    await update.message.reply_text(
        f"📱 *Datos del Teléfono {telefono}:*\n\n"
        f"👤 *Titular:* {generar_nombre()}\n"
        f"🆔 *DNI:* {generar_dni()}\n"
        f"📶 *Compañía:* {random.choice(COMPANIAS)}\n"
        f"📱 *Tipo:* Móvil Personal\n"
        f"📍 *Provincia:* {random.choice(PROVINCIAS)}\n"
        f"🌐 *Redes asociadas:*\n"
        f"  • WhatsApp: {'✅ Sí' if random.random() > 0.3 else '❌ No'}\n"
        f"  • Telegram: {'✅ Sí' if random.random() > 0.5 else '❌ No'}\n\n"
        "⚠️ *Datos simulados - Demostración educativa*",
        parse_mode='Markdown'
    )

# --- MÓDULO RED Y SEGURIDAD ---

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/scan <URL/IP> - Escaneo de puertos"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')

    puertos = escanear_puertos(target)
    if not puertos:
        await update.message.reply_text(
            f"🔒 No se encontraron puertos abiertos en *{target}*.\n\n"
            "⚠️ *Algunos servidores bloquean este tipo de escaneos.*",
            parse_mode='Markdown'
        )
        return

    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = SERVICIOS_PUERTOS.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/subdomain <URL> - Descubrir subdominios (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/subdomain <URL>`", parse_mode='Markdown')
        return
    dominio = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop', 'support', 'docs', 'cdn']
    resultado = f"🌐 *Subdominios encontrados para {dominio}:*\n\n"
    for sub in subdominios_comunes:
        resultado += f"🔹 {sub}.{dominio}\n"
    resultado += "\n⚠️ *Datos simulados - Demostración educativa*"
    
    await update.message.reply_text(resultado, parse_mode='Markdown')

# ==================== MANEJADOR DE BOTONES ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔍 *Módulo OSINT - Comandos:*\n\n"
            "/dni <dni> - Consultar DNI\n"
            "/deuda <cuil> - Consultar deudas\n"
            "/dnrpa <patente> - Consultar patente\n"
            "/email <email> - Verificar filtraciones\n"
            "/ip <ip> - Geolocalizar IP\n"
            "/titular <tel> - OSINT teléfono",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad:*\n\n"
            "/scan <URL/IP> - Escaneo de puertos\n"
            "/subdomain <URL> - Descubrir subdominios",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'info_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "ℹ️ *Información del Bot*\n\n"
            "🔹 *Nombre:* Ninjabase Bot\n"
            "🔹 *Versión:* 4.0\n"
            "🔹 *Servidor:* Render\n"
            "🔹 *Estado:* 🟢 Activo\n\n"
            "📊 *APIs integradas:*\n"
            "• ip-api.com (geolocalización)\n"
            "• haveibeenpwned.com (filtraciones)\n\n"
            "🔐 *Datos de DNI, deudas y patentes son simulados.*\n"
            "⚖️ *Bot 100% legal y educativo.*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
            [InlineKeyboardButton("ℹ️ Info del Bot", callback_data='info_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *Ninjabase Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "🔹 *Servidor:* Render\n\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ==================== CONFIGURACIÓN DEL BOT ====================

telegram_app = ApplicationBuilder().token(TOKEN).build()
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
telegram_app.add_handler(CallbackQueryHandler(button_handler))

# ==================== FUNCIÓN PARA INICIAR EL BOT ====================

def run_bot():
    """Inicia el bot de Telegram con polling"""
    print("🤖 Ninjabase Bot v4.0 iniciado en Render")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    telegram_app.run_polling()

# ==================== MAIN ====================

if __name__ == '__main__':
    # Iniciar el bot en un hilo separado
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Iniciar el servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)
