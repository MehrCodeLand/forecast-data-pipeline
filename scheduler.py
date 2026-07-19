import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

from loguru import logger

from cities import CityStore
from config import settings
from fetch_weather import collect_weather_snapshot

logger.add('logs/scheduler.txt', rotation="1 week")


class WeatherScheduler:
    """Collects weather data for every enabled city inside the app process.

    Runs as an asyncio background task started by the FastAPI lifespan; no
    external cron service is needed and the per-city collection status can
    be inspected over the API.
    """

    def __init__(self, city_store: CityStore,
                 interval_minutes: int = settings.fetch_interval_minutes):
        self.city_store = city_store
        self.interval_seconds = interval_minutes * 60
        self._task: Optional[asyncio.Task] = None
        self.runs = 0
        self.failures = 0
        self.last_run_at: Optional[str] = None
        self.city_status: Dict[str, Dict] = {}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            logger.warning("Scheduler is already running")
            return
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Scheduler started, collecting every {self.interval_seconds // 60} minutes")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("Scheduler stopped")

    async def set_interval(self, interval_minutes: int) -> None:
        """Change the collection interval; restarts the loop so it applies immediately."""
        self.interval_seconds = interval_minutes * 60
        if self.running:
            await self.stop()
            self.start()
        logger.info(f"Scheduler interval changed to {interval_minutes} minutes")

    async def _run_loop(self) -> None:
        # The loop must never die: a bug or an unexpected error in one round
        # is logged and the scheduler simply tries again next period.
        while True:
            try:
                await self.collect_all()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error in collection round: {e}")
            await asyncio.sleep(self.interval_seconds)

    async def collect_all(self) -> Dict[str, bool]:
        """Collect a snapshot for every enabled city. Returns per-city success.

        One city's failure never affects the others, and a failed fetch is
        skipped (no record written) so the next run just tries again.
        """
        self.runs += 1
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        results = {}
        for city in self.city_store.enabled():
            results[city["id"]] = await self.collect_city(city)
        return results

    async def collect_city(self, city: Dict, attempts: int = 3) -> bool:
        """Collect one snapshot for one city, retrying transient failures.

        Returns True on success. On failure nothing is stored, the error is
        recorded for the admin/city page, and the caller moves on - the
        website keeps serving whatever data already exists.
        """
        status = self.city_status.setdefault(city["id"], {
            "last_success_at": None, "last_error": None, "failures": 0,
        })

        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                await collect_weather_snapshot(
                    city["latitude"], city["longitude"], self.city_store.data_manager(city))
                status["last_success_at"] = datetime.now(timezone.utc).isoformat()
                status["last_error"] = None
                return True
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"Collection attempt {attempt}/{attempts} failed for "
                               f"{city['name']}: {e}")
                if attempt < attempts:
                    await asyncio.sleep(2 * attempt)  # 2s, 4s backoff

        self.failures += 1
        status["failures"] += 1
        status["last_error"] = str(last_error)
        logger.error(f"Collection failed for {city['name']} after {attempts} attempts: {last_error}")
        return False

    def status(self) -> Dict:
        return {
            "running": self.running,
            "interval_minutes": self.interval_seconds // 60,
            "runs": self.runs,
            "failures": self.failures,
            "last_run_at": self.last_run_at,
            "cities": self.city_status,
        }
