import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
SETTINGS_FILE = '/tmp/settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {
        'token': '8690395101:AAFE3Zidfp36vXb0JOUqwI4TAMC9qW7eUEA',
        'admin_password': 'F5M-TEAM',
        'max_users': 20,
        'active_users': [],
        'is_active': False
    }

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

settings = load_settings()
bot_app = None
polling_thread = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not settings['is_active']:
        await update.message.reply_text(
            "🤖 البوت غير مفعل\n🔐 أرسل كلمة السر للتفعيل:"
        )
        context.user_data['awaiting_password'] = True
        return
    
    if user_id in settings['active_users']:
        await update.message.reply_text("✅ البوت مفعل لديك بالفعل!")
        return
    
    if len(settings['active_users']) >= settings['max_users']:
        await update.message.reply_text(f"⚠️ تم الوصول للحد الأقصى: {settings['max_users']}")
        return
    
    context.user_data['awaiting_password'] = True
    await update.message.reply_text("🔐 أرسل كلمة السر:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if context.user_data.get('awaiting_password'):
        if text == settings['admin_password']:
            if len(settings['active_users']) < settings['max_users']:
                settings['active_users'].append(user_id)
                save_settings(settings)
                await update.message.reply_text("✅ تم التفعيل بنجاح!")
        else:
            await update.message.reply_text("❌ كلمة سر خاطئة")
        context.user_data['awaiting_password'] = False

def run_bot():
    global bot_app
    if settings['token'] and settings['is_active']:
        bot_app = Application.builder().token(settings['token']).build()
        bot_app.add_handler(CommandHandler("start", start_command))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        bot_app.run_polling()

@app.route('/api/get-settings', methods=['GET'])
def get_settings():
    return jsonify({
        'token': settings['token'],
        'admin_password': settings['admin_password'],
        'max_users': settings['max_users'],
        'active_users': len(settings['active_users']),
        'is_active': settings['is_active']
    })

@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    data = request.json
    settings['token'] = data.get('token', settings['token'])
    settings['admin_password'] = data.get('admin_password', settings['admin_password'])
    settings['max_users'] = data.get('max_users', settings['max_users'])
    save_settings(settings)
    return jsonify({'success': True})

@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    settings['is_active'] = not settings['is_active']
    save_settings(settings)
    
    if settings['is_active'] and settings['token']:
        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()
    
    return jsonify({'is_active': settings['is_active']})

if __name__ == '__main__':
    app.run()
