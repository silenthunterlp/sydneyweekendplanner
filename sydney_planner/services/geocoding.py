import httpx


class GeocodingService:
    BASE_URL = "https://nominatim.openstreetmap.org/search"
    _cache: dict[str, tuple[float, float]] = {}

    async def suburb_to_coords(self, suburb: str) -> tuple[float, float]:
        key = suburb.lower().strip()
        if key in self._cache:
            return self._cache[key]

        query = f"{suburb}, Sydney, NSW, Australia"
        async with httpx.AsyncClient(headers={"User-Agent": "SydneyPlannerBot/1.0"}) as client:
            resp = await client.get(
                self.BASE_URL,
                params={"q": query, "format": "json", "limit": 1},
            )
            resp.raise_for_status()

        results = resp.json()
        if not results:
            # Fall back to Sydney CBD
            return (-33.8688, 151.2093)

        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
        self._cache[key] = (lat, lon)
        return (lat, lon)
