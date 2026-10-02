from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

app = FastAPI(title="Muhannad AI Worker Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== Gemini AI ======
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY and GENAI_AVAILABLE:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None

def ai_generate(prompt: str) -> str:
    if not model:
        return "⚠️ الذكاء الاصطناعي غير مفعّل. تأكد من GEMINI_API_KEY و requirements.txt"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"خطأ في AI: {str(e)}"

# ====== State ======
agent = {
    "name": "Muhannad AI",
    "status": "running",
    "skills": ["writing", "translation", "summarization", "data_entry", "research", "data_analysis", "image_description"],
}

tasks = [
    {
        "id": 1,
        "title": "كتابة وصف منتج",
        "description": "اكتب وصفًا عربيًا مختصرًا وجذابًا لمنتج تجريبي.",
        "category": "writing",
        "reward": 3.00,
        "status": "available",
        "platform": "Demo Platform",
    },
    {
        "id": 2,
        "title": "ترجمة نص قصير",
        "description": "ترجمة فقرة قصيرة من الإنجليزية إلى العربية.",
        "category": "translation",
        "reward": 2.00,
        "status": "available",
        "platform": "Demo Platform",
    },
]

logs = [
    {"time": datetime.now().isoformat(timespec="seconds"), "message": "تم تشغيل Muhannad AI", "type": "system"}
]

class AgentToggle(BaseModel):
    status: str

class TaskExecute(BaseModel):
    task_id: int
    user_input: Optional[str] = None

def add_log(message, log_type="agent"):
    logs.insert(0, {
        "time": datetime.now().isoformat(timespec="seconds"),
        "message": message,
        "type": log_type
    })

# ====== Routes ======
@app.get("/api/health")
def health():
    return {"ok": True, "service": "Muhannad AI Worker Agent", "ai": "ready" if model else "missing key"}

@app.get("/api/agent")
def get_agent():
    return agent

@app.post("/api/agent/toggle")
def toggle_agent(body: AgentToggle):
    if body.status not in ("running", "paused"):
        return {"ok": False, "error": "invalid status"}
    agent["status"] = body.status
    add_log("تم تشغيل الوكيل" if body.status == "running" else "تم إيقاف الوكيل", "system")
    return agent

@app.get("/api/tasks")
def get_tasks():
    return {"tasks": tasks}

@app.post("/api/tasks/analyze")
def analyze_task(body: TaskExecute):
    task = next((t for t in tasks if t["id"] == body.task_id), None)
    if not task:
        return {"ok": False, "error": "task not found"}

    if task["category"] not in agent["skills"]:
        decision = "rejected"
        reason = "المهارة غير مفعلة"
    else:
        decision = "accepted"
        reason = "المهمة مناسبة وسيتم تنفيذها بالذكاء الاصطناعي"

    add_log(f"تم تحليل المهمة #{task['id']}: {decision}")
    return {
        "ok": True,
        "decision": decision,
        "reason": reason,
        "task": task
    }

@app.post("/api/tasks/execute")
def execute_task(body: TaskExecute):
    task = next((t for t in tasks if t["id"] == body.task_id), None)
    if not task:
        return {"ok": False, "error": "task not found"}

    if agent["status"] != "running":
        return {"ok": False, "error": "agent is paused"}

    prompts = {
        "writing": f"أنت كاتب محتوى محترف. نفّذ المهمة التالية بالعربية بأسلوب جذاب واحترافي:\n\n{task['description']}",
        "translation": f"ترجم النص التالي إلى العربية ترجمة احترافية:\n\n{task['description']}",
        "summarization": f"لخّص النص التالي في نقاط مختصرة:\n\n{task['description']}",
        "research": f"ابحث وقدّم معلومات شاملة وموثوقة عن:\n\n{task['description']}",
        "data_analysis": f"حلّل البيانات التالية وقدّم رؤى واستنتاجات:\n\n{task['description']}",
        "image_description": f"اكتب وصفًا تفصيليًا احترافيًا لـ:\n\n{task['description']}",
        "data_entry": f"نظّم وأدخل البيانات التالية بشكل مرتب:\n\n{task['description']}",
    }

    prompt = prompts.get(task["category"], f"نفّذ المهمة التالية:\n\n{task['description']}")

    if body.user_input:
        prompt += f"\n\nملاحظات إضافية من المستخدم: {body.user_input}"

    result = ai_generate(prompt)

    task["status"] = "review"
    task["result"] = result
    add_log(f"تم تنفيذ المهمة #{task['id']} بالذكاء الاصطناعي")
    return {
        "ok": True,
        "requires_approval": True,
        "result": result,
        "task": task
    }

@app.post("/api/tasks/approve")
def approve_task(body: TaskExecute):
    task = next((t for t in tasks if t["id"] == body.task_id), None)
    if not task:
        return {"ok": False, "error": "task not found"}

    if task["status"] != "review":
        return {"ok": False, "error": "task is not awaiting review"}

    task["status"] = "completed"
    add_log(f"تمت الموافقة على المهمة #{task['id']} — جاهزة للتسليم", "success")
    return {"ok": True, "task": task}

@app.get("/api/logs")
def get_logs():
    return {"logs": logs[:50]}

@app.get("/api/earnings")
def get_earnings():
    completed = sum(t["reward"] for t in tasks if t["status"] == "completed")
    review = sum(t["reward"] for t in tasks if t["status"] == "review")
    return {
        "total": completed,
        "pending": review,
        "currency": "USD"
    }

# ====== تقديم الواجهة ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/style.css")
def serve_css():
    return FileResponse(os.path.join(BASE_DIR, "style.css"))

@app.get("/app.js")
def serve_js():
    return FileResponse(os.path.join(BASE_DIR, "app.js"))
