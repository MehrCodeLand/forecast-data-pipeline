import requests
import asyncio
from loguru import logger
from data_json_manager import JSONDataManager

logger.add('logs/fetch.txt', rotation="1 week")


async def fetch_weather_data(lat: float, lon: float):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result["current_weather"]
    except requests.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        raise
    except KeyError as e:
        logger.error(f"Unexpected API response format: {e}")
        raise


async def main():
    try:
        logger.info("Starting weather data collection")
        lat, lon = 35.685017, 51.389693
        
        weather_data = await fetch_weather_data(lat, lon)
        data_manager = JSONDataManager('data/forecast_data_tehran.json')
        await data_manager.save_data(weather_data)
        
        logger.info("Weather data collection completed")
    except Exception as e:
        logger.error(f"Issues in main: {e}")


if __name__ == "__main__":
    asyncio.run(main())
