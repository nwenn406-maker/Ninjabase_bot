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
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== MODO FANTASMA ====================

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

# 5. Limpiar logs automáticamente
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

limpiar_logs()

# ==================== BASE DE DATOS ====================

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ARGENTINA
    c.execute('''CREATE TABLE IF NOT EXISTS cache1 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT, addr TEXT,
        city TEXT, state TEXT, cuil TEXT, phone TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache2 (
        id TEXT PRIMARY KEY, name TEXT, status TEXT, amount REAL,
        entities TEXT, score INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache3 (
        plate TEXT PRIMARY KEY, brand TEXT, model TEXT, year TEXT,
        owner TEXT, owner_id TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache4 (
        phone TEXT PRIMARY KEY, owner TEXT, owner_id TEXT,
        company TEXT, province TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache5 (
        email TEXT PRIMARY KEY, pass TEXT, domain TEXT, source TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache6 (
        domain TEXT, user TEXT, pass TEXT, source TEXT)''')
    
    # GUATEMALA
    c.execute('''CREATE TABLE IF NOT EXISTS cache7 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT, addr TEXT,
        city TEXT, state TEXT, nit TEXT, phone TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache8 (
        id TEXT PRIMARY KEY, name TEXT, addr TEXT, phone TEXT, vehicle TEXT)''')
    
    # MÉXICO
    c.execute('''CREATE TABLE IF NOT EXISTS cache9 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        phone TEXT, addr TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache10 (
        id TEXT PRIMARY KEY, name TEXT, addr TEXT, phone TEXT)''')
    
    # EL SALVADOR
    c.execute('''CREATE TABLE IF NOT EXISTS cache11 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        addr TEXT, city TEXT, state TEXT, phone TEXT)''')
    
    # HONDURAS
    c.execute('''CREATE TABLE IF NOT EXISTS cache12 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        addr TEXT, city TEXT, state TEXT, phone TEXT)''')
    
    # CHILE
    c.execute('''CREATE TABLE IF NOT EXISTS cache13 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        addr TEXT, city TEXT, state TEXT, phone TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache14 (
        id TEXT PRIMARY KEY, name TEXT, addr TEXT, phone TEXT)''')
    
    # BRASIL
    c.execute('''CREATE TABLE IF NOT EXISTS cache15 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        addr TEXT, city TEXT, state TEXT, phone TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cache16 (
        id TEXT PRIMARY KEY, name TEXT, addr TEXT, phone TEXT)''')
    
    # ECUADOR
    c.execute('''CREATE TABLE IF NOT EXISTS cache17 (
        id TEXT PRIMARY KEY, name TEXT, last TEXT, birth TEXT,
        addr TEXT, state TEXT, phone TEXT)''')
    
    # Índices
    c.execute('CREATE INDEX IF NOT EXISTS idx1 ON cache1(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx2 ON cache2(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx3 ON cache3(plate)')
    c.execute('CREATE INDEX IF NOT EXISTS idx4 ON cache4(phone)')
    c.execute('CREATE INDEX IF NOT EXISTS idx5 ON cache5(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx6 ON cache6(domain)')
    c.execute('CREATE INDEX IF NOT EXISTS idx7 ON cache7(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx8 ON cache8(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx9 ON cache9(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx10 ON cache10(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx11 ON cache11(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx12 ON cache12(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx13 ON cache13(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx14 ON cache14(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx15 ON cache15(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx16 ON cache16(id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx17 ON cache17(id)')
    
    conn.commit()
    conn.close()
    cargar_datos()
    print("✅ Bases de datos inicializadas")

def cargar_datos():
    archivos = {
        'cache1': 'data/renaper.csv',
        'cache2': 'data/bcra.csv',
        'cache3': 'data/dnrpa.csv',
        'cache4': 'data/telefonos.csv',
        'cache5': 'data/emails.csv',
        'cache6': 'data/credenciales.csv',
        'cache7': 'data/guatemala_renap.csv',
        'cache8': 'data/guatemala_sat.csv',
        'cache9': 'data/mexico_imss.csv',
        'cache10': 'data/mexico_sat.csv',
        'cache11': 'data/salvador_dui.csv',
        'cache12': 'data/honduras_dni.csv',
        'cache13': 'data/chile_rc.csv',
        'cache14': 'data/chile_sii.csv',
        'cache15': 'data/brasil_cpf.csv',
        'cache16': 'data/brasil_rf.csv',
        'cache17': 'data/ecuador_registro_civil.csv'
    }
    for tabla, archivo in archivos.items():
        if os.path.exists(archivo):
            importar_csv(archivo, tabla)

def importar_csv(archivo, tabla):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            try:
                if tabla == 'cache1':
                    c.execute('INSERT OR IGNORE INTO cache1 VALUES (?,?,?,?,?,?,?,?,?)', row[:9])
                elif tabla == 'cache2':
                    c.execute('INSERT OR IGNORE INTO cache2 VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'cache3':
                    c.execute('INSERT OR IGNORE INTO cache3 VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'cache4':
                    c.execute('INSERT OR IGNORE INTO cache4 VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'cache5':
                    c.execute('INSERT OR IGNORE INTO cache5 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache6':
                    c.execute('INSERT OR IGNORE INTO cache6 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache7':
                    c.execute('INSERT OR IGNORE INTO cache7 VALUES (?,?,?,?,?,?,?,?,?)', row[:9])
                elif tabla == 'cache8':
                    c.execute('INSERT OR IGNORE INTO cache8 VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'cache9':
                    c.execute('INSERT OR IGNORE INTO cache9 VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'cache10':
                    c.execute('INSERT OR IGNORE INTO cache10 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache11':
                    c.execute('INSERT OR IGNORE INTO cache11 VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'cache12':
                    c.execute('INSERT OR IGNORE INTO cache12 VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'cache13':
                    c.execute('INSERT OR IGNORE INTO cache13 VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'cache14':
                    c.execute('INSERT OR IGNORE INTO cache14 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache15':
                    c.execute('INSERT OR IGNORE INTO cache15 VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'cache16':
                    c.execute('INSERT OR IGNORE INTO cache16 VALUES (?,?,?,?)', row[:4])
                elif tabla == 'cache17':
                    c.execute('INSERT OR IGNORE INTO cache17 VALUES (?,?,?,?,?,?,?)', row[:7])
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
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'cuil': r[7], 'phone': r[8]}
    return None

def consultar_cache2(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache2 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'status': r[2], 'amount': r[3], 'entities': r[4], 'score': r[5]}
    return None

def consultar_cache3(plate):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache3 WHERE plate = ?', (plate,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'plate': r[0], 'brand': r[1], 'model': r[2], 'year': r[3], 'owner': r[4], 'owner_id': r[5]}
    return None

def consultar_cache4(phone):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache4 WHERE phone = ?', (phone,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'phone': r[0], 'owner': r[1], 'owner_id': r[2], 'company': r[3], 'province': r[4]}
    return None

def consultar_cache5(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT pass, domain, source FROM cache5 WHERE email = ?', (email,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'pass': r[0], 'domain': r[1], 'source': r[2]}
    return None

def consultar_cache6(domain):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user, pass, source FROM cache6 WHERE domain = ?', (domain,))
    r = c.fetchall()
    conn.close()
    return [{'user': x[0], 'pass': x[1], 'source': x[2]} for x in r]

def consultar_cache7(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache7 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'nit': r[7], 'phone': r[8]}
    return None

def consultar_cache8(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache8 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'addr': r[2], 'phone': r[3], 'vehicle': r[4]}
    return None

def consultar_cache9(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache9 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3], 'phone': r[4], 'addr': r[5]}
    return None

def consultar_cache10(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache10 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'addr': r[2], 'phone': r[3]}
    return None

def consultar_cache11(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache11 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'phone': r[7]}
    return None

def consultar_cache12(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache12 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'phone': r[7]}
    return None

def consultar_cache13(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache13 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'phone': r[7]}
    return None

def consultar_cache14(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache14 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'addr': r[2], 'phone': r[3]}
    return None

def consultar_cache15(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache15 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'city': r[5], 'state': r[6], 'phone': r[7]}
    return None

def consultar_cache16(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache16 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'addr': r[2], 'phone': r[3]}
    return None

def consultar_cache17(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM cache17 WHERE id = ?', (id,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'id': r[0], 'name': r[1], 'last': r[2], 'birth': r[3],
                'addr': r[4], 'state': r[5], 'phone': r[6]}
    return None

# ==================== FUNCIONES REALES ====================

def geolocalizar_ip(ip):
    try:
        r = request_con_proxy(f'http://ip-api.com/json/{ip}')
        if r:
            data = r.json()
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
        [InlineKeyboardButton("🇬🇹 Guatemala", callback_data='gt_menu')],
        [InlineKeyboardButton("🇲🇽 México", callback_data='mx_menu')],
        [InlineKeyboardButton("🇸🇻 El Salvador", callback_data='sv_menu')],
        [InlineKeyboardButton("🇭🇳 Honduras", callback_data='hn_menu')],
        [InlineKeyboardButton("🇨🇱 Chile", callback_data='cl_menu')],
        [InlineKeyboardButton("🇧🇷 Brasil", callback_data='br_menu')],
        [InlineKeyboardButton("🇪🇨 Ecuador", callback_data='ec_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='security')],
        [InlineKeyboardButton("💰 Tokens", callback_data='tokens')],
    ]
    await update.message.reply_text(
        f"🕵️ *SISTEMA v61.0 - MODO FANTASMA*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Países:* 8\n"
        f"🌎 *Argentina, Guatemala, México, El Salvador,*\n"
        f"   *Honduras, Chile, Brasil, Ecuador*\n\n"
        f"💡 *Selecciona un país para ver sus comandos*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ==================== ARGENTINA ====================

async def arg_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇦🇷 *ARGENTINA - OSINT*\n\n"
        f"/dni <dni>\n/deuda <cuil>\n/dnrpa <patente>\n/email <email>\n/titular <tel>\n/url <dominio>\n/ip <ip>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def dni_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /dni <dni>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache1(id)
    if not data:
        await update.message.reply_text(f"❌ DNI {id} no encontrado.")
        return
    msg = f"📄 *RENAPER - DNI {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n🔑 {data['cuil']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def deuda_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /deuda <cuil>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache2(id)
    if not data:
        await update.message.reply_text(f"❌ CUIL {id} no encontrado.")
        return
    msg = f"📊 *BCRA - CUIL {id}:*\n\n"
    msg += f"👤 {data['name']}\n📈 {data['status']}\n💸 $ {data['amount']:,}\n🏦 {data['entities']}\n📊 Score: {data['score']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def dnrpa_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /dnrpa <patente>")
        return
    plate = context.args[0].upper()
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache3(plate)
    if not data:
        await update.message.reply_text(f"❌ Patente {plate} no encontrada.")
        return
    msg = f"🚘 *DNRPA - Patente {plate}:*\n\n"
    msg += f"🏭 {data['brand']}\n🚗 {data['model']}\n📅 {data['year']}\n👤 {data['owner']}\n🆔 {data['owner_id']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== GUATEMALA ====================

async def gt_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇬🇹 *GUATEMALA - OSINT*\n\n"
        f"/gt_dpi <dpi>\n/gt_nit <nit>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def gt_dpi_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /gt_dpi <dpi>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache7(id)
    if not data:
        await update.message.reply_text(f"❌ DPI {id} no encontrado.")
        return
    msg = f"📄 *RENAP Guatemala - DPI {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n🔑 {data['nit']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== MÉXICO ====================

async def mx_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇲🇽 *MÉXICO - OSINT*\n\n"
        f"/mx_imss <curp>\n/mx_sat <rfc>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def mx_imss_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /mx_imss <curp>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache9(id)
    if not data:
        await update.message.reply_text(f"❌ CURP {id} no encontrado.")
        return
    msg = f"🇲🇽 *IMSS - CURP {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📱 {data['phone']}\n📍 {data['addr']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== EL SALVADOR ====================

async def sv_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇸🇻 *EL SALVADOR - OSINT*\n\n"
        f"/sv_dui <dui>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def sv_dui_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /sv_dui <dui>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache11(id)
    if not data:
        await update.message.reply_text(f"❌ DUI {id} no encontrado.")
        return
    msg = f"🇸🇻 *DUI - {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== HONDURAS ====================

async def hn_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇭🇳 *HONDURAS - OSINT*\n\n"
        f"/hn_dni <dni>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def hn_dni_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /hn_dni <dni>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache12(id)
    if not data:
        await update.message.reply_text(f"❌ DNI {id} no encontrado.")
        return
    msg = f"🇭🇳 *DNI - {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== CHILE ====================

async def cl_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇨🇱 *CHILE - OSINT*\n\n"
        f"/cl_rc <rut>\n/cl_sii <rut>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def cl_rc_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /cl_rc <rut>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache13(id)
    if not data:
        await update.message.reply_text(f"❌ RUT {id} no encontrado.")
        return
    msg = f"🇨🇱 *Registro Civil - RUT {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== BRASIL ====================

async def br_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇧🇷 *BRASIL - OSINT*\n\n"
        f"/br_cpf <cpf>\n/br_rf <cpf>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def br_cpf_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /br_cpf <cpf>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache15(id)
    if not data:
        await update.message.reply_text(f"❌ CPF {id} no encontrado.")
        return
    msg = f"🇧🇷 *CPF - {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== ECUADOR ====================

async def ec_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇪🇨 *ECUADOR - OSINT*\n\n"
        f"/ec_cedula <cedula>\n\n"
        f"💰 *Tokens:* {get_tokens(update.callback_query.from_user.id)}",
        parse_mode='Markdown'
    )

async def ec_cedula_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /ec_cedula <cedula>")
        return
    id = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache17(id)
    if not data:
        await update.message.reply_text(f"❌ Cédula {id} no encontrada.")
        return
    msg = f"🇪🇨 *Registro Civil - Cédula {id}:*\n\n"
    msg += f"👤 {data['name']} {data['last']}\n🆔 {data['id']}\n📅 {data['birth']}\n📍 {data['addr']}\n📱 {data['phone']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

# ==================== COMANDOS GENERALES ====================

async def email_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /email <email>")
        return
    email = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_cache5(email)
    if not data:
        await update.message.reply_text(f"✅ {email} no se encontró en filtraciones.")
        return
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    msg += f"🔑 `{data['pass']}`\n🌐 {data['domain']}\n📌 {data['source']}\n"
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
    data = consultar_cache6(domain)
    if data:
        msg = f"🔴 *CREDENCIALES ENCONTRADAS* - {domain}\n\n"
        for c in data[:20]:
            msg += f"👤 `{c['user']}`\n🔑 `{c['pass']}`\n📌 {c['source']}\n\n"
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
    data = consultar_cache4(phone)
    if not data:
        await update.message.reply_text(f"❌ Teléfono {phone} no encontrado.")
        return
    msg = f"📱 *OSINT - Teléfono {phone}:*\n\n"
    msg += f"👤 {data['owner']}\n🆔 {data['owner_id']}\n📶 {data['company']}\n📍 {data['province']}\n"
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
    msg += f"🌍 {data.get('country', 'N/A')}\n🗺️ {data.get('regionName', 'N/A')}\n🏙️ {data.get('city', 'N/A')}\n🔌 {data.get('isp', 'N/A')}\n📌 {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}\n"
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
    await update.message.reply_text(f"🔎 Escaneando {target}...", parse_mode='Markdown')
    puertos, servicios = escanear_puertos(target)
    if not puertos:
        await update.message.reply_text(f"🔒 No se encontraron puertos abiertos en {target}.", parse_mode='Markdown')
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
        await update.message.reply_text(f"🔍 No se encontraron subdominios para {dominio}.", parse_mode='Markdown')
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

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'arg_menu':
        await arg_menu(update, context)
    elif query.data == 'gt_menu':
        await gt_menu(update, context)
    elif query.data == 'mx_menu':
        await mx_menu(update, context)
    elif query.data == 'sv_menu':
        await sv_menu(update, context)
    elif query.data == 'hn_menu':
        await hn_menu(update, context)
    elif query.data == 'cl_menu':
        await cl_menu(update, context)
    elif query.data == 'br_menu':
        await br_menu(update, context)
    elif query.data == 'ec_menu':
        await ec_menu(update, context)
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
    app = Application.builder().token(base64.b64decode(TOKEN).decode()).build()
    
    # Argentina
    app.add_handler(CommandHandler("dni", dni_command))
    app.add_handler(CommandHandler("deuda", deuda_command))
    app.add_handler(CommandHandler("dnrpa", dnrpa_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("titular", titular_command))
    app.add_handler(CommandHandler("url", url_command))
    app.add_handler(CommandHandler("ip", ip_command))
    
    # Guatemala
    app.add_handler(CommandHandler("gt_dpi", gt_dpi_command))
    app.add_handler(CommandHandler("gt_nit", gt_nit_command))
    
    # México
    app.add_handler(CommandHandler("mx_imss", mx_imss_command))
    app.add_handler(CommandHandler("mx_sat", mx_sat_command))
    
    # El Salvador
    app.add_handler(CommandHandler("sv_dui", sv_dui_command))
    
    # Honduras
    app.add_handler(CommandHandler("hn_dni", hn_dni_command))
    
    # Chile
    app.add_handler(CommandHandler("cl_rc", cl_rc_command))
    app.add_handler(CommandHandler("cl_sii", cl_sii_command))
    
    # Brasil
    app.add_handler(CommandHandler("br_cpf", br_cpf_command))
    app.add_handler(CommandHandler("br_rf", br_rf_command))
    
    # Ecuador
    app.add_handler(CommandHandler("ec_cedula", ec_cedula_command))
    
    # Generales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("saldo", saldo_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("subdomain", subdomain_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 SISTEMA v61.0 - MODO FANTASMA iniciado")
    print("📊 8 países integrados")
    print("🔐 Modo fantasma: activado")
    app.run_polling()

if __name__ == '__main__':
    main()
