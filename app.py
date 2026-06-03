"""
Production ASGI entry point for Render (and any other platform).

Render runs:  uvicorn app:app --host 0.0.0.0 --port $PORT
Local dev:    python scripts/run_dev.py
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sydney_planner.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sydney_planner")


def _is_configured(val: str, placeholder: str = "") -> bool:
    return bool(val and val != placeholder and len(val) > 4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all services when the server starts."""
    from sydney_planner.agent.core import PlannerAgent
    from sydney_planner.agent.tool_handlers import ToolHandlers
    from sydney_planner.channels.web import build_web_app
    from sydney_planner.channels.whatsapp import register_whatsapp_routes
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
        agent = PlannerAgent(repo=repo, tool_handlers=handlers)
    except ValueError as exc:
        logger.error("Agent config error: %s", exc)
        # Stub agent — returns helpful error until key is set
        agent = object.__new__(PlannerAgent)
        agent._repo = repo

        async def _stub(user_id, message, channel):
            return (
                "The planner isn't configured yet.\n\n"
                "Please set ANTHROPIC_API_KEY in Render environment variables."
            )
        agent.chat = _stub

    # Mount routes onto this app instance
    from sydney_planner.channels.web import STATIC_DIR
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi import WebSocket, WebSocketDisconnect

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(STATIC_DIR / "index.html"))

    @app.get("/health")
    async def health():
        api_ok = _is_configured(settings.anthropic_api_key, "sk-ant-...")
        return JSONResponse(
            status_code=200 if api_ok else 503,
            content={
                "status": "ok" if api_ok else "degraded",
                "model": settings.claude_model,
                "anthropic_api_key": "configured" if api_ok else "missing",
                "channels": {
                    "web": "active",
                    "whatsapp": "active" if _is_configured(settings.twilio_account_sid, "AC...") else "not configured",
                    "telegram": "active" if _is_configured(settings.telegram_bot_token, "...") else "not configured",
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
                if not message.strip():
                    continue
                reply = await agent.chat(user_id, message, "web")
                await websocket.send_text(reply)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected: %s", user_id)

    # WhatsApp webhook
    from sydney_planner.channels.whatsapp import register_whatsapp_routes
    register_whatsapp_routes(app, agent)

    # Telegram polling (background)
    if _is_configured(settings.telegram_bot_token, "..."):
        from sydney_planner.channels.telegram import build_telegram_app
        tg_app = build_telegram_app(settings.telegram_bot_token, agent)
        asyncio.create_task(tg_app.run_polling())
        logger.info("Telegram bot polling started")

    logger.info("Sydney Weekend Planner ready")
    yield
    # Cleanup on shutdown
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Sydney Weekend Planner",
    description="AI-powered Sydney weekend planning agent",
    version="1.0.0",
    lifespan=lifespan,
)
