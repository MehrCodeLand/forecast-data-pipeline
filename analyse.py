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
                # Air quality (OpenWeather)
                "avg_aqi": await self.get_optional_avg("aqi", period),
                "avg_pm2_5": await self.get_optional_avg("pm2_5", period),
                "avg_pm10": await self.get_optional_avg("pm10", period),
                "avg_clouds": await self.get_optional_avg("clouds", period),
            }
            summary.update({k: v for k, v in optional.items() if v is not None})

            # Latest snapshot carries the current condition and air-quality
            # components for the "right now" cards.
            latest = records[-1]
            current = {}
            for key in ("aqi", "pm2_5", "pm10", "co", "no2", "o3", "so2", "nh3",
                        "condition_main", "condition_desc", "condition_icon",
                        "visibility", "clouds", "source"):
                if latest.get(key) is not None:
                    current[key] = latest[key]
            if current:
                summary["current"] = current

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

    def _record_time(self, record: Dict) -> Optional[datetime]:
        """Best available datetime for a record: stored timestamp, else the
        source 'time' field."""
        dt = _parse_timestamp(record)
        if dt is not None:
            return dt
        try:
            return datetime.fromisoformat(record["time"])
        except (KeyError, ValueError, TypeError):
            return None

    async def get_heatmap(self, field: str) -> Optional[Dict]:
        """Average of `field` by weekday (0=Mon..6=Sun) and hour-of-day.

        Returns a 7x24 grid of averages (None where no data), plus the global
        min/max for color scaling and per-cell counts. Powers the
        hour-of-day vs weekday heatmap.
        """
        try:
            data = await self.json_manager.read_data()
            if not data:
                return None

            sums = [[0.0] * 24 for _ in range(7)]
            counts = [[0] * 24 for _ in range(7)]
            has_any = False
            for r in data:
                value = r.get(field)
                dt = self._record_time(r)
                if dt is None or not isinstance(value, (int, float)):
                    continue
                sums[dt.weekday()][dt.hour] += value
                counts[dt.weekday()][dt.hour] += 1
                has_any = True

            if not has_any:
                return None

            grid = [[round(sums[d][h] / counts[d][h], 2) if counts[d][h] else None
                     for h in range(24)] for d in range(7)]
            flat = [v for row in grid for v in row if v is not None]

            return {
                "field": field,
                "grid": grid,
                "counts": counts,
                "min": round(min(flat), 2),
                "max": round(max(flat), 2),
                "samples": len(flat),
            }
        except Exception as e:
            logger.error(f"Error in get_heatmap({field}): {e}")
            return None

    async def get_forecast(self, field: str, steps: int = 6,
                           window: int = 12) -> Optional[Dict]:
        """Naive short-term projection of `field` for the next `steps` hours.

        Fits a least-squares line to the most recent `window` records (spaced
        by their real timestamps) and extends it. This is a simple trend
        estimate, NOT a meteorological forecast - the response is labelled so
        the UI can say so.
        """
        try:
            data = await self.json_manager.read_data()
            if not data:
                return None

            points = []
            for r in data[-window:]:
                dt = self._record_time(r)
                value = r.get(field)
                if dt is not None and isinstance(value, (int, float)):
                    points.append((dt, value))
            if len(points) < 3:
                return None

            base = points[0][0]
            xs = [(dt - base).total_seconds() / 3600 for dt, _ in points]
            ys = [v for _, v in points]
            n = len(xs)

            mean_x = sum(xs) / n
            mean_y = sum(ys) / n
            denom = sum((x - mean_x) ** 2 for x in xs)
            if denom == 0:
                return None
            slope = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom
            intercept = mean_y - slope * mean_x

            last_dt, _ = points[-1]
            last_x = xs[-1]

            # Clamp AQI-style indices to their valid 1..5 range.
            clamp = (1, 5) if field == "aqi" else None
            from datetime import timedelta
            forecast = []
            for step in range(1, steps + 1):
                x = last_x + step
                y = slope * x + intercept
                if clamp:
                    y = max(clamp[0], min(clamp[1], y))
                forecast.append({
                    "time": (last_dt + timedelta(hours=step)).isoformat(),
                    "value": round(y, 2),
                })

            return {
                "field": field,
                "method": "linear-trend",
                "slope_per_hour": round(slope, 3),
                "based_on": n,
                "forecast": forecast,
            }
        except Exception as e:
            logger.error(f"Error in get_forecast({field}): {e}")
            return None
