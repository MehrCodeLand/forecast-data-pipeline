import asyncio
from typing import Dict, Optional

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


async def collect_weather_snapshot(data_manager: Optional[JSONDataManager] = None) -> Dict:
    """Fetch one weather snapshot and append it to the data store."""
    data_manager = data_manager or JSONDataManager(settings.data_file)
    weather_data = await fetch_current_weather(settings.latitude, settings.longitude)
    await data_manager.save_data(weather_data)
    return weather_data


if __name__ == "__main__":
    asyncio.run(collect_weather_snapshot())
