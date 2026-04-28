# ================ استيراد المكتبات ================
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
import sqlite3
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ================ تحميل المتغيرات ================
load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================ قاعدة البيانات ================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT,
    user_id INTEGER,
    chat_id INTEGER,
    message TEXT,
    request_type TEXT,
    subject TEXT,
    grade TEXT
)
""")
conn.commit()

def save_request(name, username, user_id, chat_id, message, req_type, subject, grade):
    cursor.execute(
        "INSERT INTO requests (name, username, user_id, chat_id, message, request_type, subject, grade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, username, user_id, chat_id, message, req_type, subject, grade)
    )
    conn.commit()

# ================ نظام الكلمات الذكي ================
REQUEST_SIGNALS = [
    "ابغى", "اريد", "احتاج", "ادور", "ابحث", "محتاج", "محتاجة",
    "اللي يساعدني", "اللي يقدر يساعد", "ساعدوني", "ياجماعة", "ياشباب",
    "ممكن مساعدة", "ابي", "أبغى", "أريد", "أحتاج", "أبحث", "مطلوب",
    "ضروري", "تكفون", "الله يجزاكم خير", "اللي عنده خبر",
    "طلب", "طلب مساعدة", "احتاج مساعدة", "ابي مساعدة"
]

TYPE_WORDS = {
    "مشروع": ["مشروع", "بروجكت", "عمل مشروع", "مشروع تخرج", "مشروعي"],
    "واجب": ["واجب", "واجبي", "حل واجب", "تسليم واجب", "واجبات"],
    "شرح": ["شرح", "شرحين", "يفهمني", "فهمني", "شرح الدرس", "مافهمت"],
    "بحث": ["بحث", "تقرير", "ورقة بحثية", "بحثي", "عمل بحث", "كتابة بحث"],
    "تمارين": ["تمارين", "تمرين", "حل تمارين", "مسائل", "حل مسألة"],
    "ملخص": ["ملخص", "تلخيص", "ملخصات", "تلخيصات"],
    "مساعدة عامة": ["مساعدة", "ساعدوني", "محتاج مساعدة", "طلب مساعدة"]
}

SUBJECT_LIST = [
    "رياضيات", "فيزياء", "كيمياء", "أحياء", "إنجليزي", "عربي",
    "لغة عربية", "علوم", "حاسب", "تقنية", "تاريخ", "جغرافيا",
    "تربية إسلامية", "فقه", "توحيد", "حديث", "لغة إنجليزية",
    "رياضيات بحتة", "رياضيات تطبيقية", "فيزياء عامة", "كيمياء عضوية"
]

GRADE_PATTERNS = {
    "أول ابتدائي": ["اول ابتدائي", "أول ابتدائي", "الأول الإبتدائي"],
    "ثاني ابتدائي": ["ثاني ابتدائي", "الثاني الإبتدائي"],
    "ثالث ابتدائي": ["ثالث ابتدائي", "الثالث الإبتدائي"],
    "رابع ابتدائي": ["رابع ابتدائي", "الرابع الإبتدائي"],
    "خامس ابتدائي": ["خامس ابتدائي", "الخامس الإبتدائي"],
    "سادس ابتدائي": ["سادس ابتدائي", "السادس الإبتدائي"],
    "أول متوسط": ["اول متوسط", "أول متوسط", "الأول متوسط"],
    "ثاني متوسط": ["ثاني متوسط", "الثاني متوسط"],
    "ثالث متوسط": ["ثالث متوسط", "الثالث متوسط"],
    "أول ثانوي": ["اول ثانوي", "أول ثانوي", "الأول ثانوي"],
    "ثاني ثانوي": ["ثاني ثانوي", "الثاني ثانوي"],
    "ثالث ثانوي": ["ثالث ثانوي", "الثالث ثانوي"],
    "جامعة": ["جامعة", "جامعي", "جامعيه"]
}

def analyze_request(text: str):
    text_lower = text.strip().lower()
    is_req = any(signal in text_lower for signal in REQUEST_SIGNALS)
    if not is_req:
        return {"is_request": False, "request_type": "", "subject": "", "grade": ""}

    req_type = "طلب عام"
    for typ, keywords in TYPE_WORDS.items():
        if any(kw in text_lower for kw in keywords):
            req_type = typ
            break

    subject = ""
    for sub in sorted(SUBJECT_LIST, key=len, reverse=True):
        if sub.lower() in text_lower:
            subject = sub
            break

    grade = ""
    for grade_name, patterns in GRADE_PATTERNS.items():
        if any(pat in text_lower for pat in patterns):
            grade = grade_name
            break

    return {
        "is_request": True,
        "request_type": req_type,
        "subject": subject,
        "grade": grade
    }

# ================ دالة استقبال الرسائل ================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    chat_id = update.effective_chat.id

    analysis = analyze_request(text)
    if not analysis["is_request"]:
        return

    req_type = analysis["request_type"]
    subject = analysis["subject"]
    grade = analysis["grade"]

    save_request(
        user.first_name,
        user.username,
        user.id,
        chat_id,
        text,
        req_type,
        subject,
        grade
    )

    # ===== إرسال إشعار خاص للمشرف فقط =====
    admin_msg = (
        "📥 طلب جديد من المجموعة\n"
        f"👤 الاسم: {user.first_name}\n"
        f"📎 اليوزر: @{user.username}\n"
        f"🆔 معرف المستخدم: <code>{user.id}</code>\n"
        f"💬 معرف المجموعة: <code>{chat_id}</code>\n"
        f"📌 النوع: {req_type}\n"
        f"📚 المادة: {subject if subject else 'غير محدد'}\n"
        f"🏫 الصف: {grade if grade else 'غير محدد'}\n\n"
        f"📝 الرسالة:\n{text}"
    )
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_msg,
        parse_mode="HTML"
    )

# ================ خادم HTTP وهمي (ضروري لـ Render) ================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def log_message(self, format, *args):
        return  # إسكات السجلات غير الضرورية

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

# تشغيل الخادم في خيط منفصل حتى لا يعطل البوت
threading.Thread(target=start_dummy_server, daemon=True).start()

# ================ تشغيل البوت ================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🚀 البوت الذكي يعمل الآن (مجاني – بدون API خارجي)...")
app.run_polling()
