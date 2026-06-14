"""
Production ASGI entry point for Render.
Start command: uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*' --ws websockets
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sydney_planner")

STATIC_DIR = Path(__file__).parent / "static"

# Global agent reference — set during lifespan startup
_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent

    from sydney_planner.agent.core import PlannerAgent
    from sydney_planner.agent.tool_handlers import ToolHandlers
    from sydney_planner.config import get_settings
    from sydney_planner.memory.repository import UserPreferencesRepository
    from sydney_planner.memory.session import create_engine_and_tables
    from sydney_planner.services.events import EventsService
    from sydney_planner.services.transport import TransportService
    from sydney_planner.services.weather import WeatherService

    settings = get_settings()
    logger.info("Starting Sydney Weekend Planner (model=%s)", settings.claude_model)

    engine = await create_engine_and_tables(settings.database_url)
    repo = UserPreferencesRepository(engine)

    handlers = ToolHandlers(
        weather_svc=WeatherService(),
        events_svc=EventsService(settings),
        transport_svc=TransportService(settings),
        repo=repo,
    )

    try:
        _agent = PlannerAgent(repo=repo, tool_handlers=handlers)
        logger.info("PlannerAgent ready")
    except ValueError as exc:
        logger.error("Agent config error: %s", exc)

        class _StubAgent:
            async def chat(self, user_id, message, channel):
                return (
                    "The planner isn't configured yet.\n\n"
                    "Please set ANTHROPIC_API_KEY in Render environment variables."
                )
        _agent = _StubAgent()

    # Start Telegram polling
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if tg_token and len(tg_token) > 10:
        from sydney_planner.channels.telegram import build_telegram_app
        tg_app = build_telegram_app(tg_token, _agent)
        await tg_app.initialize()
        await tg_app.start()
        await tg_app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot polling started")

    logger.info("Sydney Weekend Planner ready")
    yield

    await engine.dispose()
    logger.info("Shutdown complete")


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Sydney Weekend Planner",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files (CSS, images, etc.) — chat.js served as explicit route below
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/static/chat.js")
async def chat_js():
    """Serve chat.js via Python route so it always deploys with the app."""
    js = (STATIC_DIR / "chat.js").read_text(encoding="utf-8")
    return Response(content=js, media_type="application/javascript")


@app.get("/health")
async def health():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")

    api_ok = bool(api_key and len(api_key) > 20)
    tg_ok = bool(tg_token and len(tg_token) > 10)
    wa_ok = bool(twilio_sid and twilio_sid not in ("", "AC...") and len(twilio_sid) > 10)

    return JSONResponse(
        status_code=200 if api_ok else 503,
        content={
            "status": "ok" if api_ok else "degraded",
            "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
            "anthropic_api_key": "configured" if api_ok else "missing",
            "channels": {
                "web": "active",
                "whatsapp": "active" if wa_ok else "not configured",
                "telegram": "active" if tg_ok else "not configured",
            },
            "debug": {
                "telegram_token_length": len(tg_token),
                "telegram_token_preview": tg_token[:8] + "..." if tg_token else "empty",
            },
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
            if not message.strip() or message == "__ping__":
                continue
            if _agent is None:
                await websocket.send_text("Server is still starting up, please wait a moment.")
                continue
            reply = await _agent.chat(user_id, message, "web")
            await websocket.send_text(reply)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", user_id)


# WhatsApp webhook
from fastapi import Request
from fastapi.responses import Response as _Response

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    from sydney_planner.config import get_settings
    from sydney_planner.utils.formatting import markdown_to_whatsapp
    settings = get_settings()

    form = await request.form()
    if settings.twilio_auth_token and settings.twilio_auth_token not in ("", "..."):
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(settings.twilio_auth_token)
        if not validator.validate(str(request.url), dict(form), request.headers.get("X-Twilio-Signature", "")):
            return _Response(content="Forbidden", status_code=403)

    from_number = form.get("From", "")
    body = form.get("Body", "").strip()
    if not body or _agent is None:
        return _Response(content="", media_type="text/plain")

    user_id = f"whatsapp:{from_number}"
    reply = await _agent.chat(user_id, body, "whatsapp")

    from twilio.twiml.messaging_response import MessagingResponse
    twiml = MessagingResponse()
    twiml.message(markdown_to_whatsapp(reply))
    return _Response(content=str(twiml), media_type="application/xml")
