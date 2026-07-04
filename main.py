"""Local analysis demo: prints stats over the collected weather data.

Data collection itself is handled by the WeatherScheduler inside the API
(see apis.py / scheduler.py). Run `python fetch_weather.py` for a one-off
manual collection.
"""

import asyncio

from analyse import Analyse
from config import settings
from data_json_manager import JSONDataManager
from data_type_convertor import WeatherDataConverter


async def main():
    data_manager = JSONDataManager(settings.data_file)
    analyse = Analyse(json_manager=data_manager)

    summary = await analyse.get_weather_summary(period=24)
    if summary is None:
        print("No data available yet. Start the API or run `python fetch_weather.py` first.")
        return

    print("Weather summary (last 24 records):")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    converter = WeatherDataConverter(await data_manager.read_data())
    df = converter.to_dataframe()
    if df is not None:
        print("\nMost recent records:")
        print(df.tail())


if __name__ == "__main__":
    asyncio.run(main())
