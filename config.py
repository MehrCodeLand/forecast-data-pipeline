import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Application settings, overridable via environment variables."""

    latitude: float = field(default_factory=lambda: float(os.getenv("WEATHER_LAT", "35.685017")))
    longitude: float = field(default_factory=lambda: float(os.getenv("WEATHER_LON", "51.389693")))
    fetch_interval_minutes: int = field(default_factory=lambda: int(os.getenv("FETCH_INTERVAL_MINUTES", "60")))
    data_file: str = field(default_factory=lambda: os.getenv("DATA_FILE", "data/forecast_data_tehran.json"))
    api_url: str = "https://api.open-meteo.com/v1/forecast"


settings = Settings()
