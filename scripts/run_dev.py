"""
Development entry point. Starts:
  - FastAPI/uvicorn on WEB_PORT (serves web UI + WhatsApp webhook)
  - Telegram polling in background (if TELEGRAM_BOT_TOKEN is set)
"""
import asyncio
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn

from sydney_planner.agent.core import PlannerAgent
from sydney_planner.agent.tool_handlers import ToolHandlers
from sydney_planner.channels.web import build_web_app
from sydney_planner.channels.whatsapp import register_whatsapp_routes
from sydney_planner.config import get_settings
from sydney_planner.memory.repository import UserPreferencesRepository
from sydney_planner.memory.session import create_engine_and_tables
from sydney_planner.services.events import EventsService
from sydney_planner.services.transport import TransportService
from sydney_planner.services.weather import WeatherService


async def main() -> None:
    settings = get_settings()

    engine = await create_engine_and_tables(settings.database_url)
    repo = UserPreferencesRepository(engine)

    handlers = ToolHandlers(
        weather_svc=WeatherService(),
        events_svc=EventsService(settings),
        transport_svc=TransportService(settings),
        repo=repo,
    )
    agent = PlannerAgent(repo=repo, tool_handlers=handlers)

    # Build FastAPI app (web UI + WhatsApp webhook on same port)
    app = build_web_app(agent)
    register_whatsapp_routes(app, agent)

    # Start Telegram polling in background if token is configured
    if settings.telegram_bot_token:
        from sydney_planner.channels.telegram import build_telegram_app
        tg_app = build_telegram_app(settings.telegram_bot_token, agent)
        asyncio.create_task(tg_app.run_polling())
        print("Telegram bot polling started.")
    else:
        print("TELEGRAM_BOT_TOKEN not set — Telegram channel disabled.")

    if not settings.twilio_account_sid:
        print("TWILIO_ACCOUNT_SID not set — WhatsApp channel disabled (webhook still available).")

    print(f"Web UI: http://localhost:{settings.web_port}")
    print("For WhatsApp: expose with 'ngrok http 8000' and set webhook to /webhook/whatsapp")

    config = uvicorn.Config(app, host=settings.web_host, port=settings.web_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
