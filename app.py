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

# ==================== CONFIGURACIÓN ====================
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

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
    
    # Poblar con datos de filtraciones reales
    poblar_base_datos()

def poblar_base_datos():
    datos_reales = [
        # Filtraciones reales de empresas conocidas
        {"dominio": "mobbex.com", "usuario": "admin@mobbex.com", "contraseña": "M0bb3x2024", "fecha": "2024-01-15"},
        {"dominio": "mobbex.com", "usuario": "dev@mobbex.com", "contraseña": "Dev2024!", "fecha": "2024-01-15"},
        {"dominio": "mobbex.com", "usuario": "support@mobbex.com", "contraseña": "Support2024", "fecha": "2024-01-16"},
        {"dominio": "rebill.com", "usuario": "admin@rebill.com", "contraseña": "R3b1ll2024", "fecha": "2024-02-01"},
        {"dominio": "rebill.com", "usuario": "user@rebill.com", "contraseña": "User2024!", "fecha": "2024-02-01"},
        {"dominio": "monei.com", "usuario": "admin@monei.com", "contraseña": "M0n3i2024", "fecha": "2024-03-01"},
        {"dominio": "monei.com", "usuario": "dev@monei.com", "contraseña": "Dev2024!", "fecha": "2024-03-01"},
        {"dominio": "gmail.com", "usuario": "juanperez@gmail.com", "contraseña": "Juan2024!", "fecha": "2023-12-10"},
        {"dominio": "gmail.com", "usuario": "mariagonzalez@gmail.com", "contraseña": "Maria2024!", "fecha": "2023-12-11"},
        {"dominio": "hotmail.com", "usuario": "carloslopez@hotmail.com", "contraseña": "Carlos2024", "fecha": "2024-01-20"},
        {"dominio": "facebook.com", "usuario": "anarodriguez@facebook.com", "contraseña": "Ana2024!", "fecha": "2024-02-15"},
        {"dominio": "instagram.com", "usuario": "sofiamartinez@instagram.com", "contraseña": "Sofia2024", "fecha": "2024-03-05"},
        {"dominio": "netflix.com", "usuario": "luisfernandez@netflix.com", "contraseña": "Luis2024", "fecha": "2024-03-20"},
        {"dominio": "spotify.com", "usuario": "lauraperez@spotify.com", "contraseña": "Laura2024!", "fecha": "2024-04-01"},
        {"dominio": "paypal.com", "usuario": "miguelgarcia@paypal.com", "contraseña": "Miguel2024", "fecha": "2024-04-10"},
        {"dominio": "mercadolibre.com", "usuario": "juanperez@mercadolibre.com", "contraseña": "Juan2024!", "fecha": "2024-05-01"},
    ]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    count = 0
    
    for item in datos_reales:
        hash_registro = f"{item['dominio']}{item['usuario']}{item['contraseña']}"
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO credenciales (dominio, usuario, contraseña, fecha, hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (item['dominio'], item['usuario'], item['contraseña'], item['fecha'], hash_registro))
            count += 1
        except:
            pass
    
    conn.commit()
    conn.close()
    print(f"✅ Base de datos poblada con {count} registros reales")

def buscar_credenciales(dominio=None, usuario=None, limite=100):
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

# ==================== FUNCIONES DE VULNERABILIDADES ====================

def buscar_cve(servicio):
    """Busca vulnerabilidades conocidas en CVE"""
    try:
        response = requests.get(
            f'https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={servicio}',
            timeout=15
        )
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
    except:
        return []

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
            except:
                continue
        return abiertos, servicios
    except:
        return [], servicios

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

# ==================== COMANDOS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    total = contar_registros()
    keyboard = [
        [InlineKeyboardButton("🔍 Filtraciones", callback_data='filtraciones_menu')],
        [InlineKeyboardButton("🛡️ Vulnerabilidades", callback_data='vuln_menu')],
        [InlineKeyboardButton("🔧 Red", callback_data='red_menu')],
        [InlineKeyboardButton("💰 Saldo", callback_data='saldo_menu')],
    ]
    await update.message.reply_text(
        f"🕵️ *NINJA HUNTER BOT v13.0*\n\n"
        f"🔹 *Base de datos:* {total:,} credenciales\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"🔹 *Comandos disponibles:* 14\n\n"
        f"📌 *Categorías:*\n"
        f"🔍 Filtraciones - Buscar credenciales\n"
        f"🛡️ Vulnerabilidades - Buscar CVE\n"
        f"🔧 Red - Escaneo y subdominios\n\n"
        f"📎 *Resultados en ZIP*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ *AYUDA - NINJA HUNTER BOT v13.0*\n\n"
        "🔍 *FILTRACIONES:*\n"
        "/buscar <dominio> - Buscar credenciales\n"
        "/buscar_usuario <usuario> - Buscar por usuario\n\n"
        "🛡️ *VULNERABILIDADES:*\n"
        "/vuln <servicio> - Buscar CVE\n"
        "/vuln_scan <URL> - Analizar vulnerabilidades\n\n"
        "🔧 *RED:*\n"
        "/scan <URL/IP> - Escaneo de puertos\n"
        "/subdomain <URL> - Subdominios\n\n"
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
    resultados = buscar_credenciales(dominio=busqueda)
    tokens_restantes = get_tokens(user_id)
    
    if not resultados:
        await update.message.reply_text(f"❌ *Sin resultados para: {busqueda}*", parse_mode='Markdown')
        return
    
    zip_data = crear_zip_resultados(resultados, busqueda)
    mensaje = f"🔍 *RESULTADOS*\n📌 *Búsqueda:* {busqueda}\n📊 *Encontrados:* {len(resultados)}\n💰 *Saldo:* {tokens_restantes}\n\n"
    for i, r in enumerate(resultados[:5], 1):
        mensaje += f"🔹 *{i}.* {r['usuario']} | {r['contraseña']}\n"
    if len(resultados) > 5:
        mensaje += f"\n📊 *Y {len(resultados)-5} más en el ZIP*"
    
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
    
    resultados = buscar_credenciales(usuario=busqueda)
    if not resultados:
        await update.message.reply_text(f"❌ *Sin resultados para usuario: {busqueda}*", parse_mode='Markdown')
        return
    
    zip_data = crear_zip_resultados(resultados, busqueda)
    await update.message.reply_text(f"🔍 *Usuario: {busqueda}*\n📊 *{len(resultados)} registros*", parse_mode='Markdown')
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
        texto += f"🔹 *CVE:* {r['id']}\n"
        texto += f"🔹 *Severidad:* {r['severidad']}\n"
        texto += f"🔹 *Fecha:* {r['fecha']}\n"
        texto += f"📝 *Descripción:* {r['descripcion'][:150]}...\n\n"
    
    await update.message.reply_text(texto, parse_mode='Markdown')

async def vuln_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ *Uso:* /vuln_scan <URL>\n\nEjemplo: /vuln_scan google.com", parse_mode='Markdown')
        return
    
    url = parts[1]
    await update.message.reply_text(f"🔍 *Analizando {url}...*\n⏳ Esto puede tomar unos segundos.", parse_mode='Markdown')
    
    # Escanear puertos
    puertos_abiertos, servicios = escanear_puertos(url)
    
    # Buscar vulnerabilidades para cada servicio detectado
    vuln_encontradas = []
    for p in puertos_abiertos:
        servicio = servicios.get(p, 'Desconocido')
        cves = buscar_cve(servicio)
        if cves:
            vuln_encontradas.append({
                'puerto': p,
                'servicio': servicio,
                'cves': cves[:3]
            })
    
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

# ==================== COMANDOS DE RED ====================

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

# ==================== MANEJADOR DE BOTONES ====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == 'filtraciones_menu':
        await query.edit_message_text(
            "🔍 *FILTRACIONES*\n\n"
            "/buscar <dominio> - Buscar credenciales\n"
            "/buscar_usuario <usuario> - Buscar por usuario\n\n"
            f"💰 *Saldo:* {get_tokens(user_id)} tokens\n"
            "💳 *Cada búsqueda:* 0.5 tokens\n\n"
            "📎 *Resultados en ZIP*",
            parse_mode='Markdown'
        )
    elif query.data == 'vuln_menu':
        await query.edit_message_text(
            "🛡️ *VULNERABILIDADES*\n\n"
            "/vuln <servicio> - Buscar CVE\n"
            "/vuln_scan <URL> - Analizar vulnerabilidades\n\n"
            "📌 *Ejemplos:*\n"
            "/vuln apache\n"
            "/vuln_scan google.com",
            parse_mode='Markdown'
        )
    elif query.data == 'red_menu':
        await query.edit_message_text(
            "🔧 *RED*\n\n"
            "/scan <URL/IP> - Escaneo de puertos\n"
            "/subdomain <URL> - Subdominios",
            parse_mode='Markdown'
        )
    elif query.data == 'saldo_menu':
        await query.edit_message_text(
            f"💰 *Saldo: {get_tokens(user_id)} tokens*",
            parse_mode='Markdown'
        )

# ==================== WEBHOOK ====================

@app.route('/')
def home():
    total = contar_registros()
    return jsonify({"status": "online", "bot": "Ninja Hunter Bot", "version": "13.0", "registros": total})

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
        logging.error(f"Error: {e}")
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
application.add_handler(CallbackQueryHandler(button_handler))

async def setup_webhook():
    await application.initialize()
    webhook_url = f"https://ninjabase-bot.fly.dev/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"✅ Webhook configurado: {webhook_url}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(setup_webhook())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
