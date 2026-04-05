import json
import os
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
from threading import Thread

app = Flask(__name__)

# ملف الإعدادات
SETTINGS_FILE = '/tmp/settings.json'  # Vercel يستخدم /tmp للتخزين المؤقت

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {
        'token': '',
        'admin_password': 'F5M-TEAM',
        'max_users': 20,
        'active_users': [],
        'is_active': False,
        'bot_running': False
    }

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

settings = load_settings()
bot_app = None
bot_thread = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "مستخدم"
    
    if not settings['is_active']:
        await update.message.reply_text(
            f"👋 مرحباً {username}!\n\n"
            "🤖 **البوت غير مفعل حالياً**\n"
            "🔐 الرجاء إرسال كلمة السر للتفعيل:\n\n"
            "💡 *ملاحظة:* البوت لا يعمل إلا بعد التفعيل الصحيح",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_password'] = True
        return
    
    if user_id in settings['active_users']:
        await update.message.reply_text(
            "✅ **البوت مفعل لديك بالفعل!**\n\n"
            "✨ يمكنك استخدام جميع ميزات البوت\n"
            "🎮 شكراً لانضمامك إلينا",
            parse_mode='Markdown'
        )
        return
    
    if len(settings['active_users']) >= settings['max_users']:
        await update.message.reply_text(
            "⚠️ **عذراً!**\n\n"
            f"البوت وصل للعدد الأقصى من المستخدمين: **{settings['max_users']}**\n"
            "🚫 لا يمكن تفعيل بوتات جديدة حالياً",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['awaiting_password'] = True
    await update.message.reply_text(
        "🔐 **البوت غير مفعل لديك**\n\n"
        "الرجاء إدخال كلمة السر للتفعيل:\n"
        "💡 *كلمة السر مخصصة للإداريين فقط*",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل العادية"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if context.user_data.get('awaiting_password'):
        if text == settings['admin_password']:
            if len(settings['active_users']) >= settings['max_users']:
                await update.message.reply_text(
                    "⚠️ **العدد الأقصى تم الوصول إليه!**\n\n"
                    f"الحد الأقصى: {settings['max_users']} مستخدم\n"
                    "🚫 لا يمكن تفعيل المزيد",
                    parse_mode='Markdown'
                )
            else:
                settings['active_users'].append(user_id)
                save_settings(settings)
                await update.message.reply_text(
                    "✅ **تم تفعيل البوت بنجاح!**\n\n"
                    "🎉 شكراً لاستخدامك بوت F5M\n"
                    "✨ يمكنك الآن استخدام جميع الميزات\n\n"
                    f"📊 المستخدمون النشطون: {len(settings['active_users'])}/{settings['max_users']}",
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                "❌ **كلمة السر غير صحيحة!**\n\n"
                "الرجاء المحاولة مرة أخرى:\n"
                "🔐 أرسل كلمة السر الصحيحة للتفعيل",
                parse_mode='Markdown'
            )
        context.user_data['awaiting_password'] = False
    else:
        if user_id in settings['active_users']:
            await update.message.reply_text(
                "✨ **مرحباً بك في بوت F5M!**\n\n"
                "💫 البوت يعمل بشكل طبيعي\n"
                "🎯 استخدم /start لعرض القائمة الرئيسية",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⚠️ **البوت غير مفعل لديك**\n\n"
                "🔐 أرسل /start ثم أدخل كلمة السر للتفعيل",
                parse_mode='Markdown'
            )

async def bot_worker():
    """تشغيل البوت في الخلفية"""
    global bot_app
    try:
        if settings['token'] and settings['is_active']:
            bot_app = Application.builder().token(settings['token']).build()
            bot_app.add_handler(CommandHandler("start", start_command))
            bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # بدء البوت
            await bot_app.initialize()
            await bot_app.start()
            
            # بدء webhook (لـ Vercel)
            webhook_url = f"https://{os.environ.get('VERCEL_URL', 'localhost')}/api/webhook"
            await bot_app.bot.set_webhook(webhook_url)
            
            print(f"✅ Bot started successfully! Token: {settings['token'][:10]}...")
            
            # الحفاظ على التشغيل
            while settings['is_active']:
                await asyncio.sleep(1)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        settings['is_active'] = False
        save_settings(settings)

def start_bot_thread():
    """بدء تشغيل البوت في thread منفصل"""
    global bot_thread
    if bot_thread is None or not bot_thread.is_alive():
        bot_thread = Thread(target=lambda: asyncio.run(bot_worker()))
        bot_thread.start()

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
    old_token = settings['token']
    
    # تحديث الإعدادات
    settings['token'] = data.get('token', settings['token'])
    settings['admin_password'] = data.get('admin_password', settings['admin_password'])
    settings['max_users'] = data.get('max_users', settings['max_users'])
    
    # إذا تغيرت كلمة السر، إعادة تعيين المستخدمين
    if old_password != settings['admin_password'] and settings['token']:
        # إرسال إشعار للمستخدمين المفعلين
        try:
            async def notify_users():
                bot = Bot(settings['token'])
                for user_id in settings['active_users']:
                    try:
                        await bot.send_message(
                            user_id,
                            "⚠️ **تم تغيير إعدادات البوت!**\n\n"
                            "🔐 تم تحديث نظام التفعيل\n"
                            "📞 تواصل مع @abdou_F5M للحصول على البوت الجديد\n\n"
                            "❌ تم إلغاء تفعيل البوت لديك",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            asyncio.run(notify_users())
        except:
            pass
        settings['active_users'] = []
    
    # إذا تغير التوكن، إعادة تشغيل البوت
    if old_token != settings['token']:
        settings['is_active'] = False
        if bot_app:
            try:
                async def stop_bot():
                    await bot_app.stop()
                asyncio.run(stop_bot())
            except:
                pass
    
    save_settings(settings)
    
    # بدء البوت إذا كان مفعلاً
    if settings['is_active'] and settings['token']:
        start_bot_thread()
    
    return jsonify({'success': True})

@app.route('/api/toggle-bot', methods=['POST'])
def toggle_bot():
    settings['is_active'] = not settings['is_active']
    save_settings(settings)
    
    if settings['is_active'] and settings['token']:
        start_bot_thread()
    elif not settings['is_active'] and bot_app:
        try:
            async def stop_bot():
                await bot_app.stop()
            asyncio.run(stop_bot())
        except:
            pass
    
    return jsonify({'is_active': settings['is_active']})

@app.route('/api/webhook', methods=['POST'])
async def webhook():
    """نقطة نهاية webhook لتيليجرام"""
    if not settings['is_active'] or not settings['token']:
        return jsonify({'status': 'bot inactive'})
    
    try:
        update = Update.de_json(request.get_json(), bot_app.bot)
        await bot_app.process_update(update)
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

# بدء البوت تلقائياً إذا كان مفعلاً
if settings['is_active'] and settings['token']:
    start_bot_thread()

if __name__ == '__main__':
    app.run(debug=True)
