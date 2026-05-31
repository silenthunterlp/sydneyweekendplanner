import httpx

# WMO weather interpretation codes → human description
_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


class WeatherService:
    SYDNEY_LAT = -33.8688
    SYDNEY_LON = 151.2093
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    async def get_forecast(self, start_date: str, end_date: str) -> dict:
        """Returns per-day weather data for Sydney between start_date and end_date."""
        params = {
            "latitude": self.SYDNEY_LAT,
            "longitude": self.SYDNEY_LON,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "weathercode",
                "uv_index_max",
            ],
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "Australia/Sydney",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
        return self._parse(resp.json())

    def _parse(self, data: dict) -> dict:
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        days = []
        for i, date in enumerate(dates):
            code = daily.get("weathercode", [])[i] if daily.get("weathercode") else 0
            days.append({
                "date": date,
                "max_temp_c": daily.get("temperature_2m_max", [])[i],
                "min_temp_c": daily.get("temperature_2m_min", [])[i],
                "precipitation_mm": daily.get("precipitation_sum", [])[i],
                "precipitation_probability_pct": daily.get("precipitation_probability_max", [])[i],
                "weather_description": _WMO_CODES.get(code, "Unknown"),
                "uv_index_max": daily.get("uv_index_max", [])[i],
            })
        return {"days": days}
