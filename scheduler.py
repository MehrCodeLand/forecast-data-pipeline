import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional

from loguru import logger

from config import settings
from data_json_manager import JSONDataManager
from fetch_weather import collect_weather_snapshot

logger.add('logs/scheduler.txt', rotation="1 week")


class WeatherScheduler:
    """Collects weather data periodically inside the application process.

    Replaces the old cron-based setup: the FastAPI app starts this scheduler
    on startup and stops it on shutdown, so no external cron service is
    needed and the collection status can be inspected over the API.
    """

    def __init__(self, data_manager: JSONDataManager,
                 interval_minutes: int = settings.fetch_interval_minutes):
        self.data_manager = data_manager
        self.interval_seconds = interval_minutes * 60
        self._task: Optional[asyncio.Task] = None
        self.runs = 0
        self.failures = 0
        self.last_run_at: Optional[str] = None
        self.last_success_at: Optional[str] = None
        self.last_error: Optional[str] = None

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
        while True:
            await self.collect_now()
            await asyncio.sleep(self.interval_seconds)

    async def collect_now(self) -> bool:
        """Run one collection immediately. Returns True on success."""
        self.runs += 1
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        try:
            await collect_weather_snapshot(self.data_manager)
            self.last_success_at = self.last_run_at
            self.last_error = None
            return True
        except Exception as e:
            self.failures += 1
            self.last_error = str(e)
            logger.error(f"Scheduled weather collection failed: {e}")
            return False

    def status(self) -> Dict:
        return {
            "running": self.running,
            "interval_minutes": self.interval_seconds // 60,
            "runs": self.runs,
            "failures": self.failures,
            "last_run_at": self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
        }
