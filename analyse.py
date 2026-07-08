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

    @staticmethod
    def _values(records: List[Dict], field: str) -> List[float]:
        """Values of `field` from records that actually have it.

        Older records collected before a field existed simply omit it, so
        every optional metric ignores the records that lack the field
        instead of raising a KeyError.
        """
        return [r[field] for r in records
                if isinstance(r.get(field), (int, float))]

    async def get_optional_avg(self, field: str, period: int) -> Optional[float]:
        """Average of an optional numeric field over the recent records.

        Returns None when no record in the window carries the field (e.g.
        only legacy data has been collected so far)."""
        try:
            records = await self._recent_records(period)
            if not records:
                return None
            values = self._values(records, field)
            if not values:
                return None
            return round(sum(values) / len(values), 2)
        except Exception as e:
            logger.error(f"Error in get_optional_avg({field}): {e}")
            return None

    async def get_optional_sum(self, field: str, period: int) -> Optional[float]:
        """Total of an optional numeric field (e.g. precipitation)."""
        try:
            records = await self._recent_records(period)
            if not records:
                return None
            values = self._values(records, field)
            if not values:
                return None
            return round(sum(values), 2)
        except Exception as e:
            logger.error(f"Error in get_optional_sum({field}): {e}")
            return None

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

            summary = {
                "avg_temperature": await self.get_avg(period),
                "temp_range": await self.get_temperature_range(period),
                "avg_windspeed": await self.get_avg_windspeed(period),
                "peak_windspeed": await self.get_peak_windspeed(period),
                "dominant_wind_direction": await self.get_dominant_wind_direction(period),
                "wind_variability": await self.get_wind_direction_variability(period),
                "calm_periods": await self.get_calm_periods(period),
                "data_points": period,
            }

            # Optional metrics: only included when the window actually has
            # records carrying the field, so summaries over legacy-only data
            # stay unchanged.
            optional = {
                "avg_humidity": await self.get_optional_avg("humidity", period),
                "avg_apparent_temperature": await self.get_optional_avg("apparent_temperature", period),
                "avg_pressure": await self.get_optional_avg("pressure", period),
                "total_precipitation": await self.get_optional_sum("precipitation", period),
            }
            summary.update({k: v for k, v in optional.items() if v is not None})

            return summary
        except Exception as e:
            logger.error(f"Error in get_weather_summary: {e}")
            return None

    async def get_records(self, calm_threshold: float = 5.0) -> Optional[Dict]:
        """All-time records and milestones over the city's full history.

        Computed over every stored record (not just a recent window), so the
        highlights grow more interesting as history accumulates.
        """
        try:
            data = await self.json_manager.read_data()
            if not data:
                return None

            def extreme(field: str, pick):
                candidates = [r for r in data if isinstance(r.get(field), (int, float))]
                if not candidates:
                    return None
                record = pick(candidates, key=lambda r: r[field])
                return {
                    "value": record[field],
                    "timestamp": record.get("timestamp"),
                    "time": record.get("time"),
                }

            # Longest run of consecutive records below the calm threshold.
            longest_calm = 0
            current_calm = 0
            calm_start = None
            best_calm_start = None
            best_calm_end = None
            for r in data:
                speed = r.get("windspeed")
                if isinstance(speed, (int, float)) and speed < calm_threshold:
                    if current_calm == 0:
                        calm_start = r.get("timestamp")
                    current_calm += 1
                    if current_calm > longest_calm:
                        longest_calm = current_calm
                        best_calm_start = calm_start
                        best_calm_end = r.get("timestamp")
                else:
                    current_calm = 0

            result = {
                "total_records": len(data),
                "first_record": data[0].get("timestamp"),
                "last_record": data[-1].get("timestamp"),
                "hottest": extreme("temperature", max),
                "coldest": extreme("temperature", min),
                "windiest": extreme("windspeed", max),
                "longest_calm_streak": {
                    "records": longest_calm,
                    "threshold": calm_threshold,
                    "start": best_calm_start,
                    "end": best_calm_end,
                },
            }

            # Optional records only appear once such data has been collected.
            wettest = extreme("precipitation", max)
            if wettest is not None and wettest["value"] > 0:
                result["wettest"] = wettest
            most_humid = extreme("humidity", max)
            if most_humid is not None:
                result["most_humid"] = most_humid

            return result
        except Exception as e:
            logger.error(f"Error in get_records: {e}")
            return None
