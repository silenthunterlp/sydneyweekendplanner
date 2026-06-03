"""
Development entry point. Starts:
  - FastAPI/uvicorn on WEB_PORT (web UI + WhatsApp webhook)
  - Telegram polling in background (if TELEGRAM_BOT_TOKEN is set)
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("sydney_planner")

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


def _check(val: str, placeholder: str) -> bool:
    return bool(val and val != placeholder and len(val) > 4)


def print_banner(settings) -> None:
    api_ok   = _check(settings.anthropic_api_key, "sk-ant-...")
    wa_ok    = _check(settings.twilio_account_sid, "AC...")
    tg_ok    = _check(settings.telegram_bot_token, "...")
    eb_ok    = _check(settings.eventbrite_api_key, "")
    tf_ok    = _check(settings.tfnsw_api_key, "...")

    def icon(ok): return "✅" if ok else "⚠️ "

    sep = "=" * 52
    print(f"\n{sep}")
    print("  Sydney Weekend Planner -- Dev Server")
    print(sep)
    print(f"  {icon(api_ok)} Anthropic API key   {'configured' if api_ok else 'NOT SET — agent will not respond'}")
    print()
    print("  Channels:")
    print(f"    {icon(True)}  Web chat      → http://localhost:{settings.web_port}")
    print(f"    {icon(wa_ok)}  WhatsApp      → {'active (POST /webhook/whatsapp)' if wa_ok else 'not configured (set TWILIO_* in .env)'}")
    print(f"    {icon(tg_ok)}  Telegram      → {'polling active' if tg_ok else 'not configured (set TELEGRAM_BOT_TOKEN in .env)'}")
    print()
    print("  External services:")
    print(f"    ✅  Open-Meteo weather  (always free)")
    print(f"    ✅  Nominatim geocoding (always free)")
    print(f"    {icon(eb_ok)}  Eventbrite events  {'configured' if eb_ok else '→ using RSS fallback'}")
    print(f"    {icon(tf_ok)}  TfNSW transport    {'configured' if tf_ok else '→ using Maps hint fallback'}")
    print()
    if not api_ok:
        print("  ⚠️  Add ANTHROPIC_API_KEY to .env to enable the agent.")
        print()
    print("  Health check: http://localhost:{}/health".format(settings.web_port))
    print("  Stop: Ctrl+C")
    print(sep + "\n")


async def main() -> None:
    settings = get_settings()
    print_banner(settings)

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
        logger.error("%s", exc)
        logger.error("Server will start but the agent will return error messages until the key is set.")
        # Create a stub agent that returns a helpful error for all messages
        from sydney_planner.agent.core import PlannerAgent as _PA
        agent = object.__new__(_PA)
        agent._repo = repo

        async def _stub_chat(user_id, message, channel):
            return (
                "⚠️ The planner isn't configured yet.\n\n"
                "Please add your `ANTHROPIC_API_KEY` to `.env` and restart the server.\n"
                "Get a key at: https://console.anthropic.com"
            )
        agent.chat = _stub_chat

    app = build_web_app(agent)
    register_whatsapp_routes(app, agent)

    if settings.telegram_bot_token and _check(settings.telegram_bot_token, "..."):
        from sydney_planner.channels.telegram import build_telegram_app
        tg_app = build_telegram_app(settings.telegram_bot_token, agent)
        asyncio.create_task(tg_app.run_polling())
        logger.info("Telegram bot polling started")

    config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="warning",  # suppress uvicorn's own INFO noise; our banner covers it
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
