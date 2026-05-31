"""Create tables and insert a sample user for manual testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sydney_planner.config import get_settings
from sydney_planner.memory.repository import UserPreferencesRepository
from sydney_planner.memory.session import create_engine_and_tables


async def main() -> None:
    settings = get_settings()
    engine = await create_engine_and_tables(settings.database_url)
    repo = UserPreferencesRepository(engine)

    prefs = await repo.get_or_create("web:test-user", "web")
    await repo.update("web:test-user", {
        "home_suburb": "Surry Hills",
        "budget_per_day_aud": 100,
        "interests": ["food", "music", "outdoor"],
        "group_type": "couple",
        "onboarding_complete": True,
    })
    print("Sample user seeded: web:test-user (Surry Hills, $100/day, couple)")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
