import xml.etree.ElementTree as ET
from typing import Optional

import httpx

from sydney_planner.config import Settings

_EVENTBRITE_CATEGORY_MAP = {
    "music": "103",
    "arts": "105",
    "food": "110",
    "sports": "108",
    "family": "115",
    "outdoor": "109",
    "markets": "199",
    "nightlife": "113",
}

_DESTINATION_NSW_RSS = "https://www.sydney.com/feed"


class EventsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(
        self,
        start_date: str,
        end_date: str,
        category: str = "any",
        suburb: str = "any",
        max_price: Optional[float] = None,
    ) -> list[dict]:
        if self._settings.eventbrite_api_key:
            try:
                return await self._eventbrite_search(start_date, end_date, category, suburb, max_price)
            except Exception:
                pass
        return await self._rss_fallback(start_date, end_date)

    async def _eventbrite_search(
        self,
        start_date: str,
        end_date: str,
        category: str,
        suburb: str,
        max_price: Optional[float],
    ) -> list[dict]:
        params: dict = {
            "location.address": f"{suburb}, Sydney, NSW" if suburb != "any" else "Sydney, NSW",
            "location.within": "20km",
            "start_date.range_start": f"{start_date}T00:00:00",
            "start_date.range_end": f"{end_date}T23:59:59",
            "expand": "venue",
        }
        if category != "any" and category in _EVENTBRITE_CATEGORY_MAP:
            params["categories"] = _EVENTBRITE_CATEGORY_MAP[category]
        if max_price is not None and max_price == 0:
            params["price"] = "free"

        headers = {"Authorization": f"Bearer {self._settings.eventbrite_api_key}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.eventbriteapi.com/v3/events/search/",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()

        events = []
        for ev in resp.json().get("events", [])[:20]:
            venue = ev.get("venue") or {}
            address = venue.get("address") or {}
            events.append({
                "name": ev.get("name", {}).get("text", ""),
                "venue": venue.get("name", ""),
                "suburb": address.get("city", "Sydney"),
                "start_datetime": ev.get("start", {}).get("local", ""),
                "url": ev.get("url", ""),
                "price_aud": 0 if ev.get("is_free") else None,
            })
        return events

    async def _rss_fallback(self, start_date: str, end_date: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(_DESTINATION_NSW_RSS)
                resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            events = []
            for item in items[:20]:
                title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                events.append({
                    "name": title,
                    "venue": "Sydney",
                    "suburb": "Sydney",
                    "start_datetime": start_date,
                    "url": link,
                    "price_aud": None,
                })
            return events
        except Exception:
            return [{"name": "Check sydney.com for events", "venue": "", "suburb": "Sydney", "start_datetime": start_date, "url": "https://www.sydney.com/events", "price_aud": None}]
