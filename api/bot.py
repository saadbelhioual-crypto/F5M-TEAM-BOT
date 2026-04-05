import json
import os
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify

app = Flask(__name__)

# تحميل الإعدادات
SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {
        'token': '',
        'adminPassword': 'F5M-TEAM',
        'maxUsers': 20,
        'activeUsers': [],
        'isActive': False
    }

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

settings = load_settings()
bot_application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not settings['isActive']:
        await update.message.reply_text(
            "🤖 البوت ليس مفعل حالياً\n"
            "🔐 أعطني كلمة السر للتفعيل:"
        )
        return
    
    if user_id in settings['activeUsers']:
        await update.message.reply_text("✅ البوت مفعل لديك بالفعل!")
        return
    
    if len(settings['activeUsers']) >= settings['maxUsers']:
        await update.message.reply_text(
            "⚠️ البوت وصل للعدد الأقصى من المستخدمين!\n"
            f"الحد الأقصى: {settings['maxUsers']} مستخدم"
        )
        return
    
    context.user_data['awaiting_password'] = True
    await update.message.reply_text(
        "🔐 البوت غير مفعل لديك\n"
        "الرجاء إدخال كلمة السر للتفعيل:"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if context.user_data.get('awaiting_password'):
        if text == settings['adminPassword']:
            if len(settings['activeUsers']) >= settings['maxUsers']:
                await update.message.reply_text("⚠️ العدد الأقصى للمستخدمين تم الوصول إليه!")
            else:
                settings['activeUsers'].append(user_id)
                save_settings(settings)
                await update.message.reply_text(
                    "✅ تم تفعيل البوت بنجاح!\n"
                    "شكراً لاستخدامك بوت F5M"
                )
        else:
            await update.message.reply_text("❌ كلمة السر غير صحيحة!")
        context.user_data['awaiting_password'] = False

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_message(update, context)

def setup_bot():
    global bot_application
    if not settings['token'] or not settings['isActive']:
        return None
    
    bot_application = Application.builder().token(settings['token']).build()
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return bot_application

@app.route('/api/get-settings', methods=['GET'])
def get_settings():
    return jsonify({
        'token': settings['token'],
        'adminPassword': settings['adminPassword'],
        'maxUsers': settings['maxUsers'],
        'activeUsers': len(settings['activeUsers']),
        'isActive': settings['isActive']
    })

@app.route('/api/update-settings', methods=['POST'])
def update_settings():
    data = request.json
    old_password = settings['adminPassword']
    
    settings['token'] = data.get('token', settings['token'])
    settings['adminPassword'] = data.get('adminPassword', settings['adminPassword'])
    settings['maxUsers'] = data.get('maxUsers', settings['maxUsers'])
    
    # إذا تغيرت كلمة السر
    if old_password != settings['adminPassword']:
        # إرسال رسالة للمستخدمين المفعلين
        if settings['token'] and settings['isActive']:
            bot = Bot(settings['token'])
            for user_id in settings['activeUsers']:
                try:
                    bot.send_message(
                        user_id,
                        "⚠️ تم تغيير إعدادات البوت!\n"
                        "تواصل مع @abdou_F5M لتتمكن من الحصول على البوت الجديد"
                    )
                except:
                    pass
        settings['activeUsers'] = []  # إعادة تعيين المستخدمين
    
    save_settings(settings)
    setup_bot()
    return jsonify({'success': True})

@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    settings['isActive'] = not settings['isActive']
    save_settings(settings)
    
    if settings['isActive']:
        setup_bot()
    
    return jsonify({'isActive': settings['isActive']})

if __name__ == '__main__':
    app.run(debug=True)
