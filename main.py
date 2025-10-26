import requests
import json
from loguru import logger
from typing import Any, Dict, List
from pathlib import Path
from data_json_manager import JSONDataManager

from analyse import Analyse
from data_type_convertor import WeatherDataConverter

logger.add('logs/tehran.txt', rotation="1 week")




async def fetch_weather_data(lat: float, lon: float) -> Dict[str, Any]:
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
        
        lat, lon = 35.4120, 51.2323
        

        # weather_data = await fetch_weather_data(lat, lon)
        

        data_manager = JSONDataManager('data/forecast_data_tehran.json')
        # await data_manager.save_data(weather_data)
        data = await data_manager.read_data()
        analyse = Analyse(json_manger=data_manager)

        avg_of_changes = await analyse.estimate_avg_of_rate_of_change(10)
        print(f" avg_of_changes : : : : : {avg_of_changes}")

        res = await analyse.get_avg(period=2)
        print(f"ressss : {res}")

        rate = await analyse.estimate_delta(hours=10)
        print(f"delta : {rate}")


        weather = WeatherDataConverter(await data_manager.read_data())
        df  = await weather.to_dataframe()
        print(df)


        res_wind = await analyse.get_avg_windspeed(period=5)
        print(f"winddd1 {res_wind}")

        res_wind2 = await analyse.get_wind_direction_variability(period=10)
        print(f"wind2222 : {res_wind2}")

        
        




        
        logger.info("Weather data collection completed")
        
    except Exception as e:
        logger.error(f"Issues in main: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())