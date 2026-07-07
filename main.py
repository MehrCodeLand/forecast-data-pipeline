"""Local analysis demo: prints stats over the collected data of each city.

Data collection itself is handled by the WeatherScheduler inside the API
(see apis.py / scheduler.py). Run `python fetch_weather.py` for a one-off
manual collection of all enabled cities.
"""

import asyncio

from analyse import Analyse
from cities import city_store
from data_type_convertor import WeatherDataConverter


async def main():
    for city in city_store.enabled():
        data_manager = city_store.data_manager(city)
        analyse = Analyse(json_manager=data_manager)

        print(f"\n=== {city['name']}, {city['country']} ===")
        summary = await analyse.get_weather_summary(period=24)
        if summary is None:
            print("No data collected yet.")
            continue

        for key, value in summary.items():
            print(f"  {key}: {value}")

        converter = WeatherDataConverter(await data_manager.read_data())
        df = converter.to_dataframe()
        if df is not None:
            print("\nMost recent records:")
            print(df.tail())


if __name__ == "__main__":
    asyncio.run(main())
