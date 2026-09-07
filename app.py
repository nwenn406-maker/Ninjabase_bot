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
import time
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

# ==================== CREDENCIALES DE APIS ====================
RENAPER_PKG1 = os.getenv('RENAPER_PKG1', '')
RENAPER_PKG2 = os.getenv('RENAPER_PKG2', '')
RENAPER_PKG3 = os.getenv('RENAPER_PKG3', '')
PATENTE_API_KEY = os.getenv('PATENTE_API_KEY', '')
NOSIS_API_KEY = os.getenv('NOSIS_API_KEY', '')
HIBP_API_KEY = os.getenv('HIBP_API_KEY', '')
VERIFIK_TOKEN = os.getenv('VERIFIK_TOKEN', '')
DEHASHED_API_KEY = os.getenv('DEHASHED_API_KEY', '')
LEAKCHECK_API_KEY = os.getenv('LEAKCHECK_API_KEY', '')
INTELX_API_KEY = os.getenv('INTELX_API_KEY', '')

DB_NAME = "filtraciones.db"

logging.basicConfig(level=logging.INFO)

# ==================== BASE DE DATOS ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tablas de filtraciones
    c.execute('''CREATE TABLE IF NOT EXISTS renaper (
        dni TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
        domicilio TEXT, localidad TEXT, provincia TEXT, cuil TEXT, telefono TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dnrpa (
        patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, año TEXT,
        titular TEXT, dni_titular TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS bcra (
        cuil TEXT PRIMARY KEY, dni TEXT, nombre TEXT, fecha_nac TEXT,
        situacion TEXT, monto_deuda REAL, entidades TEXT, score INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS telefonos (
        numero TEXT PRIMARY KEY, titular TEXT, dni_titular TEXT,
        compania TEXT, provincia TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
        email TEXT PRIMARY KEY, password TEXT, dominio TEXT, fuente TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS credenciales_url (
        dominio TEXT, usuario TEXT, contraseña TEXT, fuente TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS intelx_cache (
        dominio TEXT, archivos TEXT, fecha TEXT)''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_bcra ON bcra(cuil)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_credenciales ON credenciales_url(dominio)')
    
    conn.commit()
    conn.close()
    
    # Cargar datos de ejemplo
    cargar_datos_ejemplo()

def cargar_datos_ejemplo():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # RENAPER
    datos_renaper = [
        ('39268021', 'Juan', 'Pérez', '15/03/1985', 'Av. Corrientes 1234', 'CABA', 'Buenos Aires', '20-39268021-4', '1139328345'),
        ('12345678', 'María', 'González', '22/07/1990', 'Calle Santa Fe 567', 'CABA', 'Buenos Aires', '27-12345678-3', '1198765432'),
        ('87654321', 'Carlos', 'Rodríguez', '10/11/1982', 'Av. 9 de Julio 890', 'Córdoba', 'Córdoba', '20-87654321-4', '1165432109'),
    ]
    for d in datos_renaper:
        c.execute('INSERT OR IGNORE INTO renaper VALUES (?,?,?,?,?,?,?,?,?)', d)
    
    # DNRPA
    datos_dnrpa = [
        ('AB123CD', 'Toyota', 'Corolla', '2020', 'Juan Pérez', '39268021'),
        ('EF456GH', 'Volkswagen', 'Golf', '2019', 'María González', '12345678'),
        ('IJ789KL', 'Ford', 'Focus', '2021', 'Carlos Rodríguez', '87654321'),
    ]
    for d in datos_dnrpa:
        c.execute('INSERT OR IGNORE INTO dnrpa VALUES (?,?,?,?,?,?)', d)
    
    # Teléfonos
    datos_telefonos = [
        ('1139328345', 'Juan Pérez', '39268021', 'Movistar', 'CABA'),
        ('1198765432', 'María González', '12345678', 'Claro', 'Buenos Aires'),
        ('1165432109', 'Carlos Rodríguez', '87654321', 'Personal', 'Córdoba'),
    ]
    for d in datos_telefonos:
        c.execute('INSERT OR IGNORE INTO telefonos VALUES (?,?,?,?,?)', d)
    
    # Emails
    datos_emails = [
        ('nwenn406@gmail.com', 'Password123!', 'gmail.com', 'Filtración Gmail 2023'),
        ('admin@mobbex.com', 'M0bb3x2024', 'mobbex.com', 'Filtración Mobbex 2024'),
        ('dev@rebill.com', 'R3b1ll2024', 'rebill.com', 'Filtración Rebill 2024'),
        ('admin@monei.com', 'M0n3i2024', 'monei.com', 'Filtración Monei 2024'),
        ('user1@netflix.com', 'Netflix2024!', 'netflix.com', 'Filtración Netflix 2024'),
        ('user1@paypal.com', 'Paypal2024!', 'paypal.com', 'Filtración PayPal 2024'),
    ]
    for d in datos_emails:
        c.execute('INSERT OR IGNORE INTO emails VALUES (?,?,?,?)', d)
    
    # Credenciales URL
    datos_credenciales = [
        ('mobbex.com', 'admin@mobbex.com', 'M0bb3x2024', 'Filtración Mobbex 2024'),
        ('rebill.com', 'dev@rebill.com', 'R3b1ll2024', 'Filtración Rebill 2024'),
        ('monei.com', 'admin@monei.com', 'M0n3i2024', 'Filtración Monei 2024'),
        ('netflix.com', 'user1@netflix.com', 'Netflix2024!', 'Filtración Netflix 2024'),
        ('paypal.com', 'user1@paypal.com', 'Paypal2024!', 'Filtración PayPal 2024'),
        ('facebook.com', 'user1@facebook.com', 'Fb2024!', 'Filtración Facebook 2024'),
        ('gmail.com', 'nwenn406@gmail.com', 'Password123!', 'Filtración Gmail 2023'),
    ]
    for d in datos_credenciales:
        c.execute('INSERT OR IGNORE INTO credenciales_url VALUES (?,?,?,?)', d)
    
    conn.commit()
    conn.close()
    print("✅ Datos de ejemplo cargados")

# ==================== FUNCIONES DE CONSULTA ====================

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

def consultar_deuda(cuil):
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        if len(cuil_clean) != 11:
            return None
        response = requests.get(
            f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                return data['results']
        return None
    except requests.exceptions.Timeout:
        return 'timeout'
    except:
        return None

def consultar_patente(patente):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'marca': r[1], 'modelo': r[2], 'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
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

# ==================== FUNCIÓN /url ====================

async def url_command(update, context):
    """Comando /url - Busca credenciales en filtraciones reales"""
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso:* `/url <dominio>`\n\n"
            "Ejemplo: `/url mobbex.com`\n"
            "Ejemplo: `/url gmail.com`\n\n"
            "📌 *Busca credenciales reales en filtraciones.*",
            parse_mode='Markdown'
        )
        return

    user_id = update.effective_user.id
    dominio = context.args[0].replace('http://', '').replace('https://', '').split('/')[0].split('?')[0]

    if not usar_token(user_id):
        await update.message.reply_text("❌ Tokens insuficientes.")
        return

    await update.message.reply_text(f"🔍 *Analizando {dominio}...*\n⏳ Consultando bases de datos...", parse_mode='Markdown')

    credenciales = []

    # ==================== 1. BASE DE DATOS LOCAL ====================
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT usuario, contraseña, fuente FROM credenciales_url WHERE dominio = ?', (dominio,))
        for r in c.fetchall():
            credenciales.append({'usuario': r[0], 'contraseña': r[1], 'fuente': r[2]})
        c.execute('SELECT email, password, fuente FROM emails WHERE dominio = ?', (dominio,))
        for r in c.fetchall():
            credenciales.append({'usuario': r[0], 'contraseña': r[1], 'fuente': r[2]})
        conn.close()
    except: pass

    # ==================== 2. HAVE I BEEN PWNED ====================
    if HIBP_API_KEY:
        try:
            headers = {'hibp-api-key': HIBP_API_KEY, 'User-Agent': 'NINJA-DATA-BOT/1.0'}
            response = requests.get(f'https://haveibeenpwned.com/api/v3/breacheddomain/{dominio}', headers=headers, timeout=15)
            if response.status_code == 200:
                for breach in response.json():
                    credenciales.append({
                        'usuario': f"*{breach.get('Name', 'N/A')}*",
                        'contraseña': '**Filtración confirmada**',
                        'fuente': f"HIBP - {breach.get('BreachDate', 'N/A')} - {breach.get('PwnCount', 0):,} cuentas"
                    })
        except: pass

    # ==================== 3. EMAILS COMUNES ====================
    if HIBP_API_KEY:
        emails_comunes = [
            f"admin@{dominio}", f"info@{dominio}", f"contact@{dominio}",
            f"support@{dominio}", f"dev@{dominio}", f"webmaster@{dominio}",
            f"security@{dominio}", f"postmaster@{dominio}"
        ]
        headers = {'hibp-api-key': HIBP_API_KEY, 'User-Agent': 'NINJA-DATA-BOT/1.0'}
        for email in emails_comunes:
            try:
                response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', headers=headers, timeout=10)
                if response.status_code == 200:
                    for breach in response.json():
                        credenciales.append({
                            'usuario': email,
                            'contraseña': '**Comprometida**',
                            'fuente': f"HIBP - {breach.get('Name', 'N/A')}"
                        })
            except: continue

    # ==================== 4. DEHASHED ====================
    if DEHASHED_API_KEY:
        try:
            response = requests.get(
                f'https://api.dehashed.com/search?query=domain:{dominio}',
                headers={'Authorization': f'Bearer {DEHASHED_API_KEY}'},
                timeout=15
            )
            if response.status_code == 200:
                for entry in response.json().get('entries', []):
                    credenciales.append({
                        'usuario': entry.get('email', 'N/A'),
                        'contraseña': entry.get('password', '**Hash**'),
                        'fuente': f"Dehashed - {entry.get('breach', 'N/A')}"
                    })
        except: pass

    # ==================== 5. LEAKCHECK ====================
    if LEAKCHECK_API_KEY:
        try:
            response = requests.get(
                f'https://leak-check.net/api/v1/domain/{dominio}',
                headers={'api-key': LEAKCHECK_API_KEY},
                timeout=15
            )
            if response.status_code == 200:
                for entry in response.json().get('results', []):
                    credenciales.append({
                        'usuario': entry.get('email', 'N/A'),
                        'contraseña': entry.get('password', 'N/A'),
                        'fuente': f"LeakCheck - {entry.get('source', 'N/A')}"
                    })
        except: pass

    # ==================== FILTRAR DUPLICADOS ====================
    credenciales_unicas = []
    visto = set()
    for c in credenciales:
        key = c['usuario']
        if key not in visto:
            visto.add(key)
            credenciales_unicas.append(c)
    credenciales = credenciales_unicas

    # ==================== MOSTRAR RESULTADOS ====================
    if credenciales:
        msg = f"🔴 *CREDENCIALES ENCONTRADAS* - `{dominio}`\n\n"
        msg += f"📊 *Total encontradas:* {len(credenciales)}\n\n"
        
        for i, c in enumerate(credenciales[:20], 1):
            msg += f"👤 *{i}.* `{c['usuario']}`\n"
            msg += f"🔑 `{c['contraseña']}`\n"
            msg += f"📌 {c.get('fuente', 'N/A')}\n\n"
        
        if len(credenciales) > 20:
            msg += f"📊 *Y {len(credenciales)-20} más en el archivo ZIP*\n"
        
        msg += f"\n💳 *Tokens restantes:* {get_tokens(user_id)}"
        await update.message.reply_text(msg, parse_mode='Markdown')

        # ZIP
        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                txt = f"🔍 CREDENCIALES - {dominio}\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📊 Total: {len(credenciales)}\n\n"
                for i, c in enumerate(credenciales, 1):
                    txt += f"--- REGISTRO {i} ---\nUsuario: {c['usuario']}\nContraseña: {c['contraseña']}\nFuente: {c.get('fuente', 'N/A')}\n\n"
                zip_file.writestr(f"{dominio}_credenciales.txt", txt)
                
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["Usuario", "Contraseña", "Fuente"])
                for c in credenciales:
                    writer.writerow([c['usuario'], c['contraseña'], c.get('fuente', 'N/A')])
                zip_file.writestr(f"{dominio}_credenciales.csv", csv_buffer.getvalue())
                
                zip_file.writestr(f"{dominio}_credenciales.json", json.dumps(credenciales, indent=2))
            
            zip_buffer.seek(0)
            await update.message.reply_document(
                document=zip_buffer,
                filename=f"{dominio}_credenciales.zip",
                caption=f"📦 *{dominio} - {len(credenciales)} credenciales encontradas*"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ *Error al generar ZIP:* `{str(e)}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"✅ *No se encontraron credenciales para {dominio}.*",
            parse_mode='Markdown'
        )

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
        f"🕵️ *NINJA DATA BOT v56.0*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Comandos:*\n"
        f"/dni <dni> - RENAPER\n"
        f"/deuda <cuil> - BCRA\n"
        f"/dnrpa <patente> - DNRPA\n"
        f"/email <email> - Filtraciones\n"
        f"/ip <ip> - Geolocalización\n"
        f"/titular <tel> - Teléfono\n"
        f"/url <dominio> - Credenciales\n"
        f"/scan <URL/IP> - Puertos\n"
        f"/subdomain <URL> - Subdominios\n"
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
    msg += f"👤 *Nombre:* {data['nombre']} {data['apellido']}\n"
    msg += f"🆔 *DNI:* {data['dni']}\n"
    msg += f"🔑 *CUIL:* {data['cuil']}\n"
    msg += f"📅 *Nacimiento:* {data['fecha_nac']}\n"
    msg += f"📍 *Domicilio:* {data['domicilio']}\n"
    msg += f"📱 *Teléfono:* {data['telefono']}\n"
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
    mensaje = await update.message.reply_text(f"💰 *Consultando BCRA para CUIL {cuil}...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    data = consultar_deuda(cuil)
    
    if data == 'timeout':
        await mensaje.edit_text(
            f"⏰ *Tiempo de espera agotado.*\n\nLa API del BCRA no respondió a tiempo.\n📌 Intentá de nuevo en unos minutos.\n\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}",
            parse_mode='Markdown'
        )
        return
    
    if not data:
        await mensaje.edit_text(
            f"❌ *No se encontraron deudas para CUIL {cuil}.*\n\nPosibles causas:\n• CUIL inválido (debe tener 11 dígitos)\n• La persona no tiene deudas reportadas\n• Error en el servicio del BCRA\n\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}",
            parse_mode='Markdown'
        )
        return
    
    msg = f"📊 *BCRA - CUIL {cuil}:*\n\n"
    msg += f"👤 *Titular:* {data.get('denominacion', 'N/A')}\n"
    msg += f"📈 *Situación:* {data.get('situacion', 'N/A')}\n"
    msg += f"💸 *Monto:* $ {data.get('monto', 0):,}\n"
    msg += f"🏦 *Entidades:* {data.get('entidades', 'N/A')}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    
    await mensaje.edit_text(msg, parse_mode='Markdown')

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
    msg += f"🏭 *Marca:* {data['marca']}\n"
    msg += f"🚗 *Modelo:* {data['modelo']}\n"
    msg += f"📅 *Año:* {data['año']}\n"
    msg += f"👤 *Titular:* {data['titular']}\n"
    msg += f"🆔 *DNI Titular:* {data['dni_titular']}\n"
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
    if not data:
        await update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')
        return
    
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    msg += f"🔑 *Contraseña:* `{data['password']}`\n"
    msg += f"🌐 *Dominio:* {data['dominio']}\n"
    msg += f"📌 *Fuente:* {data['fuente']}\n"
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
            f"🔍 *OSINT*\n\n"
            f"/dni <dni>\n/deuda <cuil>\n/dnrpa <patente>\n/email <email>\n/ip <ip>\n/titular <tel>\n/url <dominio>\n\n"
            f"💰 *Tokens:* {get_tokens(user_id)}",
            parse_mode='Markdown'
        )
    elif query.data == 'security':
        await query.edit_message_text(
            f"🔧 *RED*\n\n"
            f"/scan <URL/IP>\n/subdomain <URL>\n\n"
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
    app.add_handler(CommandHandler("dnrpa", dnrpa_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("ip", ip_command))
    app.add_handler(CommandHandler("titular", titular_command))
    app.add_handler(CommandHandler("url", url_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("subdomain", subdomain_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 NINJA DATA BOT v56.0 iniciado")
    print("📊 Comandos: /dni, /deuda, /dnrpa, /email, /ip, /titular, /url, /scan, /subdomain, /saldo")
    app.run_polling()

if __name__ == '__main__':
    main()
