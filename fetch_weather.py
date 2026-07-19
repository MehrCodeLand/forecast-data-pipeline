import asyncio
from datetime import datetime, timezone
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
    """Fetch one normalized weather snapshot for a location.

    Uses OpenWeather (richer weather + air pollution) when an API key is
    configured, otherwise Open-Meteo. Both return the SAME stable keys
    (temperature, windspeed, winddirection, weathercode, is_day, time) so
    old stored records and analytics keep working; newer sources simply add
    optional keys (humidity, pressure, aqi, pm2_5, ...).
    """
    if settings.openweather_api_key:
        return await _fetch_openweather(lat, lon)
    return await _fetch_open_meteo(lat, lon)


async def _fetch_open_meteo(lat: float, lon: float) -> Dict:
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

            snapshot["source"] = "open-meteo"
            return snapshot
    except httpx.HTTPError as e:
        logger.error(f"Error fetching Open-Meteo data: {e}")
        raise
    except KeyError as e:
        logger.error(f"Unexpected Open-Meteo response format, missing key: {e}")
        raise


async def _fetch_openweather(lat: float, lon: float) -> Dict:
    """Fetch current weather + air pollution from OpenWeather and normalize.

    Wind speed is converted from m/s (OpenWeather metric) to km/h to match
    the units already stored. Air pollution is fetched separately; if that
    call fails the weather snapshot is still returned without air fields.
    """
    common = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            wx_resp = await client.get(settings.openweather_weather_url,
                                       params={**common, "units": "metric"})
            wx_resp.raise_for_status()
            wx = wx_resp.json()

            main = wx.get("main", {})
            wind = wx.get("wind", {})
            weather0 = (wx.get("weather") or [{}])[0]
            icon = weather0.get("icon", "")
            dt = wx.get("dt")

            snapshot = {
                "time": (datetime.fromtimestamp(dt, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
                         if dt else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")),
                "temperature": main.get("temp"),
                "windspeed": round(wind.get("speed", 0) * 3.6, 1),  # m/s -> km/h
                "winddirection": wind.get("deg", 0),
                "weathercode": weather0.get("id"),
                "is_day": 1 if icon.endswith("d") else 0,
                "humidity": main.get("humidity"),
                "apparent_temperature": main.get("feels_like"),
                "pressure": main.get("pressure"),
                "temp_min": main.get("temp_min"),
                "temp_max": main.get("temp_max"),
                "visibility": wx.get("visibility"),
                "clouds": (wx.get("clouds") or {}).get("all"),
                "condition_main": weather0.get("main"),
                "condition_desc": weather0.get("description"),
                "condition_icon": icon,
                "source": "openweather",
            }

            # Air pollution is a separate endpoint; never let it break the
            # weather snapshot.
            try:
                air_resp = await client.get(settings.openweather_air_url, params=common)
                air_resp.raise_for_status()
                air0 = (air_resp.json().get("list") or [{}])[0]
                snapshot["aqi"] = air0.get("main", {}).get("aqi")
                for key, value in (air0.get("components") or {}).items():
                    snapshot[key] = value  # co, no, no2, o3, so2, pm2_5, pm10, nh3
            except (httpx.HTTPError, KeyError, IndexError) as e:
                logger.warning(f"Air pollution fetch failed (weather kept): {e}")

            return snapshot
    except httpx.HTTPError as e:
        logger.error(f"Error fetching OpenWeather data: {e}")
        raise
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected OpenWeather response format: {e}")
        raise


async def collect_weather_snapshot(lat: float, lon: float,
                                   data_manager: JSONDataManager) -> Dict:
    """Fetch one weather snapshot for a location and append it to its store.

    A snapshot is only stored if it has a valid temperature, so a partial or
    malformed API response never pollutes the data file with a junk record.
    """
    weather_data = await fetch_current_weather(lat, lon)
    if not isinstance(weather_data, dict) or not isinstance(
            weather_data.get("temperature"), (int, float)):
        raise ValueError("Fetched weather has no valid temperature; nothing stored")
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
