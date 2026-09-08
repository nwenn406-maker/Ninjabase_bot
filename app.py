import os
import logging
import sqlite3
import base64
import threading
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== CONFIGURACIÓN ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_RAW = os.getenv('TELEGRAM_TOKEN')
if not TOKEN_RAW:
    raise ValueError("❌ TELEGRAM_TOKEN no configurado")
TOKEN = base64.b64encode(TOKEN_RAW.encode()).decode()

DB_NAME = "system_cache.db"

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

# ==================== BASE DE DATOS ====================

def init_db():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # CREAR TABLAS PARA 8 PAÍSES
        # Argentina
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
        
        # Guatemala
        c.execute('''CREATE TABLE IF NOT EXISTS guatemala_renap (
            dpi TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS guatemala_sat (
            nit TEXT PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT)''')
        
        # México
        c.execute('''CREATE TABLE IF NOT EXISTS mexico_imss (
            curp TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            telefono TEXT, direccion TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS mexico_sat (
            rfc TEXT PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT)''')
        
        # El Salvador
        c.execute('''CREATE TABLE IF NOT EXISTS salvador_dui (
            dui TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        # Honduras
        c.execute('''CREATE TABLE IF NOT EXISTS honduras_dni (
            dni TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        # Chile
        c.execute('''CREATE TABLE IF NOT EXISTS chile_rc (
            rut TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS chile_sii (
            rut TEXT PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT)''')
        
        # Brasil
        c.execute('''CREATE TABLE IF NOT EXISTS brasil_cpf (
            cpf TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS brasil_rf (
            cpf TEXT PRIMARY KEY, nombre TEXT, direccion TEXT, telefono TEXT)''')
        
        # Ecuador
        c.execute('''CREATE TABLE IF NOT EXISTS ecuador_cedula (
            cedula TEXT PRIMARY KEY, nombre TEXT, apellido TEXT, fecha_nac TEXT,
            direccion TEXT, telefono TEXT)''')
        
        # Índices
        c.execute('CREATE INDEX IF NOT EXISTS idx_renaper ON renaper(dni)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_dnrpa ON dnrpa(patente)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bcra ON bcra(cuil)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_telefonos ON telefonos(numero)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_emails ON emails(email)')
        
        conn.commit()
        conn.close()
        
        cargar_bases_reales()
        print("✅ Bases de datos inicializadas")
    except Exception as e:
        print(f"❌ Error: {e}")

def cargar_bases_reales():
    bases_dir = "databases"
    if not os.path.exists(bases_dir):
        os.makedirs(bases_dir)
        print("📁 Carpeta databases/ creada")
        return
    
    archivos = {
        'renaper': 'renaper.db',
        'dnrpa': 'dnrpa.db',
        'bcra': 'bcra.db',
        'telefonos': 'telefonos.db',
        'emails': 'emails.db',
        'credenciales_url': 'credenciales.db',
        'guatemala_renap': 'guatemala_renap.db',
        'guatemala_sat': 'guatemala_sat.db',
        'mexico_imss': 'mexico_imss.db',
        'mexico_sat': 'mexico_sat.db',
        'salvador_dui': 'salvador_dui.db',
        'honduras_dni': 'honduras_dni.db',
        'chile_rc': 'chile_rc.db',
        'chile_sii': 'chile_sii.db',
        'brasil_cpf': 'brasil_cpf.db',
        'brasil_rf': 'brasil_rf.db',
        'ecuador_cedula': 'ecuador_cedula.db'
    }
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    for tabla, archivo in archivos.items():
        ruta = os.path.join(bases_dir, archivo)
        if os.path.exists(ruta):
            try:
                conn_real = sqlite3.connect(ruta)
                c_real = conn_real.cursor()
                c_real.execute(f"SELECT * FROM {tabla}")
                datos = c_real.fetchall()
                conn_real.close()
                
                if datos:
                    placeholders = ','.join(['?'] * len(datos[0]))
                    c.executemany(f"INSERT OR IGNORE INTO {tabla} VALUES ({placeholders})", datos)
                    conn.commit()
                    print(f"✅ Cargada {archivo} ({len(datos)} registros)")
            except Exception as e:
                print(f"❌ Error en {archivo}: {e}")
    
    conn.close()

# ==================== FUNCIONES DE CONSULTA ====================

def consultar_renaper(dni):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM renaper WHERE dni = ?', (dni,))
        r = c.fetchone()
        conn.close()
        if r:
            return {'dni': r[0], 'nombre': r[1], 'apellido': r[2], 'fecha_nac': r[3],
                    'domicilio': r[4], 'localidad': r[5], 'provincia': r[6], 'cuil': r[7], 'telefono': r[8]}
        return None
    except:
        return None

def consultar_deuda(cuil):
    try:
        cuil_clean = ''.join(filter(str.isdigit, cuil))
        if len(cuil_clean) != 11:
            return None
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM bcra WHERE cuil = ?', (cuil_clean,))
        r = c.fetchone()
        conn.close()
        if r:
            return {'dni': r[1], 'nombre': r[2], 'fecha_nac': r[3],
                    'situacion': r[4], 'monto_deuda': r[5], 'entidades': r[6], 'score': r[7]}
        return None
    except:
        return None

def consultar_patente(patente):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM dnrpa WHERE patente = ?', (patente.upper(),))
        r = c.fetchone()
        conn.close()
        if r:
            return {'marca': r[1], 'modelo': r[2], 'año': r[3], 'titular': r[4], 'dni_titular': r[5]}
        return None
    except:
        return None

def consultar_titular(telefono):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM telefonos WHERE numero = ?', (telefono,))
        r = c.fetchone()
        conn.close()
        if r:
            return {'titular': r[1], 'dni_titular': r[2], 'compania': r[3], 'provincia': r[4]}
        return None
    except:
        return None

def consultar_email(email):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT password, dominio, fuente FROM emails WHERE email = ?', (email,))
        r = c.fetchone()
        conn.close()
        if r:
            return {'password': r[0], 'dominio': r[1], 'fuente': r[2]}
        return None
    except:
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

# ==================== COMANDOS ====================

async def start(update, context):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("🇦🇷 Argentina", callback_data='arg_menu')],
        [InlineKeyboardButton("💰 Tokens", callback_data='tokens')],
    ]
    await update.message.reply_text(
        f"🤖 *NINJA DATA BOT*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}\n"
        f"/dni <dni> - RENAPER\n"
        f"/deuda <cuil> - BCRA\n"
        f"/dnrpa <patente> - DNRPA\n"
        f"/email <email> - Filtraciones\n"
        f"/titular <tel> - Teléfono\n"
        f"/saldo - Ver tokens\n\n"
        f"🔐 *Modo Fantasma: ACTIVADO*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def arg_menu(update, context):
    await update.callback_query.edit_message_text(
        f"🇦🇷 *ARGENTINA*\n\n"
        f"/dni <dni> - RENAPER\n"
        f"/deuda <cuil> - BCRA\n"
        f"/dnrpa <patente> - DNRPA\n"
        f"/email <email> - Filtraciones\n"
        f"/titular <tel> - Teléfono\n\n"
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
        await update.message.reply_text(f"❌ DNI {dni} no encontrado.")
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
        await update.message.reply_text(f"❌ CUIL {cuil} no encontrado.")
        return
    msg = f"📊 *BCRA - CUIL {cuil}:*\n\n"
    msg += f"👤 {data['nombre']}\n"
    msg += f"📈 Situación: {data['situacion']}\n"
    msg += f"💸 Deuda: ${data['monto_deuda']:,}\n"
    msg += f"🏦 Entidades: {data['entidades']}\n"
    msg += f"📊 Score: {data['score']}\n"
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
    msg = f"📱 *Teléfono {phone}:*\n\n"
    msg += f"👤 Titular: {data['titular']}\n"
    msg += f"🆔 DNI: {data['dni_titular']}\n"
    msg += f"📶 Compañía: {data['compania']}\n"
    msg += f"📍 Provincia: {data['provincia']}\n"
    msg += f"\n💳 *Tokens restantes:* {get_tokens(update.effective_user.id)}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def saldo_command(update, context):
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"💰 *SALDO*\n\n"
        f"🔹 *Tokens:* {get_tokens(user_id)}",
        parse_mode='Markdown'
    )

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == 'arg_menu':
        await arg_menu(update, context)
    elif query.data == 'tokens':
        await query.edit_message_text(
            f"💰 *Tokens: {get_tokens(query.from_user.id)}*",
            parse_mode='Markdown'
        )

# ==================== MAIN ====================

def main():
    try:
        print("🚀 Iniciando NINJA DATA BOT...")
        init_db()
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("🌐 Flask server iniciado")
        
        app = Application.builder().token(base64.b64decode(TOKEN).decode()).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("dni", dni_command))
        app.add_handler(CommandHandler("deuda", deuda_command))
        app.add_handler(CommandHandler("dnrpa", dnrpa_command))
        app.add_handler(CommandHandler("email", email_command))
        app.add_handler(CommandHandler("titular", titular_command))
        app.add_handler(CommandHandler("saldo", saldo_command))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("✅ NINJA DATA BOT - ACTIVO")
        print("🔐 Modo Fantasma: ACTIVADO")
        print("📁 Bases de datos en: databases/")
        
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == '__main__':
    main()
