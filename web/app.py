"""
Zari Web UI — FastAPI server.

WebSocket orqali real-time chat va REST API endpoint'lar.
Pipeline text_queue/response_queue orqali integratsiya qilinadi.
"""

import uuid
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from core.config import settings
from core.logging import get_logger
from core.scheduler import add_task, list_tasks, remove_task
from web.schemas import ChatRequest, ChatResponse, StatusResponse, TaskCreateRequest

log = get_logger("zari.web")

app = FastAPI(title="Zari AI", version="0.1.0")


async def require_api_key(x_api_key: str | None = Header(None)) -> None:
    """web_api_key sozlangan bo'lsa — barcha /api/* so'rovlarni tekshiradi."""
    if settings.web_api_key and x_api_key != settings.web_api_key:
        raise HTTPException(status_code=401, detail="Noto'g'ri yoki yo'q API kaliti")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.web_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline = None
_templates_dir = Path(__file__).parent / "templates"


def set_pipeline(pipeline) -> None:
    global _pipeline
    _pipeline = pipeline


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    index = _templates_dir / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Zari AI</h1><p>Dashboard hali tayyor emas.</p>")


@app.get("/api/status", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
async def status():
    if _pipeline is None:
        return StatusResponse(status="offline", provider="none")
    return StatusResponse(
        status="online",
        provider=settings.llm_provider,
        session_id=_pipeline.memory.session_id,
        message_count=len(_pipeline.memory.get()),
    )


@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest):
    if _pipeline is None:
        return ChatResponse(response="Zari hali ishga tushmagan.", source="error")

    try:
        response = await _pipeline.ask(req.message, timeout=65)
        return ChatResponse(response=response)
    except TimeoutError:
        return ChatResponse(response="Javob vaqti tugadi. Iltimos, qaytadan urinib ko'ring.", source="timeout")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if settings.web_api_key and ws.query_params.get("token") != settings.web_api_key:
        await ws.close(code=4401)
        return

    await ws.accept()
    session_id = str(uuid.uuid4())[:8]
    log.info("WebSocket ulandi: %s", session_id)

    if _pipeline is None:
        await ws.send_text("Zari hali ishga tushmagan.")
        await ws.close()
        return

    try:
        while True:
            data = await ws.receive_text()
            log.info("[%s] Xabar: %s", session_id, data)

            try:
                response = await _pipeline.ask(data, timeout=65)
                await ws.send_text(response)
            except TimeoutError:
                await ws.send_text("Javob vaqti tugadi.")
    except WebSocketDisconnect:
        log.info("WebSocket uzildi: %s", session_id)


@app.get("/api/tasks", dependencies=[Depends(require_api_key)])
async def get_tasks():
    tasks = await list_tasks(active_only=False)
    return [
        {
            "id": t.id,
            "name": t.name,
            "message": t.message,
            "schedule_type": t.schedule_type,
            "schedule_value": t.schedule_value,
            "is_active": t.is_active,
            "next_run": t.next_run.isoformat() if t.next_run else None,
        }
        for t in tasks
    ]


@app.post("/api/tasks", dependencies=[Depends(require_api_key)])
async def create_task(req: TaskCreateRequest):
    task = await add_task(
        name=req.name,
        message=req.message,
        schedule_type=req.schedule_type,
        schedule_value=req.schedule_value,
    )
    return {"id": task.id, "status": "created"}


@app.delete("/api/tasks/{task_id}", dependencies=[Depends(require_api_key)])
async def delete_task(task_id: int):
    removed = await remove_task(task_id)
    return {"removed": removed}
