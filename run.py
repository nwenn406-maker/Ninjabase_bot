from app import telegram_app, app
import os
import threading

TOKEN = os.getenv('TELEGRAM_TOKEN')

def run_bot():
    print("🤖 OSINT Ninja Bot v4.0 iniciado en Render")
    telegram_app.run_polling()

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
