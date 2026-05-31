import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sydney_planner.agent.core import PlannerAgent

STATIC_DIR = Path(__file__).parent.parent.parent / "static"


def build_web_app(agent: PlannerAgent) -> FastAPI:
    app = FastAPI(title="Sydney Weekend Planner")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        await websocket.accept()
        user_id = f"web:{session_id}"
        try:
            while True:
                message = await websocket.receive_text()
                if not message.strip():
                    continue
                reply = await agent.chat(user_id, message, "web")
                await websocket.send_text(reply)
        except WebSocketDisconnect:
            pass

    return app
