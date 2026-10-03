import os
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import google.generativeai as genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== Gemini مع اختيار موديل يعمل ======
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # ترتيب الموديلات من الأحدث للأقدم - بيختار أول واحد شغال
    MODEL_NAMES = [
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
    ]
    model = None
    for name in MODEL_NAMES:
        try:
            test_model = genai.GenerativeModel(name)
            test_model.generate_content("test")
            model = test_model
            logger.info(f"✅ استخدمنا الموديل: {name}")
            break
        except Exception as e:
            logger.warning(f"❌ الموديل {name} مش شغال: {e}")
            continue
    if model is None:
        logger.error("⚠️ مفيش موديل شغال!")
else:
    model = None


def ai_generate(prompt: str) -> str:
    if not model:
        return "⚠️ الذكاء الاصطناعي غير مفعّل"
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"خطأ في AI: {str(e)}"


SECTIONS = {
    "writing": {"name": "✍️ كتابة محتوى", "prompt": "أنت كاتب محتوى محترف. اكتب المحتوى التالي بالعربية بأسلوب جذاب واحترافي:\n\n{text}"},
    "translation": {"name": "🌐 ترجمة", "prompt": "ترجم النص التالي ترجمة احترافية دقيقة (لو إنجليزي → عربي، ولو عربي → إنجليزي):\n\n{text}"},
    "design": {"name": "🎨 وصف تصميم", "prompt": "أنت مصمم محترف. اكتب وصفًا تفصيليًا احترافيًا واحترافيًا لـ:\n\n{text}"},
    "analysis": {"name": "📊 تحليل", "prompt": "أنت محلل بيانات محترف. حلّل التالي وقدّم رؤى واستنتاجات واضحة:\n\n{text}"},
    "research": {"name": "🔍 بحث", "prompt": "أنت باحث محترف. قدّم معلومات شاملة وموثوقة عن:\n\n{text}"},
    "summary": {"name": "📝 تلخيص", "prompt": "لخّص النص التالي في نقاط واضحة ومختصرة:\n\n{text}"},
    "email": {"name": "📧 إيميل", "prompt": "اكتب إيميل احترافي بالعربية بناءً على:\n\n{text}"},
    "social": {"name": "📱 سوشيال ميديا", "prompt": "اكتب منشور جذاب للسوشيال ميديا عن:\n\n{text}"},
    "code": {"name": "💻 كود", "prompt": "أنت مبرمج محترف. اكتب كودًا نظيفًا وموثقًا لـ:\n\n{text}"},
}

user_state = {}
user_history = {}


# ====== Handlers ======
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
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *كيف تستخدم البوت:*\n\n"
        "1️⃣ اضغط /start\n"
        "2️⃣ اختر القسم\n"
        "3️⃣ اكتب المهمة\n"
        "4️⃣ استلم النتيجة\n\n"
        "/cancel — إلغاء"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_user.id] = None
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
            await query.edit_message_text(f"{section['name']}\n\n✏️ اكتب مهمتك:")

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
        await query.edit_message_text(
            "🤖 *Muhannad AI Worker*\n\n"
            "وكيل ذكي متعدد الأقسام مدعوم بـ Google Gemini.\n\n"
            "الإصدار: 2.0",
            parse_mode="Markdown"
        )

    elif data == "back":
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
        await query.edit_message_text("🤖 اختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    section_key = user_state.get(user_id)

    if not section_key:
        await update.message.reply_text("⚠️ اختر قسم أول من /start")
        return

    section = SECTIONS[section_key]
    thinking_msg = await update.message.reply_text("⏳ جاري التنفيذ...")

    prompt = section["prompt"].format(text=text)
    result = ai_generate(prompt)

    if user_id not in user_history:
        user_history[user_id] = []
    user_history[user_id].append({
        "section": section["name"],
        "time": datetime.now().strftime("%H:%M"),
        "input": text[:50]
    })

    header = f"✅ *نتيجة {section['name']}*\n\n"
    full_msg = header + result

    if len(full_msg) <= 4000:
        await thinking_msg.edit_text(full_msg, parse_mode="Markdown")
    else:
        await thinking_msg.edit_text(header, parse_mode="Markdown")
        for i in range(0, len(result), 4000):
            await update.message.reply_text(result[i:i+4000])

    keyboard = [[
        InlineKeyboardButton("🔄 مهمة تانية", callback_data=f"section_{section_key}"),
        InlineKeyboardButton("🏠 القائمة", callback_data="back")
    ]]
    await update.message.reply_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))


# ====== FastAPI App ======
application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("cancel", cancel))
application.add_handler(CallbackQueryHandler(button_click))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

api = FastAPI()


@api.get("/")
def root():
    return {"status": "bot is running", "service": "Muhannad AI Telegram Bot"}


@api.get("/api/health")
def health():
    return {"ok": True, "model": str(model) if model else "none"}


@api.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"ok": False, "error": str(e)}


@api.on_event("startup")
async def startup():
    await application.initialize()
    await application.start()
    webhook_url = os.getenv("WEBHOOK_URL", "")
    if webhook_url:
        try:
            await application.bot.set_webhook(url=f"{webhook_url}/webhook")
            logger.info(f"✅ Webhook set to {webhook_url}/webhook")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
    logger.info("🤖 Bot started")


@api.on_event("shutdown")
async def shutdown():
    await application.stop()
    await application.shutdown()
