"""City registry: which places around the world we collect weather for.

Cities are stored in a JSON file (no database in this version) and managed
through the admin panel. Each city gets its own data file.
"""

import json
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from config import settings
from data_json_manager import JSONDataManager

CITIES_FILE = os.getenv("CITIES_FILE", "data/cities.json")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "city"


class CityStore:

    def __init__(self, path: str = CITIES_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._cities: List[Dict] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                self._cities = json.load(f)
        except FileNotFoundError:
            self._cities = [self._default_city()]
            self._persist()
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid cities file {self.path}: {e}")
            self._cities = [self._default_city()]

    def _default_city(self) -> Dict:
        # Seed with Tehran, pointing at the pre-existing single-city data file
        # so previously collected data is kept.
        return {
            "id": "tehran",
            "name": "Tehran",
            "country": "Iran",
            "latitude": settings.latitude,
            "longitude": settings.longitude,
            "enabled": True,
            "data_file": settings.data_file,
        }

    def _persist(self) -> None:
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self._cities, f, indent=2)
        except OSError as e:
            logger.error(f"Could not persist cities to {self.path}: {e}")

    # ----- queries -----

    def all(self) -> List[Dict]:
        return [dict(c) for c in self._cities]

    def enabled(self) -> List[Dict]:
        return [dict(c) for c in self._cities if c.get("enabled", True)]

    def get(self, city_id: str) -> Optional[Dict]:
        for city in self._cities:
            if city["id"] == city_id:
                return dict(city)
        return None

    def data_manager(self, city: Dict) -> JSONDataManager:
        return JSONDataManager(city["data_file"])

    # ----- mutations -----

    def add(self, name: str, country: str, latitude: float, longitude: float) -> Dict:
        with self._lock:
            base_slug = _slugify(name)
            slug = base_slug
            suffix = 2
            while any(c["id"] == slug for c in self._cities):
                slug = f"{base_slug}-{suffix}"
                suffix += 1

            city = {
                "id": slug,
                "name": name.strip(),
                "country": country.strip(),
                "latitude": float(latitude),
                "longitude": float(longitude),
                "enabled": True,
                "data_file": f"data/weather_{slug}.json",
            }
            self._cities.append(city)
            self._persist()
            logger.info(f"City added: {city['name']} ({city['id']})")
            return dict(city)

    def update(self, city_id: str, **fields) -> Optional[Dict]:
        allowed = {"name", "country", "latitude", "longitude", "enabled"}
        with self._lock:
            for city in self._cities:
                if city["id"] == city_id:
                    for key, value in fields.items():
                        if key in allowed and value is not None:
                            city[key] = value
                    self._persist()
                    logger.info(f"City updated: {city_id}")
                    return dict(city)
        return None

    def delete(self, city_id: str) -> bool:
        with self._lock:
            before = len(self._cities)
            self._cities = [c for c in self._cities if c["id"] != city_id]
            if len(self._cities) < before:
                self._persist()
                logger.info(f"City deleted: {city_id}")
                return True
        return False


city_store = CityStore()
