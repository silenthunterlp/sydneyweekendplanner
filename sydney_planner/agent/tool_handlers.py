import json
from typing import Any

from sydney_planner.memory.repository import UserPreferencesRepository
from sydney_planner.services.events import EventsService
from sydney_planner.services.transport import TransportService
from sydney_planner.services.weather import WeatherService


class ToolHandlers:
    def __init__(
        self,
        weather_svc: WeatherService,
        events_svc: EventsService,
        transport_svc: TransportService,
        repo: UserPreferencesRepository,
    ) -> None:
        self._weather = weather_svc
        self._events = events_svc
        self._transport = transport_svc
        self._repo = repo
        self._dispatch_map = {
            "get_weather": self._get_weather,
            "search_events": self._search_events,
            "get_transport_options": self._get_transport_options,
            "get_user_preferences": self._get_user_preferences,
            "save_user_preferences": self._save_user_preferences,
        }

    async def dispatch(self, tool_name: str, inputs: dict, user_id: str) -> Any:
        handler = self._dispatch_map.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name!r}"}
        try:
            return await handler(inputs, user_id)
        except Exception as exc:
            return {"error": str(exc)}

    async def _get_weather(self, inputs: dict, user_id: str) -> dict:
        return await self._weather.get_forecast(inputs["start_date"], inputs["end_date"])

    async def _search_events(self, inputs: dict, user_id: str) -> list:
        return await self._events.search(
            start_date=inputs["start_date"],
            end_date=inputs["end_date"],
            category=inputs.get("category", "any"),
            suburb=inputs.get("suburb", "any"),
            max_price=inputs.get("max_price_aud"),
        )

    async def _get_transport_options(self, inputs: dict, user_id: str) -> dict:
        return await self._transport.get_journey(
            origin=inputs["origin_suburb"],
            destination=inputs["destination_suburb"],
            departure_dt=inputs["departure_datetime"],
        )

    async def _get_user_preferences(self, inputs: dict, user_id: str) -> dict:
        prefs = await self._repo.get_or_create(user_id, channel="unknown")
        return prefs.to_dict()

    async def _save_user_preferences(self, inputs: dict, user_id: str) -> dict:
        await self._repo.update(user_id, inputs["preferences"])
        return {"status": "saved", "updated_fields": list(inputs["preferences"].keys())}
