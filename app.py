import os
import logging
import random
import requests
import socket
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import threading

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

# --- FUNCIONES DE APIs REALES ---

def geolocalizar_ip(ip):
    """API real: ip-api.com - Geolocalización de IP"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'pais': data.get('country', 'N/A'),
                'region': data.get('regionName', 'N/A'),
                'ciudad': data.get('city', 'N/A'),
                'isp': data.get('isp', 'N/A'),
                'lat': data.get('lat', 'N/A'),
                'lon': data.get('lon', 'N/A')
            }
        return None
    except:
        return None

def verificar_email_breach(email):
    """API real: Have I Been Pwned - Verifica filtraciones de correo"""
    try:
        response = requests.get(
            f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
            timeout=10
        )
        if response.status_code == 200:
            return [b.get('Name') for b in response.json()]
        elif response.status_code == 404:
            return []
        return None
    except:
        return None

def consultar_deuda_bcra(cuil):
    """API REAL del BCRA - Central de Deudores (Pública y gratuita)"""
    try:
        # Limpiar CUIL (solo números)
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        if len(cuil_clean) != 11:
            return None
        
        # Endpoint de deudas actuales
        response = requests.get(
            f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}',
            timeout=15
        )
        
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
    except Exception as e:
        logging.error(f"Error en BCRA: {e}")
        return None

def escanear_puertos(host):
    """Escaneo real de puertos con socket"""
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
    except:
        return []

def descubrir_subdominios(dominio):
    """Descubrimiento de subdominios (simulación)"""
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop', 'support', 'docs', 'cdn']
    encontrados = []
    for sub in subdominios_comunes:
        if random.random() > 0.5:
            encontrados.append(f"{sub}.{dominio}")
    return encontrados[:8]

# --- DATOS SIMULADOS PARA COMANDOS SIN API PÚBLICA ---
NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía', 'Diego', 'Valentina']
APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez']
CIUDADES = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán']
PROVINCIAS = ['Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza', 'Tucumán']
COMPANIAS = ['Movistar', 'Claro', 'Personal', 'Tuenti']

def generar_dni(): return f"{random.randint(10000000, 99999999)}"
def generar_cuil(dni=None):
    if not dni: dni = generar_dni()
    return f"20-{dni}-{random.randint(0, 9)}"
def generar_nombre_completo(): return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
def generar_domicilio(): return f"{random.choice(['Av.', 'Calle'])} {random.choice(['Corrientes', 'Santa Fe', 'San Martín', '9 de Julio'])} {random.randint(100, 5000)}"

# --- COMANDOS DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v5.0 - APIs REALES*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Fly.io\n"
        "🔹 *APIs integradas:*\n"
        "  • BCRA Central de Deudores (pública)\n"
        "  • Have I Been Pwned\n"
        "  • ip-api.com\n"
        "  • Escaneo de puertos\n\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot - APIs REALES*\n\n"
        "🔍 *OSINT:*\n"
        "/dni <dni> - RENAPER (simulado)\n"
        "/deuda <cuil> - BCRA (pública y gratuita)\n"
        "/dnrpa <patente> - DNRPA (simulado)\n"
        "/email <email> - Have I Been Pwned\n"
        "/ip <ip> - ip-api.com\n"
        "/titular <tel> - OSINT de teléfono (simulado)\n\n"
        "🔧 *Red y Seguridad:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo y funcionando con APIs reales.", parse_mode='Markdown')

# --- COMANDO: /deuda (API REAL DEL BCRA) ---

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta la Central de Deudores del BCRA - API REAL Y PÚBLICA"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/deuda <cuil>`\n\nEjemplo: `/deuda 20123456789`", parse_mode='Markdown')
        return
    
    cuil = context.args[0]
    await update.message.reply_text(f"💰 Consultando BCRA para CUIL *{cuil}*...\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    resultado = consultar_deuda_bcra(cuil)
    
    if not resultado:
        await update.message.reply_text(
            "❌ No se pudo obtener información del BCRA.\n\n"
            "Posibles causas:\n"
            "• CUIL inválido (debe tener 11 dígitos)\n"
            "• La persona no tiene deudas reportadas\n"
            "• Error en el servicio del BCRA",
            parse_mode='Markdown'
        )
        return
    
    situacion_map = {
        '1': 'Normal',
        '2': 'Riesgo bajo',
        '3': 'Riesgo medio',
        '4': 'Alto riesgo',
        '5': 'Irrecuperable',
        '6': 'Irrecuperable por disposición técnica'
    }
    
    situacion_texto = situacion_map.get(str(resultado.get('situacion', '')), 'N/A')
    monto = resultado.get('monto', 0)
    
    await update.message.reply_text(
        f"📊 *Central de Deudores BCRA - CUIL {cuil}:*\n\n"
        f"👤 *Titular:* {resultado.get('denominacion', 'N/A')}\n"
        f"📈 *Situación Crediticia:* {situacion_texto}\n"
        f"💸 *Monto Total:* $ {monto:,}\n"
        f"📅 *Periodo reportado:* {resultado.get('periodo', 'N/A')}\n"
        f"🏦 *Entidades financieras:* {len(resultado.get('entidades', []))} reportan\n\n"
        "📊 *Fuente: BCRA - API pública*",
        parse_mode='Markdown'
    )

# --- COMANDO: /dni (SIMULADO - RENAPER) ---

async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta RENAPER (simulado - requiere credenciales comerciales para ser real)"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`\n\nEjemplo: `/dni 12345678`", parse_mode='Markdown')
        return
    
    dni = context.args[0]
    nombre = generar_nombre_completo()
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* {nombre}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* {generar_cuil(dni)}\n"
        f"📅 *Nacimiento:* {random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(1960, 2005)}\n"
        f"📍 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*\n"
        "📌 *Para datos reales: necesitas credenciales comerciales de RENAPER*",
        parse_mode='Markdown'
    )

# --- COMANDO: /dnrpa (SIMULADO) ---

async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta DNRPA (simulado - requiere API Key comercial para ser real)"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dnrpa <patente>`\n\nEjemplo: `/dnrpa AB123CD`", parse_mode='Markdown')
        return
    
    patente = context.args[0].upper()
    await update.message.reply_text(
        f"🚘 *Datos DNRPA - Patente {patente}:*\n\n"
        f"🏭 *Marca:* {random.choice(['Toyota', 'Volkswagen', 'Ford', 'Chevrolet'])}\n"
        f"🚗 *Modelo:* {random.choice(['Corolla', 'Golf', 'Focus', 'Cruze'])}\n"
        f"📅 *Año:* {random.randint(2000, 2025)}\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI Titular:* {generar_dni()}\n"
        f"📍 *Radicación:* {random.choice(CIUDADES)}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*\n"
        "📌 *Para datos reales: necesitas API Key de Patente.ar*",
        parse_mode='Markdown'
    )

# --- COMANDO: /email (API REAL) ---

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica filtraciones de email con Have I Been Pwned - API REAL"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/email <email>`\n\nEjemplo: `/email correo@ejemplo.com`", parse_mode='Markdown')
        return
    
    email = context.args[0]
    await update.message.reply_text(f"📧 Verificando *{email}* en filtraciones...\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    breaches = verificar_email_breach(email)
    
    if breaches is None:
        await update.message.reply_text("❌ Error al verificar el email. Intenta más tarde.", parse_mode='Markdown')
        return
    
    if breaches:
        texto = f"🔴 *{email}* apareció en {len(breaches)} filtraciones:\n\n"
        for b in breaches[:10]:
            texto += f"• {b}\n"
        texto += "\n💡 *Recomendación:* Cambia tu contraseña en estas plataformas."
        await update.message.reply_text(texto, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"✅ *{email}* no se encontró en filtraciones conocidas.\n\n"
            "📊 *Fuente: Have I Been Pwned (API real)*",
            parse_mode='Markdown'
        )

# --- COMANDO: /ip (API REAL) ---

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Geolocalización de IP con ip-api.com - API REAL"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/ip <dirección_ip>`\n\nEjemplo: `/ip 8.8.8.8`", parse_mode='Markdown')
        return
    
    ip = context.args[0]
    await update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')
    
    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ No se pudo geolocalizar la IP. Verifica que sea una IP válida.", parse_mode='Markdown')
        return
    
    await update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"📌 *Coordenadas:* {datos['lat']}, {datos['lon']}\n"
        f"🔌 *ISP:* {datos['isp']}\n\n"
        "📊 *Fuente: ip-api.com (API real)*",
        parse_mode='Markdown'
    )

# --- COMANDO: /scan (REAL) ---

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Escaneo de puertos con socket - REAL"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`\n\nEjemplo: `/scan google.com`", parse_mode='Markdown')
        return
    
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    
    puertos = escanear_puertos(target)
    servicios = {
        21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS',
        80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP',
        443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S',
        1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL',
        5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'
    }
    
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en *{target}*.", parse_mode='Markdown')
        return
    
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- COMANDO: /subdomain (SIMULADO) ---

async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Descubrimiento de subdominios (simulado)"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/subdomain <URL>`\n\nEjemplo: `/subdomain google.com`", parse_mode='Markdown')
        return
    
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    await update.message.reply_text(f"🌐 Descubriendo subdominios para *{domain}*...\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    subdominios = descubrir_subdominios(domain)
    
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in subdominios:
        resultado += f"🔹 {sub}\n"
    resultado += "\n⚠️ *Datos simulados*"
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- COMANDO: /titular (SIMULADO - SIN API PÚBLICA) ---

async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Consulta OSINT de teléfono (sin API pública)"""
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/titular <número>`\n\nEjemplo: `/titular 1123456789`", parse_mode='Markdown')
        return
    
    telefono = context.args[0]
    await update.message.reply_text(
        f"📱 *Datos OSINT - Teléfono {telefono}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {generar_dni()}\n"
        f"📶 *Compañía:* {random.choice(COMPANIAS)}\n"
        f"📍 *Provincia:* {random.choice(PROVINCIAS)}\n"
        f"🌐 *Redes asociadas:*\n"
        f"  • WhatsApp: ✅ Sí\n"
        f"  • Telegram: {random.choice(['✅ Sí', '❌ No'])}\n"
        f"  • Instagram: @usuario\n\n"
        "⚠️ *Datos simulados*\n"
        "📌 *No existe API pública para titulares de teléfono en Argentina*",
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
            "/dni <dni> - RENAPER (simulado)\n"
            "/deuda <cuil> - BCRA (pública y gratuita)\n"
            "/dnrpa <patente> - DNRPA (simulado)\n"
            "/email <email> - Have I Been Pwned (API real)\n"
            "/ip <ip> - ip-api.com (API real)\n"
            "/titular <tel> - OSINT de teléfono (simulado)\n\n"
            "📌 *Comandos con API real:* /deuda, /email, /ip, /scan",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad*\n\n"
            "/scan <URL/IP> - Escaneo de puertos (real)\n"
            "/subdomain <URL> - Subdominios (simulado)\n\n"
            "📌 *Comando con escaneo real:* /scan",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'start_menu':
        keyboard = [
            [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
            [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
        ]
        await query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v5.0 - APIs REALES*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "🔹 *Servidor:* Fly.io\n"
            "🔹 *APIs integradas:*\n"
            "  • BCRA Central de Deudores (pública)\n"
            "  • Have I Been Pwned\n"
            "  • ip-api.com\n"
            "  • Escaneo de puertos\n\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---

telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("ping", ping))
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
