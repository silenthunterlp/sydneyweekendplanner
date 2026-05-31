from unittest.mock import AsyncMock

import pytest

from sydney_planner.agent.tool_handlers import ToolHandlers


def make_handlers(repo=None):
    weather = AsyncMock()
    weather.get_forecast = AsyncMock(return_value={"days": []})
    events = AsyncMock()
    events.search = AsyncMock(return_value=[])
    transport = AsyncMock()
    transport.get_journey = AsyncMock(return_value={"journeys": [], "fare_aud": 3.61})
    if repo is None:
        repo = AsyncMock()
        repo.get_or_create = AsyncMock(return_value=AsyncMock(to_dict=lambda: {}))
        repo.update = AsyncMock(return_value=None)
    return ToolHandlers(weather, events, transport, repo)


@pytest.mark.asyncio
async def test_dispatch_get_weather():
    h = make_handlers()
    result = await h.dispatch("get_weather", {"start_date": "2026-05-30", "end_date": "2026-05-31"}, "web:u1")
    assert "days" in result


@pytest.mark.asyncio
async def test_dispatch_unknown_tool():
    h = make_handlers()
    result = await h.dispatch("nonexistent_tool", {}, "web:u1")
    assert "error" in result


@pytest.mark.asyncio
async def test_dispatch_save_preferences():
    h = make_handlers()
    result = await h.dispatch(
        "save_user_preferences",
        {"user_id": "web:u1", "preferences": {"home_suburb": "Manly"}},
        "web:u1",
    )
    assert result["status"] == "saved"
    assert "home_suburb" in result["updated_fields"]
