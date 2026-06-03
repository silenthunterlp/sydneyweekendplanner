import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sydney_planner.agent.core import PlannerAgent
from sydney_planner.config import get_settings

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent.parent.parent / "static"


def build_web_app(agent: PlannerAgent) -> FastAPI:
    app = FastAPI(
        title="Sydney Weekend Planner",
        description="AI-powered Sydney weekend planning agent",
        version="1.0.0",
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/health")
    async def health():
        settings = get_settings()
        api_key_ok = bool(
            settings.anthropic_api_key
            and settings.anthropic_api_key != "sk-ant-..."
            and len(settings.anthropic_api_key) > 20
        )
        channels = {
            "web": True,
            "whatsapp": bool(settings.twilio_account_sid and settings.twilio_account_sid != "AC..."),
            "telegram": bool(settings.telegram_bot_token and settings.telegram_bot_token != "..."),
        }
        status = "ok" if api_key_ok else "degraded"
        return JSONResponse(
            status_code=200 if api_key_ok else 503,
            content={
                "status": status,
                "model": settings.claude_model,
                "anthropic_api_key": "configured" if api_key_ok else "missing",
                "channels": {k: "active" if v else "not configured" for k, v in channels.items()},
            },
        )

    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        await websocket.accept()
        user_id = f"web:{session_id}"
        logger.info("WebSocket connected: %s", user_id)
        try:
            while True:
                message = await websocket.receive_text()
                if not message.strip():
                    continue
                reply = await agent.chat(user_id, message, "web")
                await websocket.send_text(reply)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: %s", user_id)

    return app
