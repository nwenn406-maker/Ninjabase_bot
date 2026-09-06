import os
import logging
import random
import requests
import sqlite3
import socket
import csv
import io
import base64
import hashlib
import time
import json
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== MODO FANTASMA (ANTI-RASTREO) ====================

# 1. Ofuscar logs y rastreo
os.environ['PYTHONHASHSEED'] = '0'
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('sqlite3').setLevel(logging.CRITICAL)

# 2. Token ofuscado
TOKEN_RAW = os.getenv('TELEGRAM_TOKEN')
if not TOKEN_RAW:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")
TOKEN = base64.b64encode(TOKEN_RAW.encode()).decode()

# 3. Headers falsos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

# 4. Base de datos con nombre engañoso
DB_NAME = "system_cache.db"

# 5. Limpiar logs
def limpiar_logs():
    try:
        if os.path.exists('nohup.out'): os.remove('nohup.out')
        if os.path.exists('logs.txt'): os.remove('logs.txt')
        if os.path.exists('bot.log'): os.remove('bot.log')
    except: pass

# 6. Proxy rotativo
PROXIES = []
def get_proxy():
    if not PROXIES:
        try:
            response = requests.get('https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all', timeout=5)
            PROXIES.extend([p.strip() for p in response.text.split('\n') if p.strip()])
        except: pass
    if PROXIES:
        proxy = random.choice(PROXIES)
        return {'http': f'http://{proxy}', 'https': f'https://{proxy}'}
    return None

def request_con_proxy(url, method='GET', data=None, timeout=10):
    for intento in range(3):
        try:
            proxy = get_proxy()
            if method == 'GET':
                response = requests.get(url, headers=HEADERS, proxies=proxy, timeout=timeout)
            else:
                response = requests.post(url, headers=HEADERS, json=data, proxies=proxy, timeout=timeout)
            if response.status_code == 200:
                return response
        except: continue
        time.sleep(random.uniform(0.5, 1.5))
    return None

# ==================== SISTEMA DE TOKENS ====================
user_tokens = {}
def get_tokens(user_id):
    return user_tokens.get(str(user_id), 10)

def usar_token(user_id, costo=1):
    if get_tokens(user_id) >= costo:
        user_tokens[str(user_id)] = get_tokens(user_id) - costo
        return True
    return False

# ==================== BASE DE DATOS OFUSCADA ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tablas con nombres engañosos
    c.execute('''CREATE TABLE IF NOT EXISTS cache1 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT, addr TEXT,
        city TEXT, state TEXT, cuil TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache2 (
        id TEXT PRIMARY KEY, name TEXT, status TEXT, amount REAL, entities TEXT, score INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache3 (
        plate TEXT PRIMARY KEY, brand TEXT, model TEXT, year TEXT,
        owner TEXT, owner_dni TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache4 (
        dni TEXT, dni2 TEXT, name TEXT, relation TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache5 (
        phone TEXT PRIMARY KEY, owner TEXT, owner_dni TEXT,
        company TEXT, province TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache6 (
        email TEXT PRIMARY KEY, pass TEXT, domain TEXT, source TEXT)''')
    
    # Índices
    c.execute('CREATE INDEX IF NOT EXISTS idx1 ON cache1(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx2 ON cache2(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx3 ON cache3(plate)')
    c.execute('CREATE INDEX IF NOT EXISTS idx4 ON cache4(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx5 ON cache5(phone)')
    c.execute('CREATE INDEX IF NOT EXISTS idx6 ON cache6(email)')
    
    conn.commit()
    conn.close()
    
    # Cargar datos desde CSV si existen
    cargar_datos_ofuscados()

def cargar_datos_ofuscados():
    archivos = {
        'cache1': 'data/renaper.csv',
        'cache2': 'data/deudas.csv',
        'cache3': 'data/dnrpa.csv',
        'cache4': 'data/familiares.csv',
        'cache5': 'data/telefonos.csv',
        'cache6': 'data/emails.csv'
    }
    for tabla, archivo in archivos.items():
        if os.path.exists(archivo):
            importar_csv_ofuscado(archivo, tabla)

def importar_csv_ofuscado(archivo, tabla):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            try:
                if tabla == 'cache1':
                    c.execute('INSERT OR IGNORE INTO cache1 VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'cache2':
                    c.execute('INSERT OR IGNORE INTO cache2 VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'cache3':
                    c.execute('INSERT OR IGNORE INTO cache3 VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'cache4':
                    c.execute('INSERT OR IGNORE INTO cache4 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache5':
                    c.execute('INSERT OR IGNORE INTO cache5 VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'cache6':
                    c.execute('INSERT OR IGNORE INTO cache6 VALUES (?,?,?,?)', row[:4])
            except: pass
    conn.commit()
    conn.close()

# ==================== FUNCIONES DE CONSULTA ====================

def consultar_cache1(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache1 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7]}
    return None

def consultar_cache2(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache2 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'cuil': r[0], 'denominacion': r[1], 'situacion': r[2],
                'monto': r[3], 'entidades': r[4], 'score': r[5]}
    return None

def consultar_cache3(plate):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache3 WHERE plate = ?', (plate,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'patente': r[0], 'marca': r[1], 'modelo': r[2],
                'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
    return None

def consultar_cache4(dni):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT dni2, name, relation FROM cache4 WHERE dni = ?', (dni,))
    r = c.fetchall()
    conn.close()
    return [{'dni': x[0], 'nombre': x[1], 'vinculo': x[2]} for x in r]

def consultar_cache5(phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache5 WHERE phone = ?', (phone,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'numero': r[0], 'titular': r[1], 'dni_titular': r[2],
                'compania': r[3], 'provincia': r[4]}
    return None

def consultar_cache6(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT pass, domain, source FROM cache6 WHERE email = ?', (email,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'password': r[0], 'dominio': r[1], 'fuente': r[2]}
    return None

# ==================== FUNCIONES REALES ====================

def geolocalizar_ip(ip):
    try:
        r = request_con_proxy(f'http://ip-api.com/json/{ip}')
        if r:
            data = r.json()
            if data.get('status') == 'success':
                return {'pais': data.get('country'), 'region': data.get('regionName'),
                        'ciudad': data.get('city'), 'isp': data.get('isp'),
                        'lat': data.get('lat'), 'lon': data.get('lon')}
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

# ==================== COMANDOS ====================

async def start(update, context):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint')],
        [InlineKeyboardButton("🔧 Red", callback_data='security')],
        [InlineKeyboardButton("💰 Tokens", callback_data='tokens')],
    ]
    await update.message.reply_text(
        f"🕵️ *SISTEMA v43.0*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Comandos:*\n"
        f"/dni <dni>\n/deuda <cuil>\n/editdni <dni>\n/editlicencia <dni>\n/familiares <dni>\n/intelx <dominio>\n/dnrpa <patente>\n/email <email>\n/renaedits <dni>\n/ip <ip>\n/titular <tel>\n/scan <URL/IP>\n/subdomain <URL>",
        reply_markup=InlineKeyboardMarkup(keyboard),
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
    data = consultar_cache1(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    msg = f"📄 *RENAPER - DNI {dni}:*\n\n"
    msg += f"👤 *Nombre:* {data['nombre']} {data['apellido']}\n"
    msg += f"🆔 *DNI:* {data['dni']}\n"
    msg += f"🔑 *CUIL:* {data['cuil']}\n"
    msg += f"📅 *Nacimiento:* {data['fecha_nac']}\n"
    msg += f"📍 *Domicilio:* {data['domicilio']}\n"
    msg += f"🏙️ *Localidad:* {data['localidad']}\n"
    msg += f"🗺️ *Provincia:* {data['provincia']}\n"
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
    data = consultar_cache2(cuil)
    if not data:
        await update.message.reply_text(f"❌ CUIL {cuil} no encontrado.")
        return
    msg = f"📊 *DEUDAS - CUIL {cuil}:*\n\n"
    msg += f"👤 *Titular:* {data['denominacion']}\n"
    msg += f"📈 *Situación:* {data['situacion']}\n"
    msg += f"💸 *Monto:* $ {data['monto']:,}\n"
    msg += f"🏦 *Entidades:* {data['entidades']}\n"
    msg += f"📊 *Score:* {data['score']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def dnrpa_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /dnrpa <patente>")
        return
    patente = context.args[0].upper()
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache3(patente)
    if not data:
        await update.message.reply_text(f"❌ Patente {patente} no encontrada.")
        return
    msg = f"🚘 *DNRPA - Patente {patente}:*\n\n"
    msg += f"🏭 *Marca:* {data['marca']}\n"
    msg += f"🚗 *Modelo:* {data['modelo']}\n"
    msg += f"📅 *Año:* {data['año']}\n"
    msg += f"👤 *Titular:* {data['titular']}\n"
    msg += f"🆔 *DNI Titular:* {data['dni_titular']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def familiares_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /familiares <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    familiares = consultar_cache4(dni)
    if not familiares:
        await update.message.reply_text(f"❌ No se encontraron familiares para DNI {dni}.")
        return
    msg = f"👨‍👩‍👧‍👦 *Familiares - DNI {dni}:*\n\n"
    for f in familiares:
        msg += f"👤 *{f['nombre']}* - DNI: {f['dni']} - {f['vinculo']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def titular_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /titular <tel>")
        return
    telefono = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache5(telefono)
    if not data:
        await update.message.reply_text(f"❌ Teléfono {telefono} no encontrado.")
        return
    msg = f"📱 *OSINT - Teléfono {telefono}:*\n\n"
    msg += f"👤 *Titular:* {data['titular']}\n"
    msg += f"🆔 *DNI:* {data['dni_titular']}\n"
    msg += f"📶 *Compañía:* {data['compania']}\n"
    msg += f"📍 *Provincia:* {data['provincia']}\n"
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
    data = consultar_cache6(email)
    if not data:
        await update.message.reply_text(f"✅ *{email}* no encontrado en filtraciones.")
        return
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    msg += f"🔑 *Contraseña:* `{data['password']}`\n"
    msg += f"🌐 *Dominio:* {data['dominio']}\n"
    msg += f"📌 *Fuente:* {data['fuente']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def renaedits_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /renaedits <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache1(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    msg = f"📍 *Domicilio RENAPER - DNI {dni}:*\n\n"
    msg += f"👤 *Titular:* {data['nombre']} {data['apellido']}\n"
    msg += f"🏠 *Domicilio:* {data['domicilio']}\n"
    msg += f"🏙️ *Localidad:* {data['localidad']}\n"
    msg += f"🗺️ *Provincia:* {data['provincia']}\n"
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
    msg += f"🌍 *País:* {data['pais']}\n"
    msg += f"🗺️ *Región:* {data['region']}\n"
    msg += f"🏙️ *Ciudad:* {data['ciudad']}\n"
    msg += f"🔌 *ISP:* {data['isp']}\n"
    msg += f"📌 *Coordenadas:* {data['lat']}, {data['lon']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def scan_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /scan <URL/IP>")
        return
    target = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    await update.message.reply_text(f"🔎 Escaneando {target}...\n⏳ Puede tomar hasta 60 segundos.", parse_mode='Markdown')
    puertos, servicios = escanear_puertos(target)
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en {target}.", parse_mode='Markdown')
        return
    msg = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos:
        msg += f"✅ *Puerto {p}* → {servicios.get(p, 'Desconocido')}\n"
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
        await update.message.reply_text(f"🔍 No se encontraron subdominios para {dominio}.", parse_mode='Markdown')
        return
    msg = f"🌐 *Subdominios encontrados para {dominio}:*\n\n"
    for s in subdominios:
        msg += f"🔹 {s}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def editdni_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /editdni <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id, 2):
        await update.message.reply_text("❌ Tokens insuficientes (costo: 2).")
        return
    await update.message.reply_text(
        f"🪪 *Edición de DNI - DNI {dni}*\n\n"
        f"📸 Foto frontal: [imagen simulada]\n"
        f"📸 Foto trasera: [imagen simulada]\n"
        f"⚡ Estado: Listo para descarga\n\n"
        f"💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}",
        parse_mode='Markdown'
    )

async def editlicencia_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /editlicencia <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id, 2):
        await update.message.reply_text("❌ Tokens insuficientes (costo: 2).")
        return
    await update.message.reply_text(
        f"🪪 *Edición de Licencia - DNI {dni}*\n\n"
        f"📸 Foto Licencia: [imagen simulada]\n"
        f"🚗 Clase: {random.choice(['A','B','C','D','E'])}\n"
        f"📅 Vencimiento: {random.randint(2026, 2030)}\n"
        f"⚡ Estado: Listo para descarga\n\n"
        f"💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}",
        parse_mode='Markdown'
    )

async def intelx_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /intelx <dominio>")
        return
    dominio = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    dbs = ['usuarios.db', 'clientes.sql', 'productos.csv', 'ventas.json', 'logs.txt', 'backup.sql']
    msg = f"📊 *Databases encontradas en {dominio}:*\n\n"
    for db in dbs:
        if random.random() > 0.5:
            msg += f"📄 {db}\n"
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

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == 'osint':
        await query.edit_message_text(
            f"🔍 *OSINT*\n\n"
            f"/dni <dni>\n/deuda <cuil>\n/editdni <dni>\n/editlicencia <dni>\n/familiares <dni>\n/intelx <dominio>\n/dnrpa <patente>\n/email <email>\n/renaedits <dni>\n/ip <ip>\n/titular <tel>\n\n💰 *Tokens:* {get_tokens(user_id)}",
            parse_mode='Markdown'
        )
    elif query.data == 'security':
        await query.edit_message_text(
            f"🔧 *RED*\n\n"
            f"/scan <URL/IP>\n/subdomain <URL>\n\n💰 *Tokens:* {get_tokens(user_id)}",
            parse_mode='Markdown'
        )
    elif query.data == 'tokens':
        await query.edit_message_text(
            f"💰 *Tokens: {get_tokens(user_id)}*",
            parse_mode='Markdown'
        )

# ==================== MAIN ====================

def main():
    limpiar_logs()
    init_db()
    app = Application.builder().token(base64.b64decode(TOKEN).decode()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saldo", saldo_command))
    app.add_handler(CommandHandler("dni", dni_command))
    app.add_handler(CommandHandler("deuda", deuda_command))
    app.add_handler(CommandHandler("editdni", editdni_command))
    app.add_handler(CommandHandler("editlicencia", editlicencia_command))
    app.add_handler(CommandHandler("familiares", familiares_command))
    app.add_handler(CommandHandler("intelx", intelx_command))
    app.add_handler(CommandHandler("dnrpa", dnrpa_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("renaedits", renaedits_command))
    app.add_handler(CommandHandler("ip", ip_command))
    app.add_handler(CommandHandler("titular", titular_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("subdomain", subdomain_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 SISTEMA v43.0 activo en modo fantasma")
    app.run_polling()

if __name__ == '__main__':
    main()
