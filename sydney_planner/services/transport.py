from typing import Optional

import httpx

from sydney_planner.config import Settings
from sydney_planner.services.geocoding import GeocodingService


class TransportService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._geocoder = GeocodingService()

    async def get_journey(
        self,
        origin: str,
        destination: str,
        departure_dt: str,
    ) -> dict:
        """
        Returns journey options between two Sydney suburbs.
        Falls back to a helpful message if the TfNSW API key is not configured.
        """
        if not self._settings.tfnsw_api_key:
            return self._google_maps_fallback(origin, destination)

        try:
            origin_coords = await self._geocoder.suburb_to_coords(origin)
            dest_coords = await self._geocoder.suburb_to_coords(destination)
            return await self._tfnsw_trip(origin_coords, dest_coords, departure_dt, origin, destination)
        except Exception:
            return self._google_maps_fallback(origin, destination)

    async def _tfnsw_trip(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        departure_dt: str,
        origin_name: str,
        dest_name: str,
    ) -> dict:
        # TfNSW Trip Planner API uses coordinate-based requests
        params = {
            "outputFormat": "rapidJSON",
            "coordOutputFormat": "EPSG:4326",
            "depArrMacro": "dep",
            "itdDate": departure_dt[:10].replace("-", ""),
            "itdTime": departure_dt[11:16].replace(":", "") if len(departure_dt) > 10 else "0900",
            "type_origin": "coord",
            "name_origin": f"{origin[1]}:{origin[0]}:EPSG:4326",
            "type_destination": "coord",
            "name_destination": f"{destination[1]}:{destination[0]}:EPSG:4326",
            "calcNumberOfTrips": 3,
        }
        headers = {"Authorization": f"apikey {self._settings.tfnsw_api_key}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._settings.tfnsw_base_url}/trip",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()

        return self._parse_trip(resp.json(), origin_name, dest_name)

    def _parse_trip(self, data: dict, origin: str, destination: str) -> dict:
        journeys = []
        for journey in (data.get("journeys") or [])[:3]:
            legs = journey.get("legs") or []
            total_mins = sum(
                int(leg.get("duration", 0)) // 60 for leg in legs
            )
            modes = [leg.get("transportation", {}).get("product", {}).get("name", "") for leg in legs]
            journeys.append({
                "duration_minutes": total_mins,
                "modes": [m for m in modes if m],
                "legs_count": len(legs),
            })

        # Opal adult fare estimate: base $3.61 + distance component (simplified)
        fare_estimate = 3.61

        return {
            "origin": origin,
            "destination": destination,
            "journeys": journeys,
            "fare_aud": fare_estimate,
            "note": "Opal adult fare estimate. Tap on/off with Opal card for exact fare.",
        }

    def _google_maps_fallback(self, origin: str, destination: str) -> dict:
        return {
            "origin": origin,
            "destination": destination,
            "journeys": [],
            "fare_aud": None,
            "note": f"Search Google Maps or transportnsw.info for directions from {origin} to {destination}.",
        }
