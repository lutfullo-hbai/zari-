"""
Zari Web UI — FastAPI server.

WebSocket orqali real-time chat va REST API endpoint'lar.
Pipeline text_queue/response_queue orqali integratsiya qilinadi.
"""

import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from core.config import settings
from core.logging import get_logger
from web.schemas import ChatRequest, ChatResponse, StatusResponse

log = get_logger("zari.web")

app = FastAPI(title="Zari AI", version="0.1.0")

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


@app.get("/api/status", response_model=StatusResponse)
async def status():
    if _pipeline is None:
        return StatusResponse(status="offline", provider="none")
    return StatusResponse(
        status="online",
        provider=settings.llm_provider,
        session_id=_pipeline.memory.session_id,
        message_count=len(_pipeline.memory.get()),
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if _pipeline is None:
        return ChatResponse(response="Zari hali ishga tushmagan.", source="error")

    await _pipeline.text_queue.put(req.message)

    try:
        response = await asyncio.wait_for(
            _pipeline.response_queue.get(),
            timeout=65,
        )
        return ChatResponse(response=response)
    except TimeoutError:
        return ChatResponse(response="Javob vaqti tugadi. Iltimos, qaytadan urinib ko'ring.", source="timeout")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
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

            await _pipeline.text_queue.put(data)

            try:
                response = await asyncio.wait_for(
                    _pipeline.response_queue.get(),
                    timeout=65,
                )
                await ws.send_text(response)
            except TimeoutError:
                await ws.send_text("Javob vaqti tugadi.")
    except WebSocketDisconnect:
        log.info("WebSocket uzildi: %s", session_id)
