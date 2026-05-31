import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from sydney_planner.memory.models import Base
from sydney_planner.memory.repository import UserPreferencesRepository

SAMPLE_WEATHER = {
    "daily": {
        "time": ["2026-05-30", "2026-05-31"],
        "temperature_2m_max": [22.0, 19.0],
        "temperature_2m_min": [14.0, 12.0],
        "precipitation_sum": [0.0, 5.2],
        "precipitation_probability_max": [10, 75],
        "weathercode": [1, 61],
        "uv_index_max": [3.0, 1.5],
    }
}

SAMPLE_EVENTS = [
    {
        "name": "Surry Hills Festival",
        "venue": "Crown Street",
        "suburb": "Surry Hills",
        "start_datetime": "2026-05-30T10:00:00",
        "url": "https://example.com",
        "price_aud": 0,
    }
]


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def repo(test_engine):
    return UserPreferencesRepository(test_engine)
