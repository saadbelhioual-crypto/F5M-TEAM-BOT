import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
import threading
import time

app = Flask(__name__)

SETTINGS_FILE = '/tmp/settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {
        'token': '',
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
    username = update.effective_user.username or "مستخدم"
    
    if not settings['is_active']:
        await update.message.reply_text(
            f"👋 مرحباً {username}!\n\n"
            "🤖 البوت غير مفعل حالياً\n"
            "🔐 الرجاء إرسال كلمة السر للتفعيل:"
        )
        context.user_data['awaiting_password'] = True
        return
    
    if user_id in settings['active_users']:
        await update.message.reply_text("✅ البوت مفعل لديك بالفعل!")
        return
    
    if len(settings['active_users']) >= settings['max_users']:
        await update.message.reply_text(f"⚠️ البوت وصل للعدد الأقصى: {settings['max_users']} مستخدم")
        return
    
    context.user_data['awaiting_password'] = True
    await update.message.reply_text("🔐 الرجاء إدخال كلمة السر للتفعيل:")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if context.user_data.get('awaiting_password'):
        if text == settings['admin_password']:
            if len(settings['active_users']) >= settings['max_users']:
                await update.message.reply_text("⚠️ العدد الأقصى تم الوصول إليه!")
            else:
                settings['active_users'].append(user_id)
                save_settings(settings)
                await update.message.reply_text(
                    "✅ تم تفعيل البوت بنجاح!\n"
                    f"المستخدمون النشطون: {len(settings['active_users'])}/{settings['max_users']}"
                )
        else:
            await update.message.reply_text("❌ كلمة السر غير صحيحة!")
        context.user_data['awaiting_password'] = False

def run_bot_polling():
    """تشغيل البوت بطريقة Polling"""
    global bot_app
    try:
        if settings['token'] and settings['is_active']:
            bot_app = Application.builder().token(settings['token']).build()
            bot_app.add_handler(CommandHandler("start", start_command))
            bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            print(f"🚀 Bot starting with polling... Token: {settings['token'][:10]}...")
            bot_app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Polling error: {e}")

def start_bot_polling():
    """بدء البوت في thread منفصل"""
    global polling_thread
    if polling_thread is None or not polling_thread.is_alive():
        polling_thread = threading.Thread(target=run_bot_polling)
        polling_thread.daemon = True
        polling_thread.start()
        return True
    return False

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
    old_password = settings['admin_password']
    
    settings['token'] = data.get('token', settings['token'])
    settings['admin_password'] = data.get('admin_password', settings['admin_password'])
    settings['max_users'] = data.get('max_users', settings['max_users'])
    
    if old_password != settings['admin_password']:
        settings['active_users'] = []
    
    save_settings(settings)
    
    # إعادة تشغيل البوت بالإعدادات الجديدة
    if settings['is_active'] and settings['token']:
        start_bot_polling()
    
    return jsonify({'success': True})

@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    settings['is_active'] = not settings['is_active']
    save_settings(settings)
    
    if settings['is_active'] and settings['token']:
        success = start_bot_polling()
        if success:
            return jsonify({'is_active': True, 'message': 'Bot started with polling'})
    else:
        # إيقاف البوت
        global bot_app
        if bot_app:
            try:
                bot_app.stop()
            except:
                pass
    
    return jsonify({'is_active': settings['is_active']})

@app.route('/api/keep-alive', methods=['GET'])
def keep_alive():
    """نقطة نهاية لإبقاء البوت حياً"""
    if settings['is_active'] and settings['token']:
        start_bot_polling()
    return jsonify({'status': 'alive', 'bot_active': settings['is_active']})

# بدء البوت تلقائياً
if settings['is_active'] and settings['token']:
    start_bot_polling()

if __name__ == '__main__':
    app.run(debug=True)
