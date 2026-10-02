import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import google.generativeai as genai

# ====== الإعدادات ======
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== Gemini ======
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
else:
    model = None

def ai_generate(prompt: str) -> str:
    if not model:
        return "⚠️ الذكاء الاصطناعي غير مفعّل"
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"خطأ: {str(e)}"

# ====== الأقسام ======
SECTIONS = {
    "writing": {
        "name": "✍️ كتابة محتوى",
        "prompt": "أنت كاتب محتوى محترف. اكتب المحتوى التالي بالعربية بأسلوب جذاب واحترافي:\n\n{text}"
    },
    "translation": {
        "name": "🌐 ترجمة",
        "prompt": "ترجم النص التالي ترجمة احترافية دقيقة (لو إنجليزي → عربي، ولو عربي → إنجليزي):\n\n{text}"
    },
    "design": {
        "name": "🎨 وصف تصميم",
        "prompt": "أنت مصمم محترف. اكتب وصفًا تفصيليًا احترافيًا واحترافيًا لـ:\n\n{text}"
    },
    "analysis": {
        "name": "📊 تحليل",
        "prompt": "أنت محلل بيانات محترف. حلّل التالي وقدّم رؤى واستنتاجات واضحة:\n\n{text}"
    },
    "research": {
        "name": "🔍 بحث",
        "prompt": "أنت باحث محترف. قدّم معلومات شاملة وموثوقة عن:\n\n{text}"
    },
    "summary": {
        "name": "📝 تلخيص",
        "prompt": "لخّص النص التالي في نقاط واضحة ومختصرة:\n\n{text}"
    },
    "email": {
        "name": "📧 إيميل",
        "prompt": "اكتب إيميل احترافي بالعربية بناءً على:\n\n{text}"
    },
    "social": {
        "name": "📱 سوشيال ميديا",
        "prompt": "اكتب منشور جذاب للسوشيال ميديا عن:\n\n{text}"
    },
    "code": {
        "name": "💻 كود",
        "prompt": "أنت مبرمج محترف. اكتب كودًا نظيفًا وموثقًا لـ:\n\n{text}"
    },
}

user_state = {}
user_history = {}

# ====== أوامر البوت ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = None

    name = update.effective_user.first_name or "صديقي"
    welcome = (
        f"👋 أهلًا {name}!\n\n"
        f"أنا *Muhannad AI* — وكيلك الذكي المتعدد الأقسام 🤖\n\n"
        f"اختر القسم اللي عايز تشتغل فيه:"
    )

    keyboard = [
        [InlineKeyboardButton(SECTIONS["writing"]["name"], callback_data="section_writing"),
         InlineKeyboardButton(SECTIONS["translation"]["name"], callback_data="section_translation")],
        [InlineKeyboardButton(SECTIONS["design"]["name"], callback_data="section_design"),
         InlineKeyboardButton(SECTIONS["analysis"]["name"], callback_data="section_analysis")],
        [InlineKeyboardButton(SECTIONS["research"]["name"], callback_data="section_research"),
         InlineKeyboardButton(SECTIONS["summary"]["name"], callback_data="section_summary")],
        [InlineKeyboardButton(SECTIONS["email"]["name"], callback_data="section_email"),
         InlineKeyboardButton(SECTIONS["social"]["name"], callback_data="section_social")],
        [InlineKeyboardButton(SECTIONS["code"]["name"], callback_data="section_code")],
        [InlineKeyboardButton("📋 سجل العمليات", callback_data="history"),
         InlineKeyboardButton("ℹ️ عن البوت", callback_data="about")],
    ]

    await update.message.reply_text(
        welcome,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *كيف تستخدم البوت:*\n\n"
        "1️⃣ اضغط /start لعرض الأقسام\n"
        "2️⃣ اختر القسم (كتابة، ترجمة، ...)\n"
        "3️⃣ اكتب المهمة اللي عايزها\n"
        "4️⃣ البوت هيردلك بالنتيجة\n\n"
        "🔹 الأوامر المتاحة:\n"
        "/start — القائمة الرئيسية\n"
        "/help — هذه الرسالة\n"
        "/cancel — إلغاء العملية الحالية\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = None
    await update.message.reply_text("✅ تم الإلغاء. اضغط /start للبدء من جديد.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("section_"):
        section_key = data.replace("section_", "")
        if section_key in SECTIONS:
            user_state[user_id] = section_key
            section = SECTIONS[section_key]
            msg = (
                f"{section['name']}\n\n"
                f"✏️ اكتب المهمة اللي عايزها، وأنا هنفذها لك.\n\n"
                f"مثال: اكتبلي وصف منتج لمقهى"
            )
            await query.edit_message_text(msg)

    elif data == "history":
        history = user_history.get(user_id, [])
        if not history:
            await query.edit_message_text("📋 مفيش عمليات سابقة.")
        else:
            text = "📋 *آخر عملياتك:*\n\n"
            for i, h in enumerate(history[-5:], 1):
                text += f"{i}. {h['section']} — {h['time']}\n"
            await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "about":
        text = (
            "🤖 *Muhannad AI Worker Agent*\n\n"
            "وكيل ذكي متعدد الأقسام مدعوم بـ Google Gemini.\n\n"
            "✨ يقدر يشتغل في:\n"
            "• كتابة المحتوى\n"
            "• الترجمة\n"
            "• وصف التصاميم\n"
            "• تحليل البيانات\n"
            "• البحث\n"
            "• التلخيص\n"
            "• الإيميلات\n"
            "• السوشيال ميديا\n"
            "• الكود\n\n"
            "الإصدار: 1.0"
        )
        await query.edit_message_text(text, parse_mode="Markdown")

    elif data == "back":
        await start_from_callback(query)

async def start_from_callback(query):
    keyboard = [
        [InlineKeyboardButton(SECTIONS["writing"]["name"], callback_data="section_writing"),
         InlineKeyboardButton(SECTIONS["translation"]["name"], callback_data="section_translation")],
        [InlineKeyboardButton(SECTIONS["design"]["name"], callback_data="section_design"),
         InlineKeyboardButton(SECTIONS["analysis"]["name"], callback_data="section_analysis")],
        [InlineKeyboardButton(SECTIONS["research"]["name"], callback_data="section_research"),
         InlineKeyboardButton(SECTIONS["summary"]["name"], callback_data="section_summary")],
        [InlineKeyboardButton(SECTIONS["email"]["name"], callback_data="section_email"),
         InlineKeyboardButton(SECTIONS["social"]["name"], callback_data="section_social")],
        [InlineKeyboardButton(SECTIONS["code"]["name"], callback_data="section_code")],
        [InlineKeyboardButton("📋 سجل العمليات", callback_data="history"),
         InlineKeyboardButton("ℹ️ عن البوت", callback_data="about")],
    ]
    await query.edit_message_text(
        "🤖 اختر القسم اللي عايز تشتغل فيه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    section_key = user_state.get(user_id)

    if not section_key:
        await update.message.reply_text(
            "⚠️ اختر قسم أول من /start"
        )
        return

    section = SECTIONS[section_key]

    # إشعار "جاري التنفيذ"
    thinking_msg = await update.message.reply_text(
        f"⏳ جاري التنفيذ في {section['name']}...\n\n"
        f"قد يأخذ 5-10 ثواني"
    )

    prompt = section["prompt"].format(text=text)
    result = ai_generate(prompt)

    # حفظ في السجل
    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append({
        "section": section["name"],
        "time": datetime.now().strftime("%H:%M"),
        "input": text[:50]
    })

    # إرسال النتيجة (تقسيم لو طويلة)
    header = f"✅ *نتيجة {section['name']}*\n\n"
    full_msg = header + result

    # Telegram حد أقصى 4096 حرف
    if len(full_msg) <= 4000:
        await thinking_msg.edit_text(full_msg, parse_mode="Markdown")
    else:
        await thinking_msg.edit_text(header, parse_mode="Markdown")
        for i in range(0, len(result), 4000):
            await update.message.reply_text(result[i:i+4000])

    # أزرار ما بعد النتيجة
    keyboard = [
        [InlineKeyboardButton("🔄 مهمة تانية", callback_data=f"section_{section_key}"),
         InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back")],
    ]
    await update.message.reply_text(
        "اختر الخطوة التالية:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ====== التشغيل ======
def main():
    if not TELEGRAM_TOKEN:
        print("❌ خطأ: TELEGRAM_TOKEN مش موجود في Environment Variables")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 البوت شغال...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
