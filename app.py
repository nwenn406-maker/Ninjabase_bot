import os
import logging
import csv
import sqlite3
import requests
import socket
import random
import base64
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# ==================== MODO FANTASMA ====================
os.environ['PYTHONHASHSEED'] = '0'
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)

TOKEN = base64.b64encode(TOKEN.encode()).decode()

# ==================== BASE DE DATOS ====================
DB_NAME = "data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tablas para millones de registros
    c.execute('''CREATE TABLE IF NOT EXISTS renaper (
        dni TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
        domicilio TEXT, localidad TEXT, provincia TEXT, cuil TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS deudas (
        cuil TEXT PRIMARY KEY, denominacion TEXT, situacion TEXT,
        monto REAL, entidades TEXT, score INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dnrpa (
        patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, año TEXT,
        titular TEXT, dni_titular TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS familiares (
        dni_principal TEXT, dni_familiar TEXT, nombre_familiar TEXT, vinculo TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS telefonos (
        numero TEXT PRIMARY KEY, titular TEXT, dni_titular TEXT,
        compania TEXT, provincia TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
        email TEXT PRIMARY KEY, password TEXT, dominio TEXT, fuente TEXT)''')
    
    # Índices para búsquedas rápidas
    c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_deudas ON deudas(cuil)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
    
    conn.commit()
    conn.close()
    
    # Cargar datos desde archivos CSV si existen
    cargar_datos()

def cargar_datos():
    archivos = {
        'renaper': 'renaper.csv',
        'deudas': 'deudas.csv',
        'dnrpa': 'dnrpa.csv',
        'familiares': 'familiares.csv',
        'telefonos': 'telefonos.csv',
        'emails': 'emails.csv'
    }
    for tabla, archivo in archivos.items():
        if os.path.exists(archivo) and os.path.getsize(archivo) > 0:
            importar_csv(archivo, tabla)

def importar_csv(archivo, tabla):
    """Importa archivos CSV masivos (millones de registros)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    print(f"📥 Importando {archivo}...")
    count = 0
    with open(archivo, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            try:
                if tabla == 'renaper':
                    c.execute('INSERT OR IGNORE INTO renaper VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'deudas':
                    c.execute('INSERT OR IGNORE INTO deudas VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'dnrpa':
                    c.execute('INSERT OR IGNORE INTO dnrpa VALUES (?,?,?,?,?,?)', row[:6])
                elif tabla == 'familiares':
                    c.execute('INSERT OR IGNORE INTO familiares VALUES (?,?,?,?)', row[:4])
                elif tabla == 'telefonos':
                    c.execute('INSERT OR IGNORE INTO telefonos VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'emails':
                    c.execute('INSERT OR IGNORE INTO emails VALUES (?,?,?,?)', row[:4])
                count += 1
            except: pass
            if count % 100000 == 0:
                conn.commit()
                print(f"📊 {count} registros importados...")
    conn.commit()
    conn.close()
    print(f"✅ {archivo} importado con {count} registros")

# ==================== FUNCIONES DE CONSULTA ====================

def consultar_renaper(dni):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM renaper WHERE dni = ?', (dni,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7]}
    return None

def consultar_deuda(cuil):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM deudas WHERE cuil = ?', (cuil,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'cuil': r[0], 'denominacion': r[1], 'situacion': r[2],
                'monto': r[3], 'entidades': r[4], 'score': r[5]}
    return None

def consultar_patente(patente):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'patente': r[0], 'marca': r[1], 'modelo': r[2],
                'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
    return None

def consultar_familiares(dni):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT dni_familiar, nombre_familiar, vinculo FROM familiares WHERE dni_principal = ?', (dni,))
    r = c.fetchall()
    conn.close()
    return [{'dni': x[0], 'nombre': x[1], 'vinculo': x[2]} for x in r]

def consultar_titular(telefono):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM telefonos WHERE numero = ?', (telefono,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'numero': r[0], 'titular': r[1], 'dni_titular': r[2],
                'compania': r[3], 'provincia': r[4]}
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

# ==================== FUNCIONES REALES ====================

def geolocalizar_ip(ip):
    try:
        r = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
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
        [InlineKeyboardButton("🔍 OSINT", callback_data='osint')],
        [InlineKeyboardButton("🔧 Red", callback_data='security')],
        [InlineKeyboardButton("💰 Tokens", callback_data='tokens')],
    ]
    await update.message.reply_text(
        f"🕵️ *NINJA DATA BOT v44.0*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"🔹 *Comandos disponibles:*\n"
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
    data = consultar_renaper(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado en la base de datos global.")
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

# ==================== TODOS LOS DEMÁS COMANDOS ====================
# (deuda, editdni, editlicencia, familiares, intelx, dnrpa, email, renaedits, ip, titular, scan, subdomain)
# ... (misma estructura que antes, usando las funciones de consulta)

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

def main():
    init_db()
    app = Application.builder().token(base64.b64decode(TOKEN).decode()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dni", dni_command))
    # ... resto de comandos
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 NINJA DATA BOT v44.0 iniciado")
    app.run_polling()

if __name__ == '__main__':
    main()
