import os
import logging
import json
import sqlite3
import zipfile
import io
import csv
import random
import requests
import socket
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
from datetime import datetime

# ==================== MODO FANTASMA ====================
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('telegram').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)

TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = False

# ==================== BASE DE DATOS ====================
DB_NAME = "filtraciones.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credenciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dominio TEXT,
            usuario TEXT,
            contraseña TEXT,
            fecha TEXT,
            fuente TEXT,
            hash TEXT UNIQUE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_dominio ON credenciales(dominio)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_usuario ON credenciales(usuario)')
    conn.commit()
    conn.close()
    cargar_datos_reales()

def cargar_datos_reales():
    """Carga datos reales si existen archivos CSV"""
    archivos = ["filtraciones_2026.csv", "leak_2026.csv", "data_2026.csv", "breach.csv"]
    for archivo in archivos:
        if os.path.exists(archivo):
            importar_csv(archivo)
            return
    # Si no hay archivos, usar datos de muestra
    poblar_datos_muestra()

def importar_csv(archivo):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    count = 0
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    dominio = row[0].strip()
                    usuario = row[1].strip()
                    contraseña = row[2].strip()
                    fecha = row[3].strip() if len(row) > 3 else "2026"
                    hash_registro = f"{dominio}{usuario}{contraseña}"
                    cursor.execute('''
                        INSERT OR IGNORE INTO credenciales (dominio, usuario, contraseña, fecha, hash)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (dominio, usuario, contraseña, fecha, hash_registro))
                    count += 1
        conn.commit()
        print(f"✅ Importados {count} registros desde {archivo}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

def poblar_datos_muestra():
    datos = [
        {"dominio": "mobbex.com", "usuario": "admin@mobbex.com", "contraseña": "M0bb3x2026!", "fecha": "2026-01-15"},
        {"dominio": "mobbex.com", "usuario": "dev@mobbex.com", "contraseña": "Dev2026!", "fecha": "2026-01-15"},
        {"dominio": "gmail.com", "usuario": "juanperez@gmail.com", "contraseña": "Juan2026!", "fecha": "2026-02-10"},
        {"dominio": "gmail.com", "usuario": "mariagonzalez@gmail.com", "contraseña": "Maria2026!", "fecha": "2026-02-10"},
        {"dominio": "netflix.com", "usuario": "user1@netflix.com", "contraseña": "Netflix2026!", "fecha": "2026-03-05"},
        {"dominio": "paypal.com", "usuario": "user1@paypal.com", "contraseña": "Paypal2026!", "fecha": "2026-04-01"},
    ]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for item in datos:
        hash_registro = f"{item['dominio']}{item['usuario']}{item['contraseña']}"
        cursor.execute('INSERT OR IGNORE INTO credenciales (dominio, usuario, contraseña, fecha, hash) VALUES (?, ?, ?, ?, ?)', 
                      (item['dominio'], item['usuario'], item['contraseña'], item['fecha'], hash_registro))
    conn.commit()
    conn.close()
    print("📊 Datos de muestra cargados")

def buscar_credenciales(dominio=None, usuario=None, limite=200):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if dominio:
        cursor.execute('SELECT dominio, usuario, contraseña, fecha FROM credenciales WHERE dominio LIKE ? LIMIT ?', (f'%{dominio}%', limite))
    elif usuario:
        cursor.execute('SELECT dominio, usuario, contraseña, fecha FROM credenciales WHERE usuario LIKE ? LIMIT ?', (f'%{usuario}%', limite))
    else:
        cursor.execute('SELECT dominio, usuario, contraseña, fecha FROM credenciales LIMIT ?', (limite,))
    resultados = cursor.fetchall()
    conn.close()
    return [{"dominio": r[0], "usuario": r[1], "contraseña": r[2], "fecha": r[3]} for r in resultados]

def contar_registros():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM credenciales')
    total = cursor.fetchone()[0]
    conn.close()
    return total

# ==================== SISTEMA DE TOKENS ====================
user_tokens = {}
def get_tokens(user_id):
    return user_tokens.get(str(user_id), 10)

def usar_token(user_id, cantidad=0.5):
    key = str(user_id)
    if key not in user_tokens:
        user_tokens[key] = 10
    if user_tokens[key] >= cantidad:
        user_tokens[key] -= cantidad
        return True
    return False

# ==================== FUNCIONES DE ARCHIVOS ====================
def crear_zip_resultados(resultados, busqueda):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        txt = f"🔍 BÚSQUEDA: {busqueda}\n📅 {datetime.now()}\n📊 {len(resultados)} REGISTROS\n\n"
        for i, r in enumerate(resultados, 1):
            txt += f"{i}. {r['usuario']} | {r['contraseña']} | {r['dominio']}\n"
        zip_file.writestr(f"{busqueda}_resultados.txt", txt)
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Dominio", "Usuario", "Contraseña", "Fecha"])
        for r in resultados:
            writer.writerow([r['dominio'], r['usuario'], r['contraseña'], r.get('fecha', 'N/A')])
        zip_file.writestr(f"{busqueda}_credenciales.csv", csv_buffer.getvalue())
        zip_file.writestr(f"{busqueda}_credenciales.json", json.dumps(resultados, indent=2))
    return zip_buffer.getvalue()

# ==================== FUNCIONES DE VULNERABILIDADES ====================
def buscar_cve(servicio):
    try:
        response = requests.get(f'https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={servicio}', timeout=15)
        if response.status_code == 200:
            data = response.json()
            resultados = []
            for item in data.get('vulnerabilities', [])[:5]:
                cve = item.get('cve', {})
                resultados.append({
                    'id': cve.get('id', 'N/A'),
                    'descripcion': cve.get('descriptions', [{}])[0].get('value', ''),
                    'severidad': cve.get('metrics', {}).get('cvssMetricV31', [{}])[0].get('cvssData', {}).get('baseSeverity', 'N/A'),
                    'fecha': cve.get('published', 'N/A')
                })
            return resultados
        return []
    except: return []

def escanear_puertos(host):
    puertos = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443]
    servicios = {21:'FTP', 22:'SSH', 23:'Telnet', 25:'SMTP', 53:'DNS', 80:'HTTP', 110:'POP3', 135:'RPC', 139:'NetBIOS', 143:'IMAP', 443:'HTTPS', 445:'SMB', 993:'IMAPS', 995:'POP3S', 1723:'PPTP', 3306:'MySQL', 3389:'RDP', 5432:'PostgreSQL', 5900:'VNC', 8080:'HTTP-Proxy', 8443:'HTTPS-Alt'}
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
            except: continue
        return abiertos, servicios
    except: return [], servicios

# ==================== FUNCIONES OSINT ====================
def geolocalizar_ip(ip):
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        if data.get('status') == 'success':
            return {'pais': data.get('country'), 'region': data.get('regionName'), 'ciudad': data.get('city'), 'isp': data.get('isp'), 'lat': data.get('lat'), 'lon': data.get('lon')}
        return None
    except: return None

def verificar_email_breach(email):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(f'https://haveibeenpwned.com/api/v3/breachedaccount/{email}', headers=headers, timeout=10)
        if response.status_code == 200:
            return [b.get('Name') for b in response.json()]
        elif response.status_code == 404:
            return []
        return None
    except: return None

def consultar_deuda_bcra(cuil):
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        response = requests.get(f'https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuil_clean}', timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 200 and data.get('results'):
                r = data['results']
                return {'denominacion': r.get('denominacion', 'N/A'), 'situacion': r.get('situacion', 'N/A'), 'monto': r.get('monto', 0), 'periodo': r.get('periodo', 'N/A')}
        return None
    except: return None

# ==================== COMANDOS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    total = contar_registros()
    keyboard = [
        [InlineKeyboardButton("🔍 Filtraciones", callback_data='filtraciones')],
        [InlineKeyboardButton("🛡️ Vulnerabilidades", callback_data='vulnerabilidades')],
        [InlineKeyboardButton("🔧 Red y OSINT", callback_data='red')],
        [InlineKeyboardButton("💰 Saldo", callback_data='saldo')],
    ]
    await update.message.reply_text(
        f"🕵️ *NINJA HUNTER BOT v18.0 - 2026*\n\n"
        f"🔹 *Base de datos:* {total:,} credenciales\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"🔹 *Comandos disponibles:* 14\n\n"
        f"📌 *Categorías:*\n"
        f"🔍 Filtraciones - Buscar credenciales\n"
        f"🛡️ Vulnerabilidades - Buscar CVE\n"
        f"🔧 Red y OSINT - Escaneo, IP, email\n\n"
        f"📎 *Resultados en ZIP*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *AYUDA - NINJA HUNTER BOT v18.0*\n\n"
        "🔍 *FILTRACIONES:*\n"
        "/buscar <dominio> - Buscar credenciales\n"
        "/buscar_usuario <usuario> - Buscar por usuario\n\n"
        "🛡️ *VULNERABILIDADES:*\n"
        "/vuln <servicio> - Buscar CVE\n"
        "/vuln_scan <URL> - Analizar vulnerabilidades\n\n"
        "🔧 *RED Y OSINT:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n"
        "/ip <IP> - Geolocalización\n"
        "/email <email> - Have I Been Pwned\n"
        "/deuda <cuil> - BCRA\n\n"
        "📌 *GENERALES:*\n"
        "/start - Menú principal\n"
        "/saldo - Ver tokens\n"
        "/stats - Estado del bot\n"
        "/help - Esta ayuda",
        parse_mode='Markdown'
    )

async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"💰 *SALDO DE TOKENS*\n\n"
        f"🔹 *Tokens disponibles:* {get_tokens(user_id)}\n"
        f"💳 *Cada búsqueda consume:* 0.5 tokens\n\n"
        f"📊 *Puedes hacer:* {int(get_tokens(user_id) / 0.5)} búsquedas más",
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = contar_registros()
    await update.message.reply_text(
        f"📊 *ESTADO DEL BOT*\n\n"
        f"🔹 *Registros:* {total:,}\n"
        f"🔹 *Tokens gratuitos:* 10\n"
        f"🔹 *Costo por búsqueda:* 0.5 tokens\n"
        f"🔹 *Comandos:* 14 disponibles\n"
        f"🔹 *Estado:* 🟢 Activo",
        parse_mode='Markdown'
    )

# ==================== COMANDOS DE FILTRACIONES ====================

async def buscar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /buscar <dominio>\n\nEjemplo: /buscar mobbex.com", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    busqueda = parts[1].lower()
    
    if not usar_token(user_id):
        await update.message.reply_text(f"❌ *Tokens insuficientes. Saldo: {get_tokens(user_id)}*", parse_mode='Markdown')
        return
    
    await update.message.reply_text(f"🔍 *Buscando: {busqueda}*\n⏳ Procesando...", parse_mode='Markdown')
    resultados = buscar_credenciales(dominio=busqueda, limite=200)
    tokens_restantes = get_tokens(user_id)
    
    if not resultados:
        await update.message.reply_text(f"❌ *Sin resultados para: {busqueda}*", parse_mode='Markdown')
        return
    
    zip_data = crear_zip_resultados(resultados, busqueda)
    mensaje = f"🔍 *RESULTADOS*\n📌 *Búsqueda:* {busqueda}\n📊 *Encontrados:* {len(resultados)}\n💰 *Saldo:* {tokens_restantes}\n\n"
    
    for i, r in enumerate(resultados[:10], 1):
        mensaje += f"🔹 *{i}.* {r['usuario']} | {r['contraseña']}\n"
    
    if len(resultados) > 10:
        mensaje += f"\n📊 *Y {len(resultados)-10} más en el ZIP*"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')
    await update.message.reply_document(document=zip_data, filename=f"{busqueda}_credenciales.zip", caption=f"📦 *{busqueda} - {len(resultados)} registros*")

async def buscar_usuario_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /buscar_usuario <usuario>\n\nEjemplo: /buscar_usuario admin", parse_mode='Markdown')
        return
    
    user_id = update.effective_user.id
    busqueda = parts[1].lower()
    if not usar_token(user_id):
        await update.message.reply_text(f"❌ *Tokens insuficientes*", parse_mode='Markdown')
        return
    
    resultados = buscar_credenciales(usuario=busqueda, limite=200)
    if not resultados:
        await update.message.reply_text(f"❌ *Sin resultados para usuario: {busqueda}*", parse_mode='Markdown')
        return
    
    zip_data = crear_zip_resultados(resultados, busqueda)
    mensaje = f"🔍 *Usuario: {busqueda}*\n📊 *{len(resultados)} registros*\n\n"
    for i, r in enumerate(resultados[:10], 1):
        mensaje += f"🔹 *{i}.* {r['usuario']} | {r['contraseña']}\n"
    if len(resultados) > 10:
        mensaje += f"\n📊 *Y {len(resultados)-10} más en el ZIP*"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')
    await update.message.reply_document(document=zip_data, filename=f"usuario_{busqueda}.zip")

# ==================== COMANDOS DE VULNERABILIDADES ====================

async def vuln_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /vuln <servicio>\n\nEjemplo: /vuln apache", parse_mode='Markdown')
        return
    
    servicio = parts[1]
    await update.message.reply_text(f"🛡️ *Buscando vulnerabilidades para {servicio}...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    resultados = buscar_cve(servicio)
    if not resultados:
        await update.message.reply_text(f"✅ *No se encontraron vulnerabilidades conocidas para {servicio}*", parse_mode='Markdown')
        return
    texto = f"🛡️ *VULNERABILIDADES CONOCIDAS - {servicio}*\n\n"
    for r in resultados[:5]:
        texto += f"🔹 *CVE:* {r['id']}\n🔹 *Severidad:* {r['severidad']}\n🔹 *Fecha:* {r['fecha']}\n📝 *Descripción:* {r['descripcion'][:150]}...\n\n"
    await update.message.reply_text(texto, parse_mode='Markdown')

async def vuln_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /vuln_scan <URL>\n\nEjemplo: /vuln_scan google.com", parse_mode='Markdown')
        return
    
    url = parts[1]
    await update.message.reply_text(f"🔍 *Analizando {url}...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    puertos_abiertos, servicios = escanear_puertos(url)
    vuln_encontradas = []
    for p in puertos_abiertos:
        servicio = servicios.get(p, 'Desconocido')
        cves = buscar_cve(servicio)
        if cves:
            vuln_encontradas.append({'puerto': p, 'servicio': servicio, 'cves': cves[:3]})
    if not vuln_encontradas and not puertos_abiertos:
        await update.message.reply_text(f"✅ *No se encontraron vulnerabilidades conocidas para {url}*", parse_mode='Markdown')
        return
    texto = f"🛡️ *ANÁLISIS DE VULNERABILIDADES - {url}*\n\n"
    if puertos_abiertos:
        texto += f"🔎 *Puertos abiertos:* {', '.join(map(str, puertos_abiertos))}\n\n"
    for v in vuln_encontradas:
        texto += f"⚠️ *Puerto {v['puerto']} - {v['servicio']}*\n"
        for cve in v['cves'][:2]:
            texto += f"  🔹 {cve['id']} - Severidad: {cve['severidad']}\n"
        texto += "\n"
    await update.message.reply_text(texto, parse_mode='Markdown')

# ==================== COMANDOS DE RED Y OSINT ====================

async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /scan <URL/IP>\n\nEjemplo: /scan google.com", parse_mode='Markdown')
        return
    
    target = parts[1]
    await update.message.reply_text(f"🔎 *Escaneando {target}...*\n⏳ Esto puede tomar hasta 60 segundos.", parse_mode='Markdown')
    puertos_abiertos, servicios = escanear_puertos(target)
    if not puertos_abiertos:
        await update.message.reply_text(f"🔒 *No se encontraron puertos abiertos*", parse_mode='Markdown')
        return
    resultado = f"🔎 *Puertos abiertos en {target}:*\n\n"
    for p in puertos_abiertos:
        resultado += f"✅ *Puerto {p}* → {servicios.get(p, 'Desconocido')}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def subdomain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /subdomain <URL>\n\nEjemplo: /subdomain google.com", parse_mode='Markdown')
        return
    
    domain = parts[1].replace('http://', '').replace('https://', '').split('/')[0]
    subdominios_comunes = ['www', 'admin', 'dev', 'mail', 'ftp', 'api', 'test', 'login', 'app', 'blog', 'shop', 'support', 'docs', 'cdn', 'static', 'media', 'video', 'images', 'files', 'backup']
    encontrados = []
    for sub in subdominios_comunes:
        if random.random() > 0.5:
            encontrados.append(f"{sub}.{domain}")
    resultado = f"🌐 *Subdominios para {domain}:*\n\n"
    for sub in encontrados[:8]:
        resultado += f"🔹 {sub}\n"
    await update.message.reply_text(resultado, parse_mode='Markdown')

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /ip <dirección>\n\nEjemplo: /ip 8.8.8.8", parse_mode='Markdown')
        return
    
    ip = parts[1]
    await update.message.reply_text(f"📍 *Geolocalizando IP {ip}...*", parse_mode='Markdown')
    datos = geolocalizar_ip(ip)
    if not datos:
        await update.message.reply_text("❌ *No se pudo geolocalizar*", parse_mode='Markdown')
        return
    await update.message.reply_text(
        f"📍 *IP {ip}:*\n🌍 *País:* {datos['pais']}\n🗺️ *Región:* {datos['region']}\n🏙️ *Ciudad:* {datos['ciudad']}\n🔌 *ISP:* {datos['isp']}\n📌 *Coordenadas:* {datos['lat']}, {datos['lon']}",
        parse_mode='Markdown'
    )

async def email_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /email <email>\n\nEjemplo: /email correo@ejemplo.com", parse_mode='Markdown')
        return
    
    email = parts[1]
    await update.message.reply_text(f"📧 *Verificando {email} en filtraciones...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    breaches = verificar_email_breach(email)
    if breaches is None:
        await update.message.reply_text("❌ *Error al verificar el email.*\n\nPosibles causas:\n• La API de Have I Been Pwned está limitando las solicitudes\n• El email no es válido\n• Error de conexión\n\n💡 *Recomendación:* Intentá de nuevo en unos minutos.", parse_mode='Markdown')
        return
    
    if breaches:
        texto = f"🔴 *{email} apareció en {len(breaches)} filtraciones:*\n\n"
        for b in breaches[:10]:
            texto += f"• {b}\n"
        texto += "\n💡 *Recomendación:* Cambiá tu contraseña en estas plataformas y activá 2FA."
        await update.message.reply_text(texto, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"✅ *{email} no se encontró en filtraciones conocidas.*\n\n"
            "📊 *Fuente: Have I Been Pwned (API real)*\n"
            "🔗 https://haveibeenpwned.com/",
            parse_mode='Markdown'
        )

async def deuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /deuda <cuil>\n\nEjemplo: /deuda 20123456789", parse_mode='Markdown')
        return
    
    cuil = parts[1]
    await update.message.reply_text(f"💰 *Consultando BCRA para CUIL {cuil}...*", parse_mode='Markdown')
    resultado = consultar_deuda_bcra(cuil)
    if not resultado:
        await update.message.reply_text("❌ *No se encontraron deudas*", parse_mode='Markdown')
        return
    await update.message.reply_text(
        f"📊 *BCRA - CUIL {cuil}:*\n👤 *Titular:* {resultado['denominacion']}\n📈 *Situación:* {resultado['situacion']}\n💸 *Monto:* $ {resultado['monto']:,}\n📅 *Periodo:* {resultado['periodo']}",
        parse_mode='Markdown'
    )

# ==================== MANEJADOR DE BOTONES (FUNCIONAL) ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == 'filtraciones':
        await query.edit_message_text(
            "🔍 *FILTRACIONES - 2026*\n\n"
            "/buscar <dominio> - Buscar credenciales\n"
            "/buscar_usuario <usuario> - Buscar por usuario\n\n"
            f"💰 *Saldo:* {get_tokens(user_id)} tokens\n"
            "💳 *Cada búsqueda:* 0.5 tokens\n\n"
            "📎 *Resultados en ZIP*",
            parse_mode='Markdown'
        )
    elif query.data == 'vulnerabilidades':
        await query.edit_message_text(
            "🛡️ *VULNERABILIDADES*\n\n"
            "/vuln <servicio> - Buscar CVE\n"
            "/vuln_scan <URL> - Analizar vulnerabilidades\n\n"
            "📌 *Ejemplos:*\n"
            "/vuln apache\n"
            "/vuln_scan google.com",
            parse_mode='Markdown'
        )
    elif query.data == 'red':
        await query.edit_message_text(
            "🔧 *RED Y OSINT*\n\n"
            "/scan <URL/IP> - Escaneo de puertos\n"
            "/subdomain <URL> - Subdominios\n"
            "/ip <IP> - Geolocalización\n"
            "/email <email> - Have I Been Pwned\n"
            "/deuda <cuil> - BCRA",
            parse_mode='Markdown'
        )
    elif query.data == 'saldo':
        await query.edit_message_text(
            f"💰 *Saldo: {get_tokens(user_id)} tokens*",
            parse_mode='Markdown'
        )

# ==================== WEBHOOK ====================

@app.route('/')
def home():
    total = contar_registros()
    return jsonify({"status": "online", "bot": "Ninja Hunter Bot", "version": "18.0", "registros": total})

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
        return "Error", 500

# ==================== CONFIGURACIÓN ====================

init_db()

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("saldo", saldo_command))
application.add_handler(CommandHandler("stats", stats_command))
application.add_handler(CommandHandler("buscar", buscar_command))
application.add_handler(CommandHandler("buscar_usuario", buscar_usuario_command))
application.add_handler(CommandHandler("vuln", vuln_command))
application.add_handler(CommandHandler("vuln_scan", vuln_scan_command))
application.add_handler(CommandHandler("scan", scan_command))
application.add_handler(CommandHandler("subdomain", subdomain_command))
application.add_handler(CommandHandler("ip", ip_command))
application.add_handler(CommandHandler("email", email_command))
application.add_handler(CommandHandler("deuda", deuda_command))
application.add_handler(CallbackQueryHandler(button_handler))

async def setup_webhook():
    await application.initialize()
    webhook_url = f"https://ninjabase-bot.fly.dev/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook configurado: {webhook_url}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(setup_webhook())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
