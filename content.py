"""Editable site content (main page and info page), managed by the admin.

Stored as a JSON file (no database in this version). The public API exposes
it read-only at /content; the admin panel can update every field.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict

from loguru import logger

CONTENT_FILE = os.getenv("CONTENT_FILE", "data/site_content.json")

DEFAULT_CONTENT = {
    "site_name": "Weather Watch",
    "tagline": "Weather data collection and analysis, city by city",
    "home_intro": (
        "We continuously collect current weather conditions for cities around "
        "the world and turn them into clear, comparable analytics. Pick a city "
        "to explore its temperature and wind behaviour over time."
    ),
    "home_examples": (
        "For every city we track average temperature, temperature range and "
        "rate of change, wind speed and direction, calm periods, and more - "
        "all computed from data we collect ourselves at regular intervals."
    ),
    "about_title": "About This Project",
    "about_text": (
        "This project is an independent weather data pipeline. We fetch "
        "current conditions for each tracked city on a fixed schedule, store "
        "every snapshot, and compute analytics over the collected history. "
        "We are focused on one thing: collecting weather data and showing it "
        "to you clearly, without noise."
    ),
    "mission_text": (
        "Our goal is to make raw weather history accessible and understandable. "
        "All figures on this site come from our own collected snapshots, so you "
        "can see exactly how conditions in each city evolve over time."
    ),
    "data_description": (
        "For each city we store the current temperature, wind speed, wind "
        "direction, day/night flag and weather code, together with a timestamp. "
        "Analytics such as averages, ranges, rates of change and calm-period "
        "detection are computed from the most recent records."
    ),
    "contact_email": "contact@example.com",
    "footer_text": "Weather Analysis System",
}


class ContentStore:

    def __init__(self, path: str = CONTENT_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._content = dict(DEFAULT_CONTENT)
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                stored = json.load(f)
            # keep unknown keys out, fall back to defaults for missing ones
            for key in DEFAULT_CONTENT:
                if key in stored:
                    self._content[key] = stored[key]
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid content file {self.path}: {e}")

    def get(self) -> Dict:
        return dict(self._content)

    def update(self, fields: Dict) -> Dict:
        with self._lock:
            for key, value in fields.items():
                if key in DEFAULT_CONTENT and isinstance(value, str):
                    self._content[key] = value
            try:
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, 'w') as f:
                    json.dump(self._content, f, indent=2)
                logger.info("Site content updated")
            except OSError as e:
                logger.error(f"Could not persist content: {e}")
            return dict(self._content)


content_store = ContentStore()
