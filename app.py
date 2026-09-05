import os
import logging
import json
import random
import requests
import socket
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# --- CONFIGURACIÓN ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"bot": "OSINT Ninja Bot", "status": "online", "version": "6.0"})

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return "No data", 400
        update = Update.de_json(data, application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logging.error(f"Error en webhook: {e}")
        return "Error", 500

# ==================== APIs REALES ====================

def consultar_deuda_bcra(cuil):
    """API REAL - BCRA Central de Deudores (pública y gratuita)"""
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
                return {
                    'denominacion': r.get('denominacion', 'N/A'),
                    'situacion': r.get('situacion', 'N/A'),
                    'monto': r.get('monto', 0),
                    'periodo': r.get('periodo', 'N/A')
                }
        return None
    except:
        return None

def geolocalizar_ip(ip):
    """API REAL - ip-api.com (pública y gratuita)"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {
                'pais': data.get('country'),
                'region': data.get('regionName'),
                'ciudad': data.get('city'),
                'isp': data.get('isp'),
                'lat': data.get('lat'),
                'lon': data.get('lon'),
                'timezone': data.get('timezone'),
                'zip': data.get('zip')
            }
        return None
    except:
        return None

def verificar_email_breach(email):
    """API REAL - Have I Been Pwned"""
    try:
        headers = {'user-agent': 'OSINTNinjaBot/1.0'}
        hibp_key = os.getenv('HIBP_API_KEY')
        if hibp_key:
            headers['hibp-api-key'] = hibp_key
        response = requests.get(
            f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return [b.get('Name') for b in response.json()]
        elif response.status_code == 404:
            return []
        return None
    except:
        return None

def consultar_patente(patente):
    """API REAL - Patente.ar (requiere API Key comercial)"""
    try:
        api_key = os.getenv('PATENTE_API_KEY')
        if not api_key:
            return None
        response = requests.post(
            'https://api.patente.ar/v1/consultas',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={'patentes': [patente]},
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def escanear_puertos(host):
    """Escaneo real de puertos con socket - MÁS DETALLADO"""
    puertos = [
        21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443,
        161, 389, 636, 873, 1080, 1433, 1521, 2049, 2375, 2376, 3000, 5000, 6379, 9200, 11211, 27017
    ]
    servicios = {
        21: 'FTP - File Transfer Protocol',
        22: 'SSH - Secure Shell',
        23: 'Telnet - Remote Login',
        25: 'SMTP - Email',
        53: 'DNS - Domain Name System',
        80: 'HTTP - Web Server',
        110: 'POP3 - Email',
        135: 'RPC - Remote Procedure Call',
        139: 'NetBIOS - File Sharing',
        143: 'IMAP - Email',
        443: 'HTTPS - Secure Web Server',
        445: 'SMB - File Sharing',
        993: 'IMAPS - Secure Email',
        995: 'POP3S - Secure Email',
        1723: 'PPTP - VPN',
        3306: 'MySQL - Database',
        3389: 'RDP - Remote Desktop',
        5432: 'PostgreSQL - Database',
        5900: 'VNC - Remote Desktop',
        8080: 'HTTP-Proxy - Web Proxy',
        8443: 'HTTPS-Alt - Secure Web Server',
        161: 'SNMP - Network Management',
        389: 'LDAP - Directory Service',
        636: 'LDAPS - Secure Directory',
        873: 'RSYNC - File Sync',
        1080: 'SOCKS - Proxy',
        1433: 'MSSQL - Database',
        1521: 'Oracle - Database',
        2049: 'NFS - File Sharing',
        2375: 'Docker - Container API',
        2376: 'Docker - Secure Container',
        3000: 'Grafana - Monitoring',
        5000: 'Flask - Web Framework',
        6379: 'Redis - Cache',
        9200: 'Elasticsearch - Search',
        11211: 'Memcached - Cache',
        27017: 'MongoDB - Database'
    }
    
    abiertos = []
    try:
        ip = socket.gethostbyname(host)
        for p in puertos:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                if sock.connect_ex((ip, p)) == 0:
                    abiertos.append(p)
                sock.close()
            except:
                continue
        return abiertos, servicios
    except:
        return [], servicios

# ==================== DATOS SIMULADOS ====================
NOMBRES = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía']
APELLIDOS = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez']
CIUDADES = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán']

def generar_nombre(): return f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
def generar_domicilio(): return f"{random.choice(['Av.','Calle'])} {random.choice(['Corrientes','Santa Fe','San Martín','9 de Julio'])} {random.randint(100, 5000)}"
def generar_dni(): return f"{random.randint(10000000, 99999999)}"

# ==================== COMANDOS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security_menu')],
    ]
    await update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v6.0 - APIs REALES*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Fly.io\n\n"
        "📊 *APIs REALES integradas:*\n"
        "✅ BCRA Central de Deudores (pública y gratuita)\n"
        "✅ ip-api.com (geolocalización)\n"
        "✅ Have I Been Pwned (filtraciones)\n"
        "✅ Escaneo de puertos (35+ puertos)\n\n"
        "⚠️ *RENAPER y DNRPA requieren credenciales comerciales*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot v6.0*\n\n"
        "🔍 *OSINT (APIS REALES):*\n"
        "/deuda <cuil> - BCRA Central de Deudores (pública y gratuita)\n"
        "/ip <ip> - ip-api.com (pública y gratuita)\n"
        "/email <email> - Have I Been Pwned (API key gratuita)\n"
        "/scan <URL/IP> - Escaneo de 35+ puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
        "⚠️ *Requieren credenciales comerciales:*\n"
        "/dni <dni> - RENAPER\n"
        "/dnrpa <patente> - Patente.ar\n"
        "/titular <tel> - No existe API pública\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

# --- COMANDO /deuda (BCRA - API REAL) ---
async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/deuda <cuil>`\n\nEjemplo: `/deuda 20123456789`", parse_mode='Markdown')
        return
    
    cuil = parts[1]
    await update.message.reply_text(f"💰 *Consultando BCRA para CUIL {cuil}...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    resultado = consultar_deuda_bcra(cuil)
    if not resultado:
        await update.message.reply_text(
            "❌ *No se encontraron deudas para ese CUIL.*\n\n"
            "Posibles causas:\n"
            "• CUIL inválido (debe tener 11 dígitos)\n"
            "• Sin deudas reportadas en el BCRA",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        f"📊 *Central de Deudores BCRA - CUIL {cuil}:*\n\n"
        f"👤 *Titular:* {resultado['denominacion']}\n"
        f"📈 *Situación:* {resultado['situacion']}\n"
        f"💸 *Monto:* $ {resultado['monto']:,}\n"
        f"📅 *Periodo:* {resultado['periodo']}\n\n"
        "📊 *Fuente: BCRA - API pública*\n"
        "🔗 https://www.bcra.gob.ar/",
        parse_mode='Markdown'
    )

# --- COMANDO /ip (ip-api.com - API REAL) ---
async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/ip <dirección>`\n\nEjemplo: `/ip 8.8.8.8`", parse_mode='Markdown')
        return
    
    ip = parts[1]
    await update.message.reply_text(f"📍 *Geolocalizando IP {ip}...*", parse_mode='Markdown')
    
    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ *No se pudo geolocalizar.*\nVerifica que la IP sea válida.", parse_mode='Markdown')
        return
    
    await update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"📌 *Coordenadas:* {datos['lat']}, {datos['lon']}\n"
        f"🔌 *ISP:* {datos['isp']}\n"
        f"🕐 *Zona Horaria:* {datos.get('timezone', 'N/A')}\n"
        f"📮 *Código Postal:* {datos.get('zip', 'N/A')}\n\n"
        "📊 *Fuente: ip-api.com (API real)*\n"
        "🔗 https://ip-api.com/",
        parse_mode='Markdown'
    )

# --- COMANDO /email (HIBP - API REAL) ---
async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/email <email>`\n\nEjemplo: `/email correo@ejemplo.com`", parse_mode='Markdown')
        return
    
    email = parts[1]
    await update.message.reply_text(f"📧 *Verificando {email} en filtraciones...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    breaches = verificar_email_breach(email)
    if breaches is None:
        await update.message.reply_text("❌ *Error al verificar el email.*\nIntenta más tarde.", parse_mode='Markdown')
        return
    
    if breaches:
        texto = f"🔴 *{email} apareció en {len(breaches)} filtraciones:*\n\n"
        for b in breaches[:10]:
            texto += f"• {b}\n"
        texto += "\n💡 *Recomendación:* Cambia tu contraseña en estas plataformas y activa 2FA."
        await update.message.reply_text(texto, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"✅ *{email} no se encontró en filtraciones conocidas.*\n\n"
            "📊 *Fuente: Have I Been Pwned (API real)*\n"
            "🔗 https://haveibeenpwned.com/",
            parse_mode='Markdown'
        )

# --- COMANDO /scan (Escaneo real de puertos - DETALLADO) ---
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`\n\nEjemplo: `/scan google.com`", parse_mode='Markdown')
        return
    
    target = parts[1]
    await update.message.reply_text(f"🔎 *Escaneando puertos en {target}...*\n⏳ Esto puede tomar hasta 60 segundos.\n📊 *Analizando más de 35 puertos comunes.*", parse_mode='Markdown')
    
    puertos_abiertos, servicios = escanear_puertos(target)
    
    if not puertos_abiertos:
        await update.message.reply_text(
            f"🔒 *No se encontraron puertos abiertos en {target}.*\n\n"
            "Posibles causas:\n"
            "• El servidor no está respondiendo\n"
            "• Firewall bloqueando conexiones\n"
            "• El host no existe",
            parse_mode='Markdown'
        )
        return
    
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos_abiertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ *Puerto {p}* → {servicio}\n"
    
    resultado += f"\n📊 *Total de puertos abiertos: {len(puertos_abiertos)}*\n"
    resultado += "🔗 *Recomendación:* Cierra los puertos innecesarios."
    
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- COMANDO /subdomain ---
async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/subdomain <URL>`\n\nEjemplo: `/subdomain google.com`", parse_mode='Markdown')
        return
    
    domain = parts[1].replace('http://', '').replace('https://', '').split('/')[0]
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop', 'support', 'docs', 'cdn', 'static', 'media', 'video', 'images', 'files', 'backup']
    
    encontrados = []
    for sub in subdominios_comunes:
        if random.random() > 0.5:
            encontrados.append(f"{sub}.{domain}")
    
    if not encontrados:
        await update.message.reply_text(f"🔍 *No se encontraron subdominios para {domain}.*", parse_mode='Markdown')
        return
    
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in encontrados[:10]:
        resultado += f"🔹 {sub}\n"
    
    resultado += "\n⚠️ *Datos simulados para demostración.*\n"
    resultado += "📌 *Para resultados reales, usa SecurityTrails API.*"
    
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- COMANDO /dni (requiere credenciales) ---
async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`\n\nEjemplo: `/dni 12345678`", parse_mode='Markdown')
        return
    
    dni = parts[1]
    await update.message.reply_text(
        "⚠️ *RENAPER requiere credenciales comerciales.*\n\n"
        "Para consultar RENAPER necesitás contrato con el organismo.\n\n"
        "📌 *Alternativas disponibles (APIs reales):*\n"
        "• /deuda - BCRA (pública y gratuita)\n"
        "• /ip - Geolocalización\n"
        "• /email - Have I Been Pwned\n"
        "• /scan - Escaneo de puertos",
        parse_mode='Markdown'
    )

# --- COMANDO /dnrpa (requiere credenciales) ---
async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/dnrpa <patente>`\n\nEjemplo: `/dnrpa AB123CD`", parse_mode='Markdown')
        return
    
    patente = parts[1].upper()
    await update.message.reply_text(
        "⚠️ *DNRPA requiere API Key comercial.*\n\n"
        "Para consultar Patente.ar necesitás credenciales comerciales .\n\n"
        "📌 *Alternativas disponibles (APIs reales):*\n"
        "• /deuda - BCRA (pública y gratuita)\n"
        "• /ip - Geolocalización\n"
        "• /scan - Escaneo de puertos",
        parse_mode='Markdown'
    )

# --- COMANDO /titular ---
async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* `/titular <número>`\n\nEjemplo: `/titular 1123456789`", parse_mode='Markdown')
        return
    
    await update.message.reply_text(
        "📱 *OSINT Teléfono*\n\n"
        "⚠️ *No existe una API pública para consultar titulares de líneas telefónicas.*\n\n"
        "Esta información es privada de las compañías telefónicas.\n\n"
        "📌 *Alternativas disponibles (APIs reales):*\n"
        "• /deuda - BCRA (pública y gratuita)\n"
        "• /ip - Geolocalización\n"
        "• /email - Have I Been Pwned\n"
        "• /scan - Escaneo de puertos",
        parse_mode='Markdown'
    )

# --- MANEJADOR DE BOTONES ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        await query.edit_message_text(
            "🔍 *Módulo OSINT - APIs REALES*\n\n"
            "✅ *Funcionan sin credenciales:*\n"
            "/deuda <cuil> - BCRA (pública y gratuita)\n"
            "/ip <ip> - ip-api.com (pública y gratuita)\n"
            "/email <email> - Have I Been Pwned\n\n"
            "⚠️ *Requieren credenciales comerciales:*\n"
            "/dni <dni> - RENAPER\n"
            "/dnrpa <patente> - Patente.ar\n"
            "/titular <tel> - Sin API pública",
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        await query.edit_message_text(
            "🔧 *Módulo Red*\n\n"
            "✅ *Funcionan sin credenciales:*\n"
            "/scan <URL/IP> - Escaneo de 35+ puertos\n"
            "/subdomain <URL> - Subdominios\n\n"
            "📊 *Cada escaneo analiza puertos comunes y muestra servicios detectados.*",
            parse_mode='Markdown'
        )

# ==================== CONFIGURACIÓN ====================

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ping", ping))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("dni", dni_command))
application.add_handler(CommandHandler("deuda", deuda_command))
application.add_handler(CommandHandler("ip", ip_command))
application.add_handler(CommandHandler("email", email_command))
application.add_handler(CommandHandler("scan", scan_command))
application.add_handler(CommandHandler("subdomain", subdomain_command))
application.add_handler(CommandHandler("dnrpa", dnrpa_command))
application.add_handler(CommandHandler("titular", titular_command))
application.add_handler(CallbackQueryHandler(button_handler))

async def setup_webhook():
    await application.initialize()
    webhook_url = f"https://ninjabase-bot.fly.dev/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook configurado en: {webhook_url}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(setup_webhook())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
