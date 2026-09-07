import os
import logging
import random
import requests
import sqlite3
import socket
import csv
import io
import zipfile
import json
import base64
import time
import hashlib
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== MODO FANTASMA ====================

os.environ['PYTHONHASHSEED'] = '0'
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('sqlite3').setLevel(logging.CRITICAL)

TOKEN_RAW = os.getenv('TELEGRAM_TOKEN')
if not TOKEN_RAW:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")
TOKEN = base64.b64encode(TOKEN_RAW.encode()).decode()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

DB_NAME = "system_cache.db"

def limpiar_logs():
    try:
        if os.path.exists('nohup.out'): os.remove('nohup.out')
        if os.path.exists('logs.txt'): os.remove('logs.txt')
        if os.path.exists('bot.log'): os.remove('bot.log')
    except: pass

limpiar_logs()

# ==================== FLASK SERVER ====================

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({"status": "online", "bot": "Ninja Data Bot", "version": "62.0"})

@flask_app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port)

# ==================== BASE DE DATOS REAL ====================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # RENAPER - 48M registros reales
    c.execute('''CREATE TABLE IF NOT EXISTS renaper (
        dni TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
        domicilio TEXT, localidad TEXT, provincia TEXT, cuil TEXT, telefono TEXT)''')
    
    # DNRPA - 706,464 filas reales
    c.execute('''CREATE TABLE IF NOT EXISTS dnrpa (
        patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, año TEXT,
        titular TEXT, dni_titular TEXT)''')
    
    # BCRA - 32M registros reales
    c.execute('''CREATE TABLE IF NOT EXISTS bcra (
        cuil TEXT PRIMARY KEY, dni TEXT, nombre TEXT, fecha_nac TEXT,
        situacion TEXT, monto_deuda REAL, entidades TEXT, score INTEGER)''')
    
    # Teléfonos - 100M registros reales
    c.execute('''CREATE TABLE IF NOT EXISTS telefonos (
        numero TEXT PRIMARY KEY, titular TEXT, dni_titular TEXT,
        compania TEXT, provincia TEXT)''')
    
    # Emails filtrados
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
        email TEXT PRIMARY KEY, password TEXT, dominio TEXT, fuente TEXT)''')
    
    # Credenciales por URL
    c.execute('''CREATE TABLE IF NOT EXISTS credenciales_url (
        dominio TEXT, usuario TEXT, contraseña TEXT, fuente TEXT)''')
    
    # Índices para búsqueda rápida
    c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_bcra ON bcra(cuil)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_credenciales ON credenciales_url(dominio)')
    
    conn.commit()
    conn.close()
    cargar_datos()
    print("✅ Bases de datos reales inicializadas")

def cargar_datos():
    archivos = {
        'renaper': 'data/renaper.csv',
        'dnrpa': 'data/dnrpa.csv',
        'bcra': 'data/bcra.csv',
        'telefonos': 'data/telefonos.csv',
        'emails': 'data/emails.csv',
        'credenciales_url': 'data/credenciales.csv'
    }
    for tabla, archivo in archivos.items():
        if os.path.exists(archivo):
            importar_csv(archivo, tabla)
            print(f"✅ Cargados datos de {archivo}")

def importar_csv(archivo, tabla):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            try:
                if tabla == 'renaper':
                    c.execute('INSERT OR IGNORE INTO renaper VALUES (?,?,?,?,?,?,?,?,?)', row[:9])
                elif tabla == 'dnrpa':
                    c.execute('INSERT OR IGNORE INTO dnrpa VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'bcra':
                    c.execute('INSERT OR IGNORE INTO bcra VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'telefonos':
                    c.execute('INSERT OR IGNORE INTO telefonos VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'emails':
                    c.execute('INSERT OR IGNORE INTO emails VALUES (?,?,?,?)', row[:4])
                elif tabla == 'credenciales_url':
                    c.execute('INSERT OR IGNORE INTO credenciales_url VALUES (?,?,?,?)', row[:4])
            except: pass
    conn.commit()
    conn.close()

# ==================== FUNCIONES DE CONSULTA REAL ====================

def consultar_renaper(dni):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM renaper WHERE dni = ?', (dni,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7], 'telefono': r[8]}
    return None

def consultar_patente(patente):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente.upper(),))
    r = c.fetchone()
    conn.close()
    if r:
        return {'marca': r[1], 'modelo': r[2], 'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
    return None

def consultar_deuda(cuil):
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        if len(cuil_clean) != 11:
            return None
        
        # Primero buscar en BCRA local
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM bcra WHERE cuil = ?', (cuil_clean,))
        r = c.fetchone()
        conn.close()
        if r:
            return {'dni': r[1], 'nombre': r[2], 'fecha_nac': r[3],
                    'situacion': r[4], 'monto_deuda': r[5], 'entidades': r[6], 'score': r[7]}
        
        # Si no, consultar API BCRA real
        response = requests.get(
            f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}',
            timeout=10,
            headers=HEADERS
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                return data['results']
        return None
    except:
        return None

def consultar_titular(telefono):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM telefonos WHERE numero = ?', (telefono,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'titular': r[1], 'dni_titular': r[2], 'compania': r[3], 'provincia': r[4]}
    return None

def consultar_email(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT password, dominio, fuente FROM emails WHERE email = ?', (email,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'password': r[0], 'dominio': r[1], 'fuente': r[2]}
    return None

def buscar_credenciales_url(dominio):
    credenciales = []
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT usuario, contraseña, fuente FROM credenciales_url WHERE dominio = ?', (dominio,))
    for r in c.fetchall():
        credenciales.append({'usuario': r[0], 'contraseña': r[1], 'fuente': r[2]})
    c.execute('SELECT email, password, fuente FROM emails WHERE dominio = ?', (dominio,))
    for r in c.fetchall():
        credenciales.append({'usuario': r[0], 'contraseña': r[1], 'fuente': r[2]})
    conn.close()
    return credenciales

# ==================== FUNCIONES DE RED ====================

def geolocalizar_ip(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return data
    except: return None

def escanear_puertos(host):
    puertos = [21,22,23,25,53,80,110,135,139,143,443,445,993,995,1723,3306,3389,5432,5900,8080,8443]
    servicios = {21:'FTP',22:'SSH',23:'Telnet',25:'SMTP',53:'DNS',80:'HTTP',110:'POP3',135:'RPC',139:'NetBIOS',143:'IMAP',443:'HTTPS',445:'SMB',993:'IMAPS',995:'POP3S',1723:'PPTP',3306:'MySQL',3389:'RDP',5432:'PostgreSQL',5900:'VNC',8080:'HTTP-Proxy',8443:'HTTPS-Alt'}
    abiertos = []
    try:
        ip = socket.gethostbyname(host)
        for p in puertos:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                if s.connect_ex((ip, p)) == 0: abiertos.append(p)
                s.close()
            except: continue
        return abiertos, servicios
    except: return [], servicios

def descubrir_subdominios(dominio):
    subs = ['www','admin','dev','mail','ftp','api','test','login','app','blog','shop','support','docs','cdn','static','media','video','images','files','backup']
    encontrados = []
    for s in subs:
        try:
            socket.gethostbyname(f"{s}.{dominio}")
            encontrados.append(f"{s}.{dominio}")
        except: continue
    return encontrados

# ==================== SISTEMA DE TOKENS ====================

user_tokens = {}
def get_tokens(user_id):
    return user_tokens.get(str(user_id), 10)

def usar_token(user_id, costo=1):
    if get_tokens(user_id) >= costo:
        user_tokens[str(user_id)] = get_tokens(user_id) - costo
        return True
    return False

# ==================== COMANDOS ====================

async def start(update, context):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🇦🇷 Argentina", callback_data='arg_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security')],
        [InlineKeyboardButton("💰 Tokens", callback_data='tokens')],
    ]
    await update.message.reply_text(
        f"🕵️ *NINJA DATA BOT v62.0 - DATOS REALES*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Comandos:*\n"
        f"/dni <dni> - RENAPER (48M registros)\n"
        f"/deuda <cuil> - BCRA (32M registros)\n"
        f"/dnrpa <patente> - DNRPA (706K registros)\n"
        f"/email <email> - Filtraciones\n"
        f"/ip <ip> - Geolocalización\n"
        f"/titular <tel> - Teléfono (100M registros)\n"
        f"/url <dominio> - Credenciales\n"
        f"/scan <URL/IP> - Puertos\n"
        f"/subdomain <URL> - Subdominios\n"
        f"/saldo - Ver tokens\n\n"
        f"🔐 *Modo Fantasma: ACTIVADO*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ==================== ARGENTINA ====================

async def arg_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇦🇷 *ARGENTINA - DATOS REALES*\n\n"
        f"/dni <dni> - RENAPER (48M)\n"
        f"/deuda <cuil> - BCRA (32M)\n"
        f"/dnrpa <patente> - DNRPA (706K)\n"
        f"/email <email> - Filtraciones\n"
        f"/titular <tel> - Teléfono (100M)\n"
        f"/url <dominio> - Credenciales\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def dni_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /dni <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_renaper(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado en RENAPER.")
        return
    msg = f"📄 *RENAPER - DNI {dni}:*\n\n"
    msg += f"👤 {data['nombre']} {data['apellido']}\n"
    msg += f"🆔 {data['dni']}\n"
    msg += f"🔑 {data['cuil']}\n"
    msg += f"📅 {data['fecha_nac']}\n"
    msg += f"📍 {data['domicilio']}, {data['localidad']}, {data['provincia']}\n"
    msg += f"📱 {data['telefono']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def deuda_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /deuda <cuil>")
        return
    cuil = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_deuda(cuil)
    if not data:
        await update.message.reply_text(f"❌ CUIL {cuil} no encontrado en BCRA.")
        return
    msg = f"📊 *BCRA - CUIL {cuil}:*\n\n"
    if isinstance(data, dict):
        msg += f"👤 {data.get('nombre', 'N/A')}\n"
        msg += f"📈 Situación: {data.get('situacion', 'N/A')}\n"
        msg += f"💸 Deuda: ${data.get('monto_deuda', 0):,}\n"
        msg += f"🏦 Entidades: {data.get('entidades', 'N/A')}\n"
        msg += f"📊 Score: {data.get('score', 'N/A')}\n"
    else:
        msg += f"📊 {json.dumps(data, indent=2, ensure_ascii=False)}"
    msg += f"\n\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def dnrpa_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /dnrpa <patente>")
        return
    patente = context.args[0].upper()
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_patente(patente)
    if not data:
        await update.message.reply_text(f"❌ Patente {patente} no encontrada en DNRPA.")
        return
    msg = f"🚘 *DNRPA - Patente {patente}:*\n\n"
    msg += f"🏭 Marca: {data['marca']}\n"
    msg += f"🚗 Modelo: {data['modelo']}\n"
    msg += f"📅 Año: {data['año']}\n"
    msg += f"👤 Titular: {data['titular']}\n"
    msg += f"🆔 DNI Titular: {data['dni_titular']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def email_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /email <email>")
        return
    email = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_email(email)
    if not data:
        await update.message.reply_text(f"✅ {email} no se encontró en filtraciones.")
        return
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    msg += f"🔑 Contraseña: `{data['password']}`\n"
    msg += f"🌐 Dominio: {data['dominio']}\n"
    msg += f"📌 Fuente: {data['fuente']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def url_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /url <dominio>")
        return
    domain = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    await update.message.reply_text(f"🔍 Buscando credenciales para {domain}...")
    data = buscar_credenciales_url(domain)
    if data:
        msg = f"🔴 *CREDENCIALES ENCONTRADAS* - {domain}\n\n"
        for c in data[:20]:
            msg += f"👤 Usuario: `{c['usuario']}`\n"
            msg += f"🔑 Contraseña: `{c['contraseña']}`\n"
            msg += f"📌 Fuente: {c['fuente']}\n\n"
        msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"✅ No se encontraron credenciales para {domain}.", parse_mode='Markdown')

async def titular_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /titular <tel>")
        return
    phone = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_titular(phone)
    if not data:
        await update.message.reply_text(f"❌ Teléfono {phone} no encontrado.")
        return
    msg = f"📱 *OSINT - Teléfono {phone}:*\n\n"
    msg += f"👤 Titular: {data['titular']}\n"
    msg += f"🆔 DNI: {data['dni_titular']}\n"
    msg += f"📶 Compañía: {data['compania']}\n"
    msg += f"📍 Provincia: {data['provincia']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def ip_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /ip <ip>")
        return
    ip = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = geolocalizar_ip(ip)
    if not data:
        await update.message.reply_text("❌ No se pudo geolocalizar.")
        return
    msg = f"📍 *Geolocalización IP {ip}:*\n\n"
    msg += f"🌍 País: {data.get('country', 'N/A')}\n"
    msg += f"🗺️ Región: {data.get('regionName', 'N/A')}\n"
    msg += f"🏙️ Ciudad: {data.get('city', 'N/A')}\n"
    msg += f"🔌 ISP: {data.get('isp', 'N/A')}\n"
    msg += f"📌 Coordenadas: {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== COMANDOS DE RED ====================

async def scan_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /scan <URL/IP>")
        return
    target = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    await update.message.reply_text(f"🔎 Escaneando {target}...")
    puertos, servicios = escanear_puertos(target)
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en {target}.")
        return
    msg = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        msg += f"✅ Puerto {p} → {servicios.get(p, 'Desconocido')}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def subdomain_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /subdomain <URL>")
        return
    dominio = context.args[0].replace('http://', '').replace('https://', '').split('/')[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    subdominios = descubrir_subdominios(dominio)
    if not subdominios:
        await update.message.reply_text(f"🔍 No se encontraron subdominios para {dominio}.")
        return
    msg = f"🌐 *Subdominios encontrados para {dominio}:*\n\n"
    for s in subdominios:
        msg += f"🔹 {s}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def saldo_command(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"💰 *SALDO DE TOKENS*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"💳 *Costo por consulta:* 1 token\n"
        f"📊 *Consultas disponibles:* {get_tokens(user_id)}",
        parse_mode='Markdown'
    )

# ==================== MANEJADOR DE BOTONES ====================

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'arg_menu':
        await arg_menu(update, context)
    elif query.data == 'security':
        await query.edit_message_text(
            f"🔧 *RED Y SEGURIDAD*\n\n"
            f"/scan <URL/IP> - Puertos\n"
            f"/subdomain <URL> - Subdominios\n\n"
            f"💰 *Tokens:* {get_tokens(user_id)}",
            parse_mode='Markdown'
        )
    elif query.data == 'tokens':
        await query.edit_message_text(
            f"💰 *Tokens: {get_tokens(user_id)}*",
            parse_mode='Markdown'
        )

# ==================== MAIN ====================

def main():
    init_db()
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    app = Application.builder().token(base64.b64decode(TOKEN).decode()).build()
    
    # Argentina
    app.add_handler(CommandHandler("dni", dni_command))
    app.add_handler(CommandHandler("deuda", deuda_command))
    app.add_handler(CommandHandler("dnrpa", dnrpa_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("titular", titular_command))
    app.add_handler(CommandHandler("url", url_command))
    app.add_handler(CommandHandler("ip", ip_command))
    
    # Red
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("subdomain", subdomain_command))
    
    # Generales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saldo", saldo_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 NINJA DATA BOT v62.0 - DATOS REALES")
    print("📊 RENAPER: 48M registros")
    print("📊 DNRPA: 706K registros")
    print("📊 BCRA: 32M registros")
    print("📊 Teléfonos: 100M registros")
    print("🔐 Modo Fantasma: ACTIVADO")
    print("🌐 Flask server: puerto 8080")
    app.run_polling()

if __name__ == '__main__':
    main()
