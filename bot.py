import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from scanners.port_scanner import scan_ports
from scanners.subdomain_finder import find_subdomains

TOKEN = os.environ.get("TELEGRAM_TOKEN")
logging.basicConfig(level=logging.INFO)

# ───────── 🔧 RED & SEGURIDAD ─────────

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /scan <URL/IP> — Escaneo real de puertos con Nmap"""
    if not context.args:
        await update.message.reply_text(
            "┌ 🔧 ｢ RED & SEGURIDAD ｣ ─\n"
            "├ Uso: /scan <URL/IP>\n"
            "└ Ejemplo: /scan scanme.nmap.org"
        )
        return
    
    target = context.args[0]
    await update.message.reply_text(f"⏳ Escaneando {target}... (puede tardar hasta 5 min)")
    
    result = scan_ports(target, fast=True)
    
    if "error" in result:
        await update.message.reply_text(
            f"┌ 🔧 ｢ ERROR ｣ ─\n"
            f"├ Objetivo: {target}\n"
            f"└ ❌ {result['error']}"
        )
        return
    
    # Construir respuesta en formato árbol
    lines = [
        "┌ 🔧 ｢ RED & SEGURIDAD ｣ ─",
        f"├ Objetivo: {result['target']}",
        f"├ Puertos abiertos: {result['total']}",
    ]
    
    if result["total"] == 0:
        lines.append("└ ✅ No se encontraron puertos abiertos")
    else:
        for i, port in enumerate(result["ports"]):
            prefix = "└" if i == len(result["ports"]) - 1 else "├"
            version = f" ── {port['version']}" if port['version'] else ""
            lines.append(
                f"{prefix} {port['port']}/tcp ── {port['service']}{version}"
            )
    
    await update.message.reply_text("\n".join(lines))


async def subdomain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /subdomain <URL> — Búsqueda real de subdominios"""
    if not context.args:
        await update.message.reply_text(
            "┌ 🔧 ｢ RED & SEGURIDAD ｣ ─\n"
            "├ Uso: /subdomain <URL>\n"
            "└ Ejemplo: /subdomain example.com"
        )
        return
    
    target = context.args[0]
    await update.message.reply_text(f"⏳ Buscando subdominios de {target}...")
    
    result = find_subdomains(target)
    
    if "error" in result:
        await update.message.reply_text(
            f"┌ 🔧 ｢ ERROR ｣ ─\n"
            f"├ Dominio: {target}\n"
            f"└ ❌ {result['error']}"
        )
        return
    
    # Limitar a 20 subdominios para no saturar Telegram
    subs = result["subdomains"][:20]
    
    lines = [
        "┌ 🔧 ｢ RED & SEGURIDAD ｣ ─",
        f"├ Dominio: {result['domain']}",
        f"├ Subdominios encontrados: {result['total']}",
    ]
    
    if not subs:
        lines.append("└ ✅ No se encontraron subdominios")
    else:
        for i, sub in enumerate(subs):
            prefix = "└" if i == len(subs) - 1 else "├"
            lines.append(f"{prefix} {sub}")
        if result["total"] > 20:
            lines.append(f"   ... y {result['total'] - 20} más")
    
    await update.message.reply_text("\n".join(lines))


# ───────── 🛠 UTILIDADES ─────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "┌ 🥷 ｢ NINJA DATA BOT ｣ ─\n"
        "├ /scan <URL/IP> ── Escaneo de puertos\n"
        "├ /subdomain <URL> ── Chequeo de subdominios\n"
        "└ /help ── Ver todos los comandos"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "┌ 📖 ｢ COMANDOS ｣ ─\n"
        "├ 🔧 /scan <URL/IP> ── Nmap real\n"
        "├ 🔧 /subdomain <URL> ── crt.sh real\n"
        "└ 🛠 /start ── Inicio"
    )


def main():
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN no configurado")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("subdomain", subdomain))
    
    print("🥷 NinjaDataBot iniciado...")
    app.run_polling()


if __name__ == "__main__":
    main()
