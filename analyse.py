import math
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from data_json_manager import JSONDataManager

logger.add('logs/analyse.txt', rotation="1 week")


def _parse_timestamp(record: Dict) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(record["timestamp"])
    except (KeyError, ValueError):
        return None


class Analyse:
    def __init__(self, json_manager: JSONDataManager):
        self.json_manager = json_manager

    async def _recent_records(self, period: int) -> Optional[List[Dict]]:
        """Return the most recent `period` records, or None if unavailable."""
        if period <= 0:
            logger.warning("Invalid period: must be greater than zero.")
            return None

        data = await self.json_manager.read_data()
        if not data:
            logger.warning("No data available for analysis.")
            return None

        return data[-period:]

    async def get_avg(self, period: int) -> Optional[float]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            return round(sum(ent["temperature"] for ent in records) / len(records), 2)
        except Exception as e:
            logger.error(f"Error in get_avg: {e}")
            return None

    async def estimate_avg_of_rate_of_change(self, hours: int) -> Optional[float]:
        try:
            records = await self._recent_records(hours)
            if not records or len(records) < 2:
                logger.warning("Insufficient data for rate calculation.")
                return None

            rates = []
            for prev, curr in zip(records, records[1:]):
                prev_time, curr_time = _parse_timestamp(prev), _parse_timestamp(curr)
                if prev_time is None or curr_time is None:
                    continue
                delta_hours = (curr_time - prev_time).total_seconds() / 3600
                if delta_hours <= 0:
                    continue
                rates.append((curr["temperature"] - prev["temperature"]) / delta_hours)

            if not rates:
                logger.warning("No valid timestamp pairs for rate calculation.")
                return None

            return round(sum(rates) / len(rates), 2)
        except Exception as e:
            logger.error(f"Error in estimate_avg_of_rate_of_change: {e}")
            return None

    async def estimate_delta(self, hours: int) -> Optional[float]:
        try:
            records = await self._recent_records(hours)
            if not records or len(records) < 2:
                logger.warning("Insufficient data for delta calculation.")
                return None

            first, last = records[0], records[-1]
            first_time, last_time = _parse_timestamp(first), _parse_timestamp(last)

            if first_time and last_time and last_time > first_time:
                span_hours = (last_time - first_time).total_seconds() / 3600
            else:
                span_hours = len(records) - 1

            return round((last["temperature"] - first["temperature"]) / span_hours, 2)
        except Exception as e:
            logger.error(f"Error in estimate_delta: {e}")
            return None

    async def get_avg_windspeed(self, period: int) -> Optional[float]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            return round(sum(ent["windspeed"] for ent in records) / len(records), 2)
        except Exception as e:
            logger.error(f"Error in get_avg_windspeed: {e}")
            return None

    async def get_peak_windspeed(self, period: int) -> Optional[float]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            return round(max(ent["windspeed"] for ent in records), 2)
        except Exception as e:
            logger.error(f"Error in get_peak_windspeed: {e}")
            return None

    async def get_dominant_wind_direction(self, period: int) -> Optional[float]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            sin_sum = sum(math.sin(math.radians(ent["winddirection"])) for ent in records)
            cos_sum = sum(math.cos(math.radians(ent["winddirection"])) for ent in records)

            mean_direction = math.degrees(math.atan2(sin_sum, cos_sum))
            if mean_direction < 0:
                mean_direction += 360

            return round(mean_direction, 1)
        except Exception as e:
            logger.error(f"Error in get_dominant_wind_direction: {e}")
            return None

    async def get_wind_direction_variability(self, period: int) -> Optional[float]:
        try:
            records = await self._recent_records(period)
            if not records or len(records) < 2:
                logger.warning("Insufficient data for variability analysis.")
                return None

            changes = []
            for prev, curr in zip(records, records[1:]):
                diff = curr["winddirection"] - prev["winddirection"]
                if diff > 180:
                    diff -= 360
                elif diff < -180:
                    diff += 360
                changes.append(abs(diff))

            mean_change = sum(changes) / len(changes)
            variance = sum((x - mean_change) ** 2 for x in changes) / len(changes)

            return round(math.sqrt(variance), 2)
        except Exception as e:
            logger.error(f"Error in get_wind_direction_variability: {e}")
            return None

    async def get_calm_periods(self, period: int, threshold: float = 5.0) -> Optional[Dict]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            calm_count = sum(1 for ent in records if ent["windspeed"] < threshold)

            return {
                "calm_periods": calm_count,
                "total_periods": len(records),
                "calm_percentage": round((calm_count / len(records)) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Error in get_calm_periods: {e}")
            return None

    async def get_temperature_range(self, period: int) -> Optional[Dict]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            temps = [ent["temperature"] for ent in records]

            return {
                "min": round(min(temps), 2),
                "max": round(max(temps), 2),
                "range": round(max(temps) - min(temps), 2)
            }
        except Exception as e:
            logger.error(f"Error in get_temperature_range: {e}")
            return None

    async def get_weather_summary(self, period: int) -> Optional[Dict]:
        try:
            records = await self._recent_records(period)
            if not records:
                return None

            period = len(records)

            return {
                "avg_temperature": await self.get_avg(period),
                "temp_range": await self.get_temperature_range(period),
                "avg_windspeed": await self.get_avg_windspeed(period),
                "peak_windspeed": await self.get_peak_windspeed(period),
                "dominant_wind_direction": await self.get_dominant_wind_direction(period),
                "wind_variability": await self.get_wind_direction_variability(period),
                "calm_periods": await self.get_calm_periods(period),
                "data_points": period
            }
        except Exception as e:
            logger.error(f"Error in get_weather_summary: {e}")
            return None
