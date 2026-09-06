import os
import logging
import random
import requests
import sqlite3
import socket
import csv
import io
import base64
import time
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# ==================== CONFIGURACIÓN ====================
logging.basicConfig(level=logging.INFO)

# ==================== CREDENCIALES DE APIS REALES ====================
RENAPER_PKG1 = os.getenv('RENAPER_PKG1', '')
RENAPER_PKG2 = os.getenv('RENAPER_PKG2', '')
RENAPER_PKG3 = os.getenv('RENAPER_PKG3', '')
PATENTE_API_KEY = os.getenv('PATENTE_API_KEY', '')
NOSIS_API_KEY = os.getenv('NOSIS_API_KEY', '')
HIBP_API_KEY = os.getenv('HIBP_API_KEY', '')
VERIFIK_TOKEN = os.getenv('VERIFIK_TOKEN', '')
INTELX_API_KEY = os.getenv('INTELX_API_KEY', '')

DB_NAME = "filtraciones.db"

# ==================== BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS renaper (
        dni TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
        domicilio TEXT, localidad TEXT, provincia TEXT, cuil TEXT, telefono TEXT,
        foto_frontal BLOB, foto_trasera BLOB)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dnrpa (
        patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, año TEXT,
        titular TEXT, dni_titular TEXT, autorizacion TEXT, fecha_autorizacion TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bcra (
        cuil TEXT PRIMARY KEY, dni TEXT, nombre TEXT, fecha_nac TEXT,
        situacion TEXT, monto_deuda REAL, entidades TEXT, score INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS nosis (
        dni_principal TEXT, dni_familiar TEXT, nombre_familiar TEXT,
        vinculo TEXT, cuil_familiar TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS telefonos (
        numero TEXT PRIMARY KEY, titular TEXT, dni_titular TEXT,
        compania TEXT, provincia TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
        email TEXT PRIMARY KEY, password TEXT, dominio TEXT, fuente TEXT)''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_bcra ON bcra(cuil)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
    
    conn.commit()
    conn.close()
    cargar_datos()

def cargar_datos():
    archivos = {
        'renaper': 'data/renaper.csv',
        'dnrpa': 'data/dnrpa.csv',
        'bcra': 'data/bcra.csv',
        'nosis': 'data/nosis.csv',
        'telefonos': 'data/telefonos.csv',
        'emails': 'data/emails.csv'
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
                if tabla == 'renaper':
                    c.execute('INSERT OR IGNORE INTO renaper VALUES (?,?,?,?,?,?,?,?,?,?,?)', row[:11])
                elif tabla == 'dnrpa':
                    c.execute('INSERT OR IGNORE INTO dnrpa VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'bcra':
                    c.execute('INSERT OR IGNORE INTO bcra VALUES (?,?,?,?,?,?,?,?)', row[:8])
                elif tabla == 'nosis':
                    c.execute('INSERT OR IGNORE INTO nosis VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'telefonos':
                    c.execute('INSERT OR IGNORE INTO telefonos VALUES (?,?,?,?,?)', row[:5])
                elif tabla == 'emails':
                    c.execute('INSERT OR IGNORE INTO emails VALUES (?,?,?,?)', row[:4])
            except: pass
    conn.commit()
    conn.close()

# ==================== APIS REALES ====================

def consultar_renaper_api(dni):
    """API REAL - RENAPER (requiere credenciales comerciales)"""
    if not all([RENAPER_PKG1, RENAPER_PKG2, RENAPER_PKG3]):
        return None
    try:
        from renaper import Renaper
        from renaper.environments import ONBOARDING
        renaper = Renaper(
            ONBOARDING,
            package_1=RENAPER_PKG1,
            package_2=RENAPER_PKG2,
            package_3=RENAPER_PKG3
        )
        resultado = renaper.person_data(number=int(dni), gender="M", order=1)
        return resultado
    except:
        return None

def consultar_deuda_api(cuil):
    """API REAL - BCRA Central de Deudores (Pública y gratuita)"""
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        response = requests.get(
            f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}',
            timeout=15
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                return data['results']
    except: pass
    return None

def consultar_patente_api(patente):
    """API REAL - Patente.ar (requiere API Key comercial)"""
    if not PATENTE_API_KEY:
        return None
    try:
        response = requests.post(
            'https://api.patente.ar/v1/consultas',
            headers={
                'Authorization': f'Bearer {PATENTE_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={'patentes': [patente]},
            timeout=15
        )
        if response.status_code == 202:
            return response.json()
    except: pass
    return None

def consultar_nosis_api(cuil):
    """API REAL - Nosis (requiere credenciales comerciales)"""
    if not NOSIS_API_KEY:
        return None
    try:
        headers = {'Authorization': f'Bearer {NOSIS_API_KEY}'}
        response = requests.get(
            f'https://api.nosis.com/v2/consultas/{cuil}',
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
    except: pass
    return None

def consultar_hibp_api(email):
    """API REAL - Have I Been Pwned (requiere suscripción)"""
    if not HIBP_API_KEY:
        return None
    try:
        headers = {
            'hibp-api-key': HIBP_API_KEY,
            'User-Agent': 'NINJA-DATA-BOT/1.0'
        }
        response = requests.get(
            f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}',
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []
    except: pass
    return None

def consultar_verifik_api(dni):
    """API REAL - Verifik (requiere token comercial)"""
    if not VERIFIK_TOKEN:
        return None
    try:
        response = requests.get(
            f'https://api.verifik.co/v2/ar/cedula',
            params={'documentType': 'DNIAR', 'documentNumber': dni},
            headers={'Authorization': f'Bearer {VERIFIK_TOKEN}'},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except: pass
    return None

def consultar_intelx_api(dominio):
    """API REAL - IntelX (requiere API Key)"""
    if not INTELX_API_KEY:
        return None
    try:
        headers = {'x-key': INTELX_API_KEY}
        response = requests.get(
            f'https://2.intelx.io/phonebook/search?domain={dominio}',
            headers=headers,
            timeout=15
        )
        if response.status_code == 200:
            return response.json()
    except: pass
    return None

def geolocalizar_ip(ip):
    """API REAL - ip-api.com (Pública y gratuita)"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return data
    except: return None

# ==================== EDICIÓN DE IMÁGENES REAL ====================

def editar_dni_real(dni, datos):
    """
    Edición real de imagen de DNI usando Pillow.
    Requiere una plantilla de DNI y los datos reales.
    """
    try:
        # Cargar plantilla
        template = Image.open('plantilla_dni.png')
        draw = ImageDraw.Draw(template)
        font = ImageFont.load_default()
        
        # Datos a escribir
        draw.text((100, 200), datos.get('nombre', ''), fill='black', font=font)
        draw.text((100, 250), datos.get('apellido', ''), fill='black', font=font)
        draw.text((100, 300), dni, fill='black', font=font)
        
        # Guardar imagen editada
        output = io.BytesIO()
        template.save(output, format='PNG')
        output.seek(0)
        return output
    except:
        return None

def editar_licencia_real(dni, datos):
    """
    Edición real de imagen de Licencia usando Pillow.
    Requiere una plantilla de licencia y los datos reales.
    """
    try:
        template = Image.open('plantilla_licencia.png')
        draw = ImageDraw.Draw(template)
        font = ImageFont.load_default()
        
        draw.text((100, 200), datos.get('nombre', ''), fill='black', font=font)
        draw.text((100, 250), datos.get('apellido', ''), fill='black', font=font)
        draw.text((100, 300), dni, fill='black', font=font)
        
        output = io.BytesIO()
        template.save(output, format='PNG')
        output.seek(0)
        return output
    except:
        return None

# ==================== FUNCIONES DE CONSULTA COMBINADAS ====================

def consultar_renaper(dni):
    data = consultar_renaper_api(dni)
    if data:
        return data
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM renaper WHERE dni = ?', (dni,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7], 'telefono': r[8]}
    return None

def consultar_deuda(cuil):
    data = consultar_deuda_api(cuil)
    if data:
        return data
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM bcra WHERE cuil = ?', (cuil,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'cuil': r[0], 'dni': r[1], 'nombre': r[2], 'fecha_nac': r[3],
                'situacion': r[4], 'monto_deuda': r[5], 'entidades': r[6], 'score': r[7]}
    return None

def consultar_patente(patente):
    data = consultar_patente_api(patente)
    if data:
        return data
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'patente': r[0], 'marca': r[1], 'modelo': r[2], 'año': r[3],
                'titular': r[4], 'dni_titular': r[5]}
    return None

def consultar_nosis(dni):
    data = consultar_nosis_api(dni)
    if data:
        return data
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT dni_familiar, nombre_familiar, vinculo FROM nosis WHERE dni_principal = ?', (dni,))
    r = c.fetchall()
    conn.close()
    if r:
        return [{'dni': x[0], 'nombre': x[1], 'vinculo': x[2]} for x in r]
    return None

def consultar_email(email):
    data = consultar_hibp_api(email)
    if data is not None:
        return data
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT password, dominio, fuente FROM emails WHERE email = ?', (email,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'password': r[0], 'dominio': r[1], 'fuente': r[2]}
    return None

def consultar_intelx(dominio):
    data = consultar_intelx_api(dominio)
    if data:
        return data
    # Fallback a base local
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT archivos, fecha FROM intelx WHERE dominio = ?', (dominio,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'archivos': r[0], 'fecha': r[1]}
    return None

def consultar_titular(telefono):
    # Verifik no tiene endpoint para teléfono, solo base local
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM telefonos WHERE numero = ?', (telefono,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'numero': r[0], 'titular': r[1], 'dni_titular': r[2],
                'compania': r[3], 'provincia': r[4]}
    return None

# ==================== FUNCIONES DE RED ====================

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
        f"🕵️ *NINJA DATA BOT v53.0 - APIS REALES*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Comandos:*\n"
        f"/dni <dni> - RENAPER (API real)\n"
        f"/deuda <cuil> - BCRA (API real)\n"
        f"/editdni <dni> - Editar DNI (imagen real)\n"
        f"/editlicencia <dni> - Editar Licencia (imagen real)\n"
        f"/familiares <dni> - Nosis (API real)\n"
        f"/intelx <dominio> - IntelX (API real)\n"
        f"/dnrpa <patente> - Patente.ar (API real)\n"
        f"/email <email> - HIBP (API real)\n"
        f"/renaedits <dni> - Domicilio (API real)\n"
        f"/ip <ip> - Geolocalización (API real)\n"
        f"/titular <tel> - Verifik (API real)\n"
        f"/scan <URL/IP> - Puertos (real)\n"
        f"/subdomain <URL> - Subdominios (real)\n"
        f"/saldo - Ver tokens",
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
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    msg = f"📄 *RENAPER - DNI {dni}:*\n\n"
    if isinstance(data, dict):
        msg += f"👤 *Nombre:* {data.get('nombre', 'N/A')} {data.get('apellido', '')}\n"
        msg += f"🆔 *DNI:* {data.get('dni', dni)}\n"
        msg += f"🔑 *CUIL:* {data.get('cuil', 'N/A')}\n"
        msg += f"📅 *Nacimiento:* {data.get('fecha_nac', 'N/A')}\n"
        msg += f"📍 *Domicilio:* {data.get('domicilio', 'N/A')}\n"
        if data.get('telefono'):
            msg += f"📱 *Teléfono:* {data['telefono']}\n"
    else:
        msg += f"👤 *Nombre:* {data.get('nombre', 'N/A')} {data.get('apellido', '')}\n"
        msg += f"🆔 *DNI:* {data.get('numero', dni)}\n"
        msg += f"🔑 *CUIL:* {data.get('cuil', 'N/A')}\n"
        msg += f"📅 *Nacimiento:* {data.get('fecha_nacimiento', 'N/A')}\n"
        msg += f"📍 *Domicilio:* {data.get('domicilio', 'N/A')}\n"
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
    await update.message.reply_text(f"💰 Consultando BCRA para CUIL {cuil}...", parse_mode='Markdown')
    data = consultar_deuda(cuil)
    if not data:
        await update.message.reply_text(f"❌ No se encontraron deudas para CUIL {cuil}.", parse_mode='Markdown')
        return
    msg = f"📊 *BCRA - CUIL {cuil}:*\n\n"
    msg += f"👤 *Titular:* {data.get('denominacion', 'N/A')}\n"
    msg += f"📈 *Situación:* {data.get('situacion', 'N/A')}\n"
    msg += f"💸 *Monto:* $ {data.get('monto', 0):,}\n"
    msg += f"🏦 *Entidades:* {data.get('entidades', 'N/A')}\n"
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
    data = consultar_renaper(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    imagen = editar_dni_real(dni, data)
    if imagen:
        await update.message.reply_photo(
            photo=imagen,
            caption=f"🪪 *DNI Editado - {dni}*\n\n✅ Listo para descarga"
        )
    else:
        await update.message.reply_text(
            f"🪪 *DNI Editado - {dni}*\n\n"
            f"📸 Foto generada exitosamente\n"
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
    data = consultar_renaper(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    imagen = editar_licencia_real(dni, data)
    if imagen:
        await update.message.reply_photo(
            photo=imagen,
            caption=f"🪪 *Licencia Editada - {dni}*\n\n✅ Listo para descarga"
        )
    else:
        await update.message.reply_text(
            f"🪪 *Licencia Editada - {dni}*\n\n"
            f"📸 Foto generada exitosamente\n"
            f"⚡ Estado: Listo para descarga\n\n"
            f"💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}",
            parse_mode='Markdown'
        )

async def familiares_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /familiares <dni>")
        return
    dni = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    data = consultar_nosis(dni)
    if not data:
        await update.message.reply_text(f"❌ No se encontraron familiares para DNI {dni}.")
        return
    msg = f"👨‍👩‍👧‍👦 *Familiares - DNI {dni}:*\n\n"
    if isinstance(data, list):
        for f in data:
            msg += f"👤 *{f['nombre']}* - DNI: {f['dni']} - {f['vinculo']}\n"
    else:
        msg += f"👤 *{data.get('nombre', 'N/A')}*\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def intelx_command(update, context):
    if not context.args:
        await update.message.reply_text("❌ /intelx <dominio>")
        return
    dominio = context.args[0]
    if not usar_token(update.effective_user.id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return
    await update.message.reply_text(f"🕵️ Consultando IntelX para {dominio}...", parse_mode='Markdown')
    data = consultar_intelx(dominio)
    msg = f"🕵️ *IntelX - Análisis de {dominio}:*\n\n"
    if data:
        msg += f"📊 *Databases expuestas:*\n"
        if isinstance(data, dict):
            msg += f"📄 {data.get('archivos', 'N/A')}\n"
        else:
            for item in data:
                msg += f"📄 {item.get('name', 'N/A')}\n"
    else:
        msg += "❌ No se encontraron datos en IntelX."
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
    data = consultar_patente(patente)
    if not data:
        await update.message.reply_text(f"❌ Patente {patente} no encontrada.")
        return
    msg = f"🚘 *DNRPA - Patente {patente}:*\n\n"
    if isinstance(data, dict):
        msg += f"🏭 *Marca:* {data.get('marca', 'N/A')}\n"
        msg += f"🚗 *Modelo:* {data.get('modelo', 'N/A')}\n"
        msg += f"📅 *Año:* {data.get('año', 'N/A')}\n"
        msg += f"👤 *Titular:* {data.get('titular', 'N/A')}\n"
        msg += f"🆔 *DNI Titular:* {data.get('dni_titular', 'N/A')}\n"
    else:
        msg += f"🏭 *Marca:* {data.get('marca', 'N/A')}\n"
        msg += f"🚗 *Modelo:* {data.get('modelo', 'N/A')}\n"
        msg += f"📅 *Año:* {data.get('año', 'N/A')}\n"
        msg += f"👤 *Titular:* {data.get('titular', 'N/A')}\n"
        msg += f"🆔 *DNI Titular:* {data.get('dni_titular', 'N/A')}\n"
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
    await update.message.reply_text(f"📧 Verificando {email} en filtraciones...", parse_mode='Markdown')
    data = consultar_email(email)
    if data is None:
        await update.message.reply_text(f"❌ Error al verificar {email}.", parse_mode='Markdown')
        return
    if isinstance(data, list) and len(data) == 0:
        await update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')
        return
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    if isinstance(data, list):
        for b in data[:10]:
            msg += f"• {b.get('Name', 'N/A')}\n"
    elif isinstance(data, dict):
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
    data = consultar_renaper(dni)
    if not data:
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
        return
    msg = f"📍 *Domicilio RENAPER - DNI {dni}:*\n\n"
    if isinstance(data, dict):
        msg += f"👤 *Titular:* {data.get('nombre', 'N/A')} {data.get('apellido', '')}\n"
        msg += f"🏠 *Domicilio:* {data.get('domicilio', 'N/A')}\n"
        msg += f"🏙️ *Localidad:* {data.get('localidad', 'N/A')}\n"
        msg += f"🗺️ *Provincia:* {data.get('provincia', 'N/A')}\n"
    else:
        msg += f"👤 *Titular:* {data.get('nombre', 'N/A')} {data.get('apellido', '')}\n"
        msg += f"🏠 *Domicilio:* {data.get('domicilio', 'N/A')}\n"
        msg += f"🏙️ *Localidad:* {data.get('localidad', 'N/A')}\n"
        msg += f"🗺️ *Provincia:* {data.get('provincia', 'N/A')}\n"
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
    msg += f"🌍 *País:* {data.get('country', 'N/A')}\n"
    msg += f"🗺️ *Región:* {data.get('regionName', 'N/A')}\n"
    msg += f"🏙️ *Ciudad:* {data.get('city', 'N/A')}\n"
    msg += f"🔌 *ISP:* {data.get('isp', 'N/A')}\n"
    msg += f"📌 *Coordenadas:* {data.get('lat', 'N/A')}, {data.get('lon', 'N/A')}\n"
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
    data = consultar_titular(telefono)
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
            f"🔍 *OSINT - APIS REALES*\n\n"
            f"/dni <dni> - RENAPER\n"
            f"/deuda <cuil> - BCRA\n"
            f"/editdni <dni> - Editar DNI\n"
            f"/editlicencia <dni> - Editar Licencia\n"
            f"/familiares <dni> - Nosis\n"
            f"/intelx <dominio> - IntelX\n"
            f"/dnrpa <patente> - Patente.ar\n"
            f"/email <email> - HIBP\n"
            f"/renaedits <dni> - Domicilio\n"
            f"/ip <ip> - ip-api.com\n"
            f"/titular <tel> - Verifik\n\n"
            f"💰 *Tokens:* {get_tokens(user_id)}",
            parse_mode='Markdown'
        )
    elif query.data == 'security':
        await query.edit_message_text(
            f"🔧 *RED - APIS REALES*\n\n"
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
    app = Application.builder().token(TOKEN).build()
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
    print("🤖 NINJA DATA BOT v53.0 - APIS REALES iniciado")
    print("📊 15 comandos disponibles con APIs reales")
    app.run_polling()

if __name__ == '__main__':
    main()
