from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI(title="Muhannad AI Worker Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = {
    "name": "Muhannad AI",
    "status": "running",
    "skills": ["writing", "translation", "summarization", "data_entry"],
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

@app.get("/api/health")
def health():
    return {"ok": True, "service": "Muhannad AI Worker Agent"}

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
        reason = "المهمة مناسبة للنسخة التجريبية"

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

    # تنفيذ تجريبي فقط؛ لا توجد منصة خارجية في هذه النسخة.
    if task["category"] == "writing":
        result = "وصف تجريبي: منتج عملي بجودة ممتازة وتصميم أنيق، مناسب للاستخدام اليومي ويجمع بين البساطة والفائدة."
    elif task["category"] == "translation":
        result = "ترجمة تجريبية جاهزة للمراجعة والتسليم."
    else:
        result = "نتيجة تجريبية جاهزة للمراجعة."

    task["status"] = "review"
    add_log(f"تم تنفيذ المهمة #{task['id']} وأصبحت بانتظار المراجعة")
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
