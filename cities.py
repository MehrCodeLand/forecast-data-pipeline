"""City registry: which places around the world we collect weather for.

Cities are stored in a JSON file (no database in this version) and managed
through the admin panel. Each city gets its own data file.

Names are bilingual: `name`/`country` hold the English text (they also drive
the city's id and every export) and `name_fa`/`country_fa` hold the Farsi
text. A city added before the Farsi fields existed simply has them empty; the
site falls back to English until an admin fills them in from the panel.
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

# Optional Farsi names, blank on cities created before they existed.
TRANSLATED_FIELDS = ("name_fa", "country_fa")


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
            return
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid cities file {self.path}: {e}")
            self._cities = [self._default_city()]
            return

        # Cities stored before the bilingual fields existed get them as empty
        # strings, in memory only: the file is rewritten on the next edit, and
        # until then the site just falls back to the English name.
        for city in self._cities:
            for field in TRANSLATED_FIELDS:
                city.setdefault(field, "")

    def _default_city(self) -> Dict:
        # Seed with Tehran, pointing at the pre-existing single-city data file
        # so previously collected data is kept.
        return {
            "id": "tehran",
            "name": "Tehran",
            "country": "Iran",
            "name_fa": "تهران",
            "country_fa": "ایران",
            "latitude": settings.latitude,
            "longitude": settings.longitude,
            "enabled": True,
            "data_file": settings.data_file,
        }

    def _persist(self) -> None:
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w') as f:
                # ensure_ascii=False keeps the Farsi names readable in the file
                json.dump(self._cities, f, indent=2, ensure_ascii=False)
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

    def add(self, name: str, country: str, latitude: float, longitude: float,
            name_fa: str = "", country_fa: str = "") -> Dict:
        with self._lock:
            # The id comes from the English name so it stays ASCII and usable
            # in URLs, file names and exports.
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
                "name_fa": (name_fa or "").strip(),
                "country_fa": (country_fa or "").strip(),
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
        allowed = {"name", "country", "name_fa", "country_fa",
                   "latitude", "longitude", "enabled"}
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
