import json
import os
from pathlib import Path

from loguru import logger

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "data/app_settings.json")


class Settings:
    """Application settings.

    Defaults come from environment variables. Values changed at runtime
    (through the admin panel) are persisted to SETTINGS_FILE and reloaded
    on the next start, overriding the environment defaults.
    """

    def __init__(self):
        self.latitude = float(os.getenv("WEATHER_LAT", "35.685017"))
        self.longitude = float(os.getenv("WEATHER_LON", "51.389693"))
        self.fetch_interval_minutes = int(os.getenv("FETCH_INTERVAL_MINUTES", "60"))
        self.data_file = os.getenv("DATA_FILE", "data/forecast_data_tehran.json")
        self.api_url = "https://api.open-meteo.com/v1/forecast"

        # OpenWeather: when an API key is set, snapshots are collected from
        # OpenWeather (richer weather + air pollution). With no key the app
        # falls back to the keyless Open-Meteo source, so it keeps working.
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
        self.openweather_weather_url = "https://api.openweathermap.org/data/2.5/weather"
        self.openweather_air_url = "https://api.openweathermap.org/data/2.5/air_pollution"

        # Zibal payment gateway. ZIBAL_MERCHANT comes from the environment
        # (.env on the server); the literal "zibal" is Zibal's own sandbox
        # merchant, so the flow stays testable without a real key.
        self.zibal_merchant = os.getenv("ZIBAL_MERCHANT", "zibal").strip() or "zibal"
        self.zibal_request_url = "https://gateway.zibal.ir/v1/request"
        self.zibal_verify_url = "https://gateway.zibal.ir/v1/verify"
        self.zibal_inquiry_url = "https://gateway.zibal.ir/v1/inquiry"
        self.zibal_start_url = "https://gateway.zibal.ir/start/"

        # Public base URL of the site, used to build the payment callback and
        # the result page (e.g. https://havachetor.ir). When empty it is
        # derived from the incoming request.
        self.site_base_url = os.getenv("SITE_BASE_URL", "").strip().rstrip("/")

        self._load_overrides()

    @property
    def payments_enabled(self) -> bool:
        """True when a real (non-sandbox) merchant key is configured."""
        return bool(self.zibal_merchant) and self.zibal_merchant != "zibal"

    @property
    def source(self) -> str:
        return "openweather" if self.openweather_api_key else "open-meteo"

    def _load_overrides(self) -> None:
        try:
            with open(SETTINGS_FILE) as f:
                overrides = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not load settings overrides from {SETTINGS_FILE}: {e}")
            return

        self.latitude = float(overrides.get("latitude", self.latitude))
        self.longitude = float(overrides.get("longitude", self.longitude))
        self.fetch_interval_minutes = int(
            overrides.get("fetch_interval_minutes", self.fetch_interval_minutes))

    def update(self, latitude: float = None, longitude: float = None,
               fetch_interval_minutes: int = None) -> None:
        """Apply new values and persist them so they survive restarts."""
        if latitude is not None:
            self.latitude = float(latitude)
        if longitude is not None:
            self.longitude = float(longitude)
        if fetch_interval_minutes is not None:
            self.fetch_interval_minutes = int(fetch_interval_minutes)
        self._persist()

    def _persist(self) -> None:
        try:
            Path(SETTINGS_FILE).parent.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "fetch_interval_minutes": self.fetch_interval_minutes,
                }, f, indent=2)
            logger.info(f"Settings persisted to {SETTINGS_FILE}")
        except OSError as e:
            logger.error(f"Could not persist settings: {e}")

    def as_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "fetch_interval_minutes": self.fetch_interval_minutes,
            "data_file": self.data_file,
        }


settings = Settings()
