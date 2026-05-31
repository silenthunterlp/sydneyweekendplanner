import httpx
import pytest
import respx

from sydney_planner.services.weather import WeatherService
from tests.conftest import SAMPLE_WEATHER


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_parses_response():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(200, json=SAMPLE_WEATHER)
    )
    svc = WeatherService()
    result = await svc.get_forecast("2026-05-30", "2026-05-31")

    assert "days" in result
    assert len(result["days"]) == 2
    day0 = result["days"][0]
    assert day0["date"] == "2026-05-30"
    assert day0["max_temp_c"] == 22.0
    assert day0["weather_description"] == "Mainly clear"
    assert day0["precipitation_probability_pct"] == 10


@pytest.mark.asyncio
@respx.mock
async def test_get_forecast_http_error():
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(500)
    )
    svc = WeatherService()
    with pytest.raises(httpx.HTTPStatusError):
        await svc.get_forecast("2026-05-30", "2026-05-31")
