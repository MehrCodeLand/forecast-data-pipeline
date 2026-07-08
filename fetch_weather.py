import asyncio
from typing import Dict

import httpx
from loguru import logger

from config import settings
from data_json_manager import JSONDataManager

logger.add('logs/fetch.txt', rotation="1 week")


# Extra "current" fields requested from Open-Meteo, mapped to the stable
# key names we store. Records collected before these were added simply lack
# the keys; every reader must treat them as optional.
EXTRA_FIELD_MAP = {
    "relative_humidity_2m": "humidity",
    "apparent_temperature": "apparent_temperature",
    "precipitation": "precipitation",
    "surface_pressure": "pressure",
}


async def fetch_current_weather(lat: float, lon: float) -> Dict:
    """Fetch the current weather from Open-Meteo.

    Returns the classic ``current_weather`` block (temperature, windspeed,
    winddirection, weathercode, is_day, time, interval) plus, when the API
    provides them, the extra fields in EXTRA_FIELD_MAP. Existing keys are
    never renamed, so old stored records remain fully compatible.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "current": ",".join(EXTRA_FIELD_MAP.keys()),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.api_url, params=params)
            response.raise_for_status()
            payload = response.json()
            snapshot = dict(payload["current_weather"])

            current = payload.get("current", {})
            for api_key, stored_key in EXTRA_FIELD_MAP.items():
                value = current.get(api_key)
                if value is not None:
                    snapshot[stored_key] = value

            return snapshot
    except httpx.HTTPError as e:
        logger.error(f"Error fetching weather data: {e}")
        raise
    except KeyError as e:
        logger.error(f"Unexpected API response format, missing key: {e}")
        raise


async def collect_weather_snapshot(lat: float, lon: float,
                                   data_manager: JSONDataManager) -> Dict:
    """Fetch one weather snapshot for a location and append it to its store."""
    weather_data = await fetch_current_weather(lat, lon)
    await data_manager.save_data(weather_data)
    return weather_data


async def _collect_all_once():
    from cities import city_store
    for city in city_store.enabled():
        try:
            await collect_weather_snapshot(
                city["latitude"], city["longitude"], city_store.data_manager(city))
            logger.info(f"Collected snapshot for {city['name']}")
        except Exception as e:
            logger.error(f"Collection failed for {city['name']}: {e}")


if __name__ == "__main__":
    asyncio.run(_collect_all_once())
