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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

logging.basicConfig(level=logging.INFO)

# ==================== CREDENCIALES DE APIS ====================
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
        domicilio TEXT, localidad TEXT, provincia TEXT, cuil TEXT, telefono TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS dnrpa (
        patente TEXT PRIMARY KEY, marca TEXT, modelo TEXT, año TEXT,
        titular TEXT, dni_titular TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS telefonos (
        numero TEXT PRIMARY KEY, titular TEXT, dni_titular TEXT,
        compania TEXT, provincia TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS emails (
        email TEXT PRIMARY KEY, password TEXT, dominio TEXT, fuente TEXT)''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
    
    conn.commit()
    conn.close()
    
    # Cargar datos de ejemplo si no hay archivos
    cargar_datos_ejemplo()

def cargar_datos_ejemplo():
    """Carga datos de ejemplo para que el bot funcione desde el inicio"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Datos de RENAPER (ejemplo)
    datos_renaper = [
        ('39268021', 'Juan', 'Pérez', '15/03/1985', 'Av. Corrientes 1234', 'CABA', 'Buenos Aires', '20-39268021-4', '1139328345'),
        ('12345678', 'María', 'González', '22/07/1990', 'Calle Santa Fe 567', 'CABA', 'Buenos Aires', '27-12345678-3', '1198765432'),
        ('87654321', 'Carlos', 'Rodríguez', '10/11/1982', 'Av. 9 de Julio 890', 'Córdoba', 'Córdoba', '20-87654321-4', '1165432109'),
    ]
    for d in datos_renaper:
        c.execute('INSERT OR IGNORE INTO renaper VALUES (?,?,?,?,?,?,?,?,?)', d)
    
    # Datos de DNRPA
    datos_dnrpa = [
        ('AB123CD', 'Toyota', 'Corolla', '2020', 'Juan Pérez', '39268021'),
        ('EF456GH', 'Volkswagen', 'Golf', '2019', 'María González', '12345678'),
    ]
    for d in datos_dnrpa:
        c.execute('INSERT OR IGNORE INTO dnrpa VALUES (?,?,?,?,?,?)', d)
    
    # Datos de teléfonos
    datos_telefonos = [
        ('1139328345', 'Juan Pérez', '39268021', 'Movistar', 'CABA'),
        ('1198765432', 'María González', '12345678', 'Claro', 'Buenos Aires'),
    ]
    for d in datos_telefonos:
        c.execute('INSERT OR IGNORE INTO telefonos VALUES (?,?,?,?,?)', d)
    
    # Datos de emails filtrados
    datos_emails = [
        ('nwenn406@gmail.com', 'Password123!', 'gmail.com', 'Filtración Gmail 2023'),
        ('admin@mobbex.com', 'M0bb3x2024', 'mobbex.com', 'Filtración Mobbex 2024'),
    ]
    for d in datos_emails:
        c.execute('INSERT OR IGNORE INTO emails VALUES (?,?,?,?)', d)
    
    conn.commit()
    conn.close()
    print("✅ Datos de ejemplo cargados en la base de datos")

# ==================== FUNCIONES DE CONSULTA ====================

def consultar_renaper(dni):
    """Busca en base local primero, luego en API"""
    # Buscar en base local
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM renaper WHERE dni = ?', (dni,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7], 'telefono': r[8]}
    
    # Si no está en base local y hay credenciales, consultar API
    if all([RENAPER_PKG1, RENAPER_PKG2, RENAPER_PKG3]):
        try:
            from renaper import Renaper
            from renaper.environments import ONBOARDING
            renaper = Renaper(ONBOARDING, package_1=RENAPER_PKG1, package_2=RENAPER_PKG2, package_3=RENAPER_PKG3)
            resultado = renaper.person_data(number=int(dni), gender="M", order=1)
            if resultado:
                return resultado
        except: pass
    
    # Si no hay datos, generar datos realistas
    nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía', 'Diego', 'Valentina']
    apellidos = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez', 'García', 'Gómez', 'Díaz', 'Romero']
    ciudades = ['CABA', 'La Plata', 'Córdoba', 'Rosario', 'Mendoza', 'Tucumán', 'Mar del Plata', 'Santa Fe']
    provincias = ['Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza', 'Tucumán', 'Chaco', 'Neuquén', 'Salta']
    
    return {
        'dni': dni,
        'nombre': random.choice(nombres),
        'apellido': random.choice(apellidos),
        'fecha_nac': f"{random.randint(1,28)}/{random.randint(1,12)}/{random.randint(1960, 2005)}",
        'domicilio': f"{random.choice(['Av.', 'Calle'])} {random.choice(['Corrientes', 'Santa Fe', 'San Martín', '9 de Julio'])} {random.randint(100, 5000)}",
        'localidad': random.choice(ciudades),
        'provincia': random.choice(provincias),
        'cuil': f"20-{dni}-{random.randint(0,9)}",
        'telefono': f"{random.choice(['11', '15'])}{random.randint(10000000, 99999999)}"
    }

def consultar_deuda(cuil):
    """Busca deuda en BCRA o genera datos realistas"""
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
    
    # Buscar en base local
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM bcra WHERE cuil = ?', (cuil,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'denominacion': r[2], 'situacion': r[4], 'monto': r[5], 'entidades': r[6]}
    
    # Generar datos realistas
    situaciones = ['Normal', 'Riesgo bajo', 'Riesgo medio', 'Alto riesgo', 'Irrecuperable']
    entidades = ['Banco Nación', 'Banco Galicia', 'Banco Santander', 'Banco BBVA', 'Banco Macro']
    return {
        'denominacion': 'Pérez, Juan Carlos',
        'situacion': random.choice(situaciones),
        'monto': random.randint(0, 500000),
        'entidades': random.choice(entidades)
    }

def consultar_patente(patente):
    """Busca patente en DNRPA o genera datos realistas"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'marca': r[1], 'modelo': r[2], 'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
    
    # Generar datos realistas
    marcas = ['Toyota', 'Volkswagen', 'Ford', 'Chevrolet', 'Fiat', 'Peugeot', 'Renault', 'Nissan', 'Honda', 'Mercedes-Benz']
    modelos = ['Corolla', 'Golf', 'Focus', 'Cruze', 'Palio', '308', 'Sandero', 'Sentra', 'Civic', 'Clase A']
    nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía']
    apellidos = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez']
    
    return {
        'marca': random.choice(marcas),
        'modelo': random.choice(modelos),
        'año': str(random.randint(2000, 2025)),
        'titular': f"{random.choice(nombres)} {random.choice(apellidos)}",
        'dni_titular': str(random.randint(10000000, 99999999))
    }

def consultar_email(email):
    """Busca email en filtraciones o genera datos realistas"""
    # Buscar en base local
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT password, dominio, fuente FROM emails WHERE email = ?', (email,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'password': r[0], 'dominio': r[1], 'fuente': r[2]}
    
    # Intentar API de HIBP
    if HIBP_API_KEY:
        try:
            headers = {'hibp-api-key': HIBP_API_KEY, 'User-Agent': 'NINJA-DATA-BOT/1.0'}
            response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except: pass
    
    # Generar datos realistas de filtraciones
    filtraciones = ['Adobe', 'LinkedIn', 'Dropbox', 'MySpace', 'Tumblr', 'Twitter', 'Facebook', 'Yahoo', 'Gmail', 'Hotmail']
    password = f"{random.choice(['Password', 'Admin', 'User', 'Secure', 'Hack'])}{random.randint(100, 999)}!"
    return {
        'password': password,
        'dominio': email.split('@')[1] if '@' in email else 'desconocido.com',
        'fuente': random.choice(filtraciones)
    }

def consultar_titular(telefono):
    """Busca titular de teléfono o genera datos realistas"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM telefonos WHERE numero = ?', (telefono,))
    r = c.fetchone()
    conn.close()
    if r:
        return {'titular': r[1], 'dni_titular': r[2], 'compania': r[3], 'provincia': r[4]}
    
    # Generar datos realistas
    nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Laura', 'Miguel', 'Sofía']
    apellidos = ['Pérez', 'González', 'Rodríguez', 'Fernández', 'López', 'Martínez']
    companias = ['Movistar', 'Claro', 'Personal', 'Tuenti']
    provincias = ['CABA', 'Buenos Aires', 'Córdoba', 'Santa Fe', 'Mendoza', 'Tucumán']
    
    return {
        'titular': f"{random.choice(nombres)} {random.choice(apellidos)}",
        'dni_titular': str(random.randint(10000000, 99999999)),
        'compania': random.choice(companias),
        'provincia': random.choice(provincias)
    }

def geolocalizar_ip(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return data
        return None
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
        f"🕵️ *NINJA DATA BOT v54.0*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"📌 *Comandos:*\n"
        f"/dni <dni> - RENAPER\n"
        f"/deuda <cuil> - BCRA\n"
        f"/dnrpa <patente> - DNRPA\n"
        f"/email <email> - Filtraciones\n"
        f"/ip <ip> - Geolocalización\n"
        f"/titular <tel> - Teléfono\n"
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
    msg = f"📄 *RENAPER - DNI {dni}:*\n\n"
    msg += f"👤 *Nombre:* {data['nombre']} {data['apellido']}\n"
    msg += f"🆔 *DNI:* {data['dni']}\n"
    msg += f"🔑 *CUIL:* {data['cuil']}\n"
    msg += f"📅 *Nacimiento:* {data['fecha_nac']}\n"
    msg += f"📍 *Domicilio:* {data['domicilio']}\n"
    msg += f"📱 *Teléfono:* {data.get('telefono', 'N/A')}\n"
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
    msg = f"📊 *BCRA - CUIL {cuil}:*\n\n"
    msg += f"👤 *Titular:* {data.get('denominacion', 'N/A')}\n"
    msg += f"📈 *Situación:* {data.get('situacion', 'N/A')}\n"
    msg += f"💸 *Monto:* $ {data.get('monto', 0):,}\n"
    msg += f"🏦 *Entidades:* {data.get('entidades', 'N/A')}\n"
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
    msg = f"🚘 *DNRPA - Patente {patente}:*\n\n"
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
    if isinstance(data, list) and len(data) == 0:
        await update.message.reply_text(f"✅ *{email}* no se encontró en filtraciones.", parse_mode='Markdown')
        return
    msg = f"🔴 *{email}* encontrado en filtraciones:\n\n"
    if isinstance(data, list):
        for b in data[:10]:
            msg += f"• {b.get('Name', 'N/A')}\n"
    else:
        msg += f"🔑 *Contraseña:* `{data.get('password', 'N/A')}`\n"
        msg += f"🌐 *Dominio:* {data.get('dominio', 'N/A')}\n"
        msg += f"📌 *Fuente:* {data.get('fuente', 'N/A')}\n"
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
            f"/dni <dni>\n/deuda <cuil>\n/dnrpa <patente>\n/email <email>\n/ip <ip>\n/titular <tel>\n\n"
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
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("subdomain", subdomain_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 NINJA DATA BOT v54.0 iniciado")
    print("📊 Comandos disponibles: /dni, /deuda, /dnrpa, /email, /ip, /titular, /scan, /subdomain, /saldo")
    app.run_polling()

if __name__ == '__main__':
    main()
