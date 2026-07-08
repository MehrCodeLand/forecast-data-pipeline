import asyncio
from typing import Dict

import httpx
from loguru import logger

from config import settings
from data_json_manager import JSONDataManager

logger.add('logs/fetch.txt', rotation="1 week")


async def fetch_current_weather(lat: float, lon: float) -> Dict:
    """Fetch the current weather block from the Open-Meteo API."""
    params = {"latitude": lat, "longitude": lon, "current_weather": "true"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.api_url, params=params)
            response.raise_for_status()
            return response.json()["current_weather"]
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
