import os
import sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- إعداد الخادم الوهمي لمنع الإغلاق ---
app_server = Flask(__name__)
@app_server.route('/')
def home():
    return "البوت يعمل الآن!"

def run_server():
    app_server.run(host='0.0.0.0', port=8080)

# --- بياناتك ---
TOKEN = os.environ.get("BOT_TOKEN", "8418588205:AAG983jkzjH6rUrhmeRf6V2gI6fDRNE1De0")
ADMIN_PASSWORD = "123"
ADMIN_ID = "8418588205"
DESTINATION_ID = "-5378998412"

def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, section TEXT, file_id TEXT, file_name TEXT)')
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📂 تصفح الملفات الدراسية", callback_data='view_sections')],
        [InlineKeyboardButton("📤 إرسال ملف للأستاذ", callback_data='send_info')]
    ]
    await update.message.reply_text("مرحباً بك في بوت الأستاذ عمر التعليمي.", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("يمكنك الآن إرسال ملفك وسأقوم بتحويله للأستاذ مباشرة.")

async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] != ADMIN_PASSWORD:
        return
    section = context.args[1] if len(context.args) > 1 else "عام"
    if update.message.document or update.message.photo:
        file_id = update.message.document.file_id if update.message.document else update.message.photo[-1].file_id
        file_name = update.message.document.file_name if update.message.document else "صورة.jpg"
        conn = sqlite3.connect('data.db')
        conn.cursor().execute('INSERT INTO files (section, file_id, file_name) VALUES (?, ?, ?)', (section, file_id, file_name))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم إضافة الملف لقسم: {section}")

async def handle_student_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await context.bot.forward_message(chat_id=DESTINATION_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        await update.message.reply_text("✅ تم استلام ملفك وإرساله للأستاذ بنجاح.")

async def view_sections(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('data.db')
    sections = [r[0] for r in conn.cursor().execute('SELECT DISTINCT section FROM files').fetchall()]
    conn.close()
    if not sections:
        await update.callback_query.message.reply_text("لا توجد ملفات حالياً.")
        return
    keyboard = [[InlineKeyboardButton(f"📂 {s}", callback_data=f'sec_{s}')] for s in sections]
    await update.callback_query.edit_message_text("اختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    section = update.callback_query.data.replace('sec_', '')
    conn = sqlite3.connect('data.db')
    files = conn.cursor().execute('SELECT file_id, file_name FROM files WHERE section=?', (section,)).fetchall()
    conn.close()
    for f_id, f_name in files:
        await update.callback_query.message.reply_document(f_id, caption=f_name)

if __name__ == '__main__':
    # تشغيل الخادم الوهمي في الخلفية
    Thread(target=run_server).start()
    
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_file))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_student_files))
    app.add_handler(CallbackQueryHandler(view_sections, pattern='view_sections'))
    app.add_handler(CallbackQueryHandler(show_files, pattern='sec_.*'))
    app.add_handler(CallbackQueryHandler(send_info, pattern='send_info'))
    print("البوت يعمل الآن...")
    app.run_polling()
