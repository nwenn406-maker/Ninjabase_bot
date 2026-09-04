import os
import logging
import random
import requests
import socket
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

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

# --- DATOS SIMULADOS ---
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
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop', 'support', 'docs', 'cdn']
    encontrados = []
    for sub in subdominios_comunes:
        if random.random() > 0.5:
            encontrados.append(f"{sub}.{dominio}")
    return encontrados[:8]

# --- COMANDOS DEL BOT ---
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint_menu')],
        [InlineKeyboardButton("🔧 Red y Seguridad", callback_data='security_menu')],
    ]
    update.message.reply_text(
        "🕵️ *OSINT Ninja Bot v4.0*\n\n"
        "🔹 *Estado:* 🟢 Activo\n"
        "🔹 *Servidor:* Fly.io\n\n"
        "Selecciona una categoría:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🕵️ *Comandos OSINT Ninja Bot*\n\n"
        "🔍 *OSINT (Información):*\n"
        "/dni <dni> - Consulta RENAPER (simulado)\n"
        "/deuda <cuil> - Consulta deudores (simulado)\n"
        "/editdni <dni> - Editar foto de DNI\n"
        "/editlicencia <dni> - Editar foto de Licencia\n"
        "/familiares <dni> - Buscar familiares\n"
        "/intelx <dominio> - Extraer Databases\n"
        "/dnrpa <patente> - Buscar por patente\n"
        "/email <email> - Verificar filtraciones\n"
        "/renaedits <dni> - Domicilio RENAPER\n"
        "/ip <ip> - Geolocalización (API real)\n"
        "/titular <tel> - OSINT de teléfono\n\n"
        "🔧 *Red y Seguridad:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
        "/start - Menú principal\n"
        "/ping - Estado del bot",
        parse_mode='Markdown'
    )

def ping(update: Update, context: CallbackContext):
    update.message.reply_text("🏓 *Pong!*\n\n✅ El bot está activo y funcionando.", parse_mode='Markdown')

# --- COMANDOS OSINT ---

def dni_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/dni <número>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    update.message.reply_text(
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

def deuda_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/deuda <cuil>`", parse_mode='Markdown')
        return
    cuil = context.args[0]
    update.message.reply_text(
        f"📊 *Reporte Crediticio - CUIL {cuil}:*\n\n"
        f"📈 *Score:* {random.randint(300, 850)}\n"
        f"💸 *Deuda Total:* $ {random.randint(0, 500000):,}\n"
        f"🏦 *Entidades:* {random.choice(['Banco Nación', 'Banco Galicia', 'Banco Santander'])}\n"
        f"📊 *Situación:* {random.choice(['Normal', 'Riesgo bajo', 'Riesgo medio', 'Alto riesgo'])}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

def editdni_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/editdni <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    update.message.reply_text(
        f"🪪 *Edición de DNI - DNI {dni}:*\n\n"
        f"📸 *Foto frontal:* (simulada)\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"⚡ *Estado:* Listo para descarga\n\n"
        "⚠️ *Simulación educativa*",
        parse_mode='Markdown'
    )

def editlicencia_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/editlicencia <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    update.message.reply_text(
        f"🪪 *Edición de Licencia - DNI {dni}:*\n\n"
        f"📸 *Foto Licencia:* (simulada)\n"
        f"👤 *Nombre:* {generar_nombre_completo()}\n"
        f"🚗 *Clase:* {random.choice(['A', 'B', 'C', 'D', 'E'])}\n"
        f"⚡ *Estado:* Listo para descarga\n\n"
        "⚠️ *Simulación educativa*",
        parse_mode='Markdown'
    )

def familiares_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/familiares <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    update.message.reply_text(
        f"👨‍👩‍👧‍👦 *Familiares vinculados a DNI {dni}:*\n\n"
        f"👨 *Padre:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👩 *Madre:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👤 *Cónyuge:* {generar_nombre_completo()} - DNI: {generar_dni()}\n"
        f"👧 *Hijo/a:* {generar_nombre_completo()} - DNI: {generar_dni()}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

def intelx_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/intelx <dominio>`", parse_mode='Markdown')
        return
    dominio = context.args[0]
    update.message.reply_text(
        f"🕵️ *IntelX - Análisis de {dominio}:*\n\n"
        f"📊 *Bases de datos encontradas:* {random.randint(1, 10)}\n"
        f"📧 *Emails expuestos:* {random.randint(5, 50)}\n"
        f"🔑 *Contraseñas filtradas:* {random.choice(['Sí', 'No'])}\n"
        f"📅 *Última filtración:* {random.randint(2018, 2025)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

def dnrpa_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/dnrpa <patente>`", parse_mode='Markdown')
        return
    patente = context.args[0].upper()
    update.message.reply_text(
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

def email_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/email <email>`", parse_mode='Markdown')
        return
    email = context.args[0]
    update.message.reply_text(f"📧 Verificando *{email}* en filtraciones...", parse_mode='Markdown')
    
    try:
        response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', timeout=10)
        if response.status_code == 200:
            breaches = response.json()
            texto = f"🔴 *{email}* apareció en {len(breaches)} filtraciones:\n\n"
            for b in breaches[:10]:
                texto += f"• *{b.get('Name', 'N/A')}* - {b.get('BreachDate', 'N/A')}\n"
            update.message.reply_text(texto, parse_mode='Markdown')
        elif response.status_code == 404:
            update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')
        else:
            update.message.reply_text("❌ Error al consultar.", parse_mode='Markdown')
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}", parse_mode='Markdown')

def renaedits_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/renaedits <dni>`", parse_mode='Markdown')
        return
    dni = context.args[0]
    update.message.reply_text(
        f"📍 *Domicilio RENAPER - DNI {dni}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {dni}\n"
        f"🏠 *Domicilio:* {generar_domicilio()}\n"
        f"🏙️ *Localidad:* {random.choice(CIUDADES)}\n"
        f"🗺️ *Provincia:* {random.choice(PROVINCIAS)}\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

def ip_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/ip <dirección_ip>`", parse_mode='Markdown')
        return
    ip = context.args[0]
    update.message.reply_text(f"📍 Geolocalizando IP *{ip}*...", parse_mode='Markdown')
    
    datos = geolocalizar_ip(ip)
    if not datos:
        update.message.reply_text("❌ No se pudo geolocalizar.", parse_mode='Markdown')
        return
    
    update.message.reply_text(
        f"📍 *Geolocalización IP {ip}:*\n\n"
        f"🌍 *País:* {datos['pais']}\n"
        f"🗺️ *Región:* {datos['region']}\n"
        f"🏙️ *Ciudad:* {datos['ciudad']}\n"
        f"🔌 *ISP:* {datos['isp']}",
        parse_mode='Markdown'
    )

def titular_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/titular <número>`", parse_mode='Markdown')
        return
    telefono = context.args[0]
    update.message.reply_text(
        f"📱 *Datos OSINT - Teléfono {telefono}:*\n\n"
        f"👤 *Titular:* {generar_nombre_completo()}\n"
        f"🆔 *DNI:* {generar_dni()}\n"
        f"📶 *Compañía:* {random.choice(COMPANIAS)}\n"
        f"📍 *Provincia:* {random.choice(PROVINCIAS)}\n"
        f"🌐 *Redes asociadas:*\n"
        f"  • WhatsApp: ✅ Sí\n"
        f"  • Telegram: {random.choice(['✅ Sí', '❌ No'])}\n"
        f"  • Instagram: @usuario\n\n"
        "⚠️ *Datos simulados*",
        parse_mode='Markdown'
    )

# --- COMANDOS RED Y SEGURIDAD ---

def scan_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/scan <URL/IP>`", parse_mode='Markdown')
        return
    target = context.args[0]
    update.message.reply_text(f"🔎 Escaneando puertos en *{target}*...\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    
    puertos = escanear_puertos(target)
    servicios = {21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS', 80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP', 443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S', 1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL', 5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'}
    
    if not puertos:
        update.message.reply_text(f"🔒 No se encontraron puertos abiertos en *{target}*.", parse_mode='Markdown')
        return
    
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        servicio = servicios.get(p, 'Desconocido')
        resultado += f"✅ Puerto *{p}* → {servicio}\n"
    update.message.reply_text(resultado, parse_mode='Markdown')

def subdomain_command(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ *Uso:* `/subdomain <URL>`", parse_mode='Markdown')
        return
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    subdominios = descubrir_subdominios(domain)
    
    resultado = f"🌐 *Subdominios encontrados para {domain}:*\n\n"
    for sub in subdominios:
        resultado += f"🔹 {sub}\n"
    resultado += "\n⚠️ *Datos simulados*"
    update.message.reply_text(resultado, parse_mode='Markdown')

# --- MANEJADOR DE BOTONES ---
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    action = query.data

    if action == 'osint_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        query.edit_message_text(
            "🔍 *Módulo OSINT*\n\n"
            "/dni <dni>\n"
            "/deuda <cuil>\n"
            "/editdni <dni>\n"
            "/editlicencia <dni>\n"
            "/familiares <dni>\n"
            "/intelx <dominio>\n"
            "/dnrpa <patente>\n"
            "/email <email>\n"
            "/renaedits <dni>\n"
            "/ip <ip>\n"
            "/titular <tel>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    elif action == 'security_menu':
        keyboard = [[InlineKeyboardButton("⬅️ Volver", callback_data='start_menu')]]
        query.edit_message_text(
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
        query.edit_message_text(
            "🕵️ *OSINT Ninja Bot v4.0*\n\n"
            "🔹 *Estado:* 🟢 Activo\n"
            "🔹 *Servidor:* Fly.io\n\n"
            "Selecciona una categoría:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# --- CONFIGURACIÓN DEL BOT ---
def setup_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    # Comandos
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("ping", ping))
    dp.add_handler(CommandHandler("dni", dni_command))
    dp.add_handler(CommandHandler("deuda", deuda_command))
    dp.add_handler(CommandHandler("editdni", editdni_command))
    dp.add_handler(CommandHandler("editlicencia", editlicencia_command))
    dp.add_handler(CommandHandler("familiares", familiares_command))
    dp.add_handler(CommandHandler("intelx", intelx_command))
    dp.add_handler(CommandHandler("dnrpa", dnrpa_command))
    dp.add_handler(CommandHandler("email", email_command))
    dp.add_handler(CommandHandler("renaedits", renaedits_command))
    dp.add_handler(CommandHandler("ip", ip_command))
    dp.add_handler(CommandHandler("titular", titular_command))
    dp.add_handler(CommandHandler("scan", scan_command))
    dp.add_handler(CommandHandler("subdomain", subdomain_command))
    
    # Manejador de botones
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    return updater

# --- INICIO ---
if __name__ == '__main__':
    updater = setup_bot()
    updater.start_polling()
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Fly.io")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
