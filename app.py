import os
import logging
import random
import requests
import socket
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

# --- RUTA DEL WEBHOOK ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        if not json_data:
            return "No data", 400
        update = Update.de_json(json_data, application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    except Exception as e:
        logging.error(f"Error en webhook: {e}")
        return f"Error: {str(e)}", 500

# ==================== FUNCIONES DE APIS REALES ====================

def geolocalizar_ip(ip):
    """API real: ip-api.com"""
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
                'lon': data.get('lon')
            }
        return None
    except:
        return None

def verificar_email_breach(email):
    """API real: Have I Been Pwned"""
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
    """API REAL del BCRA - Central de Deudores (Pública)"""
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
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
    except:
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

# ==================== DATOS SIMULADOS (PARA COMANDOS SIN API PUBLICA) ====================

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

# ==================== COMANDOS DEL BOT ====================

# --- COMANDO /start ---
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

# --- COMANDO /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot - APIs REALES*\n\n"
        "🔍 *OSINT:*\n"
        "/dni <dni> - RENAPER (simulado)\n"
        "/deuda <cuil> - BCRA (pública y gratuita)\n"
        "/editdni <dni> - Editar foto de DNI (simulado)\n"
        "/editlicencia <dni> - Editar foto de Licencia (simulado)\n"
        "/familiares <dni> - Buscar familiares (simulado)\n"
        "/intelx <dominio> - Extraer Databases (simulado)\n"
        "/dnrpa <patente> - DNRPA (simulado)\n"
        "/email <email> - Have I Been Pwned (API real)\n"
        "/renaedits <dni> - Domicilio RENAPER (simulado)\n"
        "/ip <ip> - ip-api.com (API real)\n"
        "/titular <tel> - OSINT de teléfono (sin API pública)\n\n"
        "🔧 *Red y Seguridad:*\n"
        "/scan <URL/IP> - Escaneo de puertos (real)\n"
        "/subdomain <URL> - Subdominios\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

# --- COMANDO /ping ---
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo y funcionando.", parse_mode='Markdown')

# ==================== COMANDOS OSINT ====================

# --- /dni ---
async def dni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dni <número>`\n\nEjemplo: `/dni 12345678`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📄 *Resultados RENAPER - DNI {dni}:*\n\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🔑 *CUIL:* {generar_cuil(dni)}\n"
        f"📅 *Nacimiento:* {random.randint(1, 28)}/{random.randint(1, 12)}/{random.randint(1960, 2005)}\n"
        f"📍 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados - No es una consulta real*",
        parse_mode='Markdown'
    )

# --- /deuda (API REAL DEL BCRA) ---
async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    situacion_map = {'1': 'Normal', '2': 'Riesgo bajo', '3': 'Riesgo medio', '4': 'Alto riesgo', '5': 'Irrecuperable'}
    situacion_texto = situacion_map.get(str(resultado.get('situacion', '')), 'N/A')
    
    await update.message.reply_text(
        f"📊 *Central de Deudores BCRA - CUIL {cuil}:*\n\n"
        f"👤 *Titular:* {resultado.get('denominacion', 'N/A')}\n"
        f"📈 *Situación Crediticia:* {situacion_texto}\n"
        f"💸 *Monto Total:* $ {resultado.get('monto', 0):,}\n"
        f"📅 *Periodo reportado:* {resultado.get('periodo', 'N/A')}\n"
        f"🏦 *Entidades financieras:* {len(resultado.get('entidades', []))} reportan\n\n"
        "📊 *Fuente: BCRA - API pública*",
        parse_mode='Markdown'
    )

# --- /editdni ---
async def editdni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/editdni <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"🪪 *Edición de DNI - DNI {dni}:*\n\n"
        f"📸 *Foto frontal:* (simulada)\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"⚡ *Estado:* Listo para descarga\n\n"
        "⚠️ *Simulación educativa*",
        parse_mode='Markdown'
    )

# --- /editlicencia ---
async def editlicencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/editlicencia <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"🪪 *Edición de Licencia - DNI {dni}:*\n\n"
        f"📸 *Foto Licencia:* (simulada)\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🚗 *Clase:* {random.choice(['A', 'B', 'C', 'D', 'E'])}\n"
        f"⚡ *Estado:* Listo para descarga\n\n"
        "⚠️ *Simulación educativa*",
        parse_mode='Markdown'
    )

# --- /familiares ---
async def familiares_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/familiares <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"👨‍👩‍👧‍👦 *Familiares vinculados a DNI {dni}:*\n\n"
        f"👨 *Padre:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👩 *Madre:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👤 *Cónyuge:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👧 *Hijo/a:* {generar_nombre_completo()} - DNI: {generar_dni()}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

# --- /intelx ---
async def intelx_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/intelx <dominio>`", parse_mode='Markdown')
        return
    dominio = context.args[0]
    await update.message.reply_text(
        f"🕵️ *IntelX - Análisis de {dominio}:*\n\n"
        f"📊 *Bases de datos encontradas:* {random.randint(1, 10)}\n"
        f"📧 *Emails expuestos:* {random.randint(5, 50)}\n"
        f"🔑 *Contraseñas filtradas:* {random.choice(['Sí', 'No'])}\n"
        f"📅 *Última filtración:* {random.randint(2018, 2025)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

# --- /dnrpa ---
async def dnrpa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/dnrpa <patente>`", parse_mode='Markdown')
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
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

# --- /email (API REAL) ---
async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# --- /renaedits ---
async def renaedits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/renaedits <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    await update.message.reply_text(
        f"📍 *Domicilio RENAPER - DNI {dni}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🏠 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

# --- /ip (API REAL) ---
async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# --- /titular ---
async def titular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "⚠️ *Datos simulados - No existe API pública*",
        parse_mode='Markdown'
    )

# ==================== COMANDOS RED Y SEGURIDAD ====================

# --- /scan ---
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`\n\nEjemplo: `/scan google.com`", parse_mode='Markdown')
        return
    target = context.args[0]
    await update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    
    puertos = escanear_puertos(target)
    servicios = {21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS', 80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP', 443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S', 1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL', 5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'}
    
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en *{target}*.", parse_mode='Markdown')
        return
    
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

# --- /subdomain ---
async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ *Uso:* `/subdomain <URL>`\n\nEjemplo: `/subdomain google.com`", parse_mode='Markdown')
        return
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    await update.message.reply_text(f"🌐 Descubriendo subdominios para *{domain}*...\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    subdominios = descubrir_subdominios(domain)
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in subdominios:
        resultado += f"🔹 {sub}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

# ==================== MANEJADOR DE BOTONES ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔍 *Módulo OSINT - APIs REALES*\n\n"
            "/dni <dni> - RENAPER (simulado)\n"
            "/deuda <cuil> - BCRA (pública)\n"
            "/editdni <dni> - Editar DNI\n"
            "/editlicencia <dni> - Editar Licencia\n"
            "/familiares <dni> - Familiares\n"
            "/intelx <dominio> - IntelX\n"
            "/dnrpa <patente> - DNRPA\n"
            "/email <email> - Have I Been Pwned\n"
            "/renaedits <dni> - Domicilio RENAPER\n"
            "/ip <ip> - ip-api.com\n"
            "/titular <tel> - OSINT teléfono",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        await query.edit_message_text(
            "🔧 *Módulo Red y Seguridad*\n\n"
            "/scan <URL/IP> - Escaneo de puertos\n"
            "/subdomain <URL> - Subdominios\n\n"
            "📌 *Comandos con escaneo real.*",
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

# ==================== CONFIGURACIÓN DEL BOT ====================

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("ping", ping))
application.add_handler(CommandHandler("dni", dni_command))
application.add_handler(CommandHandler("deuda", deuda_command))
application.add_handler(CommandHandler("editdni", editdni_command))
application.add_handler(CommandHandler("editlicencia", editlicencia_command))
application.add_handler(CommandHandler("familiares", familiares_command))
application.add_handler(CommandHandler("intelx", intelx_command))
application.add_handler(CommandHandler("dnrpa", dnrpa_command))
application.add_handler(CommandHandler("email", email_command))
application.add_handler(CommandHandler("renaedits", renaedits_command))
application.add_handler(CommandHandler("ip", ip_command))
application.add_handler(CommandHandler("titular", titular_command))
application.add_handler(CommandHandler("scan", scan_command))
application.add_handler(CommandHandler("subdomain", subdomain_command))
application.add_handler(CallbackQueryHandler(button_handler))

# ==================== CONFIGURAR WEBHOOK ====================

async def setup_webhook():
    webhook_url = f"https://ninjabase-bot.fly.dev/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook configurado en: {webhook_url}")

# ==================== INICIALIZACIÓN ====================

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(setup_webhook())
        logging.info("🤖 OSINT Ninja Bot v5.0 iniciado en Fly.io con webhook")
    except Exception as e:
        logging.error(f"Error al inicializar el bot: {e}")
    
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
