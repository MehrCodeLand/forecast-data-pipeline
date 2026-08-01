"""Editable site content (main page and info page), managed by the admin.

Stored as a JSON file (no database in this version). Content is bilingual:
an "en" and a "fa" block with the same fields, plus shared fields such as
the donate URL. The public API exposes everything read-only at /content;
the admin panel can update every field per language.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict

from loguru import logger

CONTENT_FILE = os.getenv("CONTENT_FILE", "data/site_content.json")

LANG_FIELDS = [
    "site_name", "tagline", "home_intro", "home_examples", "about_title",
    "about_text", "mission_text", "data_description", "contact_email",
    "footer_text",
]

# Shared (not per-language) string fields.
SHARED_FIELDS = ["donate_url", "icon_data_url"]

# Superseded site names, per language, that should be upgraded to the
# current default. This covers earlier defaults and known misspellings
# (e.g. "هاوا" with an extra alef) that were saved through the admin panel.
# A name the admin genuinely customised is left alone.
OLD_SITE_NAMES = {
    "en": {"Weather Watch"},
    "fa": {
        "هواچطور",      # earlier default, single word
        "هاوا چطور",    # misspelling: extra alef
        "هاواچطور",     # same misspelling, single word
    },
}

DEFAULT_CONTENT = {
    "donate_url": "https://www.buymeacoffee.com",
    # Custom site icon as a data: URL (set from the admin panel). Empty means
    # the built-in default icon is used.
    "icon_data_url": "",
    "en": {
        "site_name": "HavaChetor",
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
    },
    "fa": {
        "site_name": "هوا چطور",
        "tagline": "جمع‌آوری و تحلیل داده‌های هواشناسی، شهر به شهر",
        "home_intro": (
            "ما به‌طور پیوسته وضعیت آب‌وهوای شهرهای مختلف جهان را جمع‌آوری می‌کنیم "
            "و آن را به تحلیل‌های روشن و قابل مقایسه تبدیل می‌کنیم. یک شهر را انتخاب "
            "کنید تا رفتار دما و باد آن را در طول زمان ببینید."
        ),
        "home_examples": (
            "برای هر شهر میانگین دما، بازه دما و نرخ تغییر، سرعت و جهت باد، "
            "دوره‌های آرام و موارد دیگر را دنبال می‌کنیم - همه از داده‌هایی که خودمان "
            "در بازه‌های منظم جمع‌آوری می‌کنیم."
        ),
        "about_title": "درباره این پروژه",
        "about_text": (
            "این پروژه یک سامانه مستقل جمع‌آوری داده‌های هواشناسی است. ما وضعیت "
            "لحظه‌ای هر شهر را طبق برنامه زمان‌بندی دریافت می‌کنیم، هر رکورد را ذخیره "
            "می‌کنیم و روی تاریخچه جمع‌آوری‌شده تحلیل انجام می‌دهیم. تمرکز ما روی یک "
            "چیز است: جمع‌آوری داده‌های هواشناسی و نمایش شفاف آن به شما."
        ),
        "mission_text": (
            "هدف ما دسترس‌پذیر و قابل فهم کردن تاریخچه خام آب‌وهواست. همه اعداد این "
            "سایت از رکوردهایی که خودمان جمع کرده‌ایم به دست می‌آید، بنابراین می‌توانید "
            "دقیقاً ببینید شرایط هر شهر چگونه در طول زمان تغییر می‌کند."
        ),
        "data_description": (
            "برای هر شهر دمای فعلی، سرعت باد، جهت باد، شاخص روز/شب و کد وضعیت هوا "
            "را همراه با برچسب زمانی ذخیره می‌کنیم. تحلیل‌هایی مانند میانگین، بازه، "
            "نرخ تغییر و تشخیص دوره‌های آرام روی جدیدترین رکوردها انجام می‌شود."
        ),
        "contact_email": "contact@example.com",
        "footer_text": "سامانه تحلیل آب‌وهوا",
    },
}


class ContentStore:

    def __init__(self, path: str = CONTENT_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._content = json.loads(json.dumps(DEFAULT_CONTENT))  # deep copy
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                stored = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid content file {self.path}: {e}")
            return

        if "en" not in stored and "fa" not in stored:
            # legacy single-language format: treat stored fields as English
            for key in LANG_FIELDS:
                if key in stored:
                    self._content["en"][key] = stored[key]
            self._migrate()
            return

        for field in SHARED_FIELDS:
            if isinstance(stored.get(field), str):
                self._content[field] = stored[field]
        for lang in ("en", "fa"):
            block = stored.get(lang)
            if isinstance(block, dict):
                for key in LANG_FIELDS:
                    if isinstance(block.get(key), str):
                        self._content[lang][key] = block[key]
        self._migrate()

    def _migrate(self) -> None:
        # One-off renames: a stored name that is just an older default is
        # treated as "not customised" and upgraded to the current default,
        # so already-deployed sites pick the new brand up automatically.
        for lang, old_names in OLD_SITE_NAMES.items():
            if self._content[lang].get("site_name") in old_names:
                self._content[lang]["site_name"] = DEFAULT_CONTENT[lang]["site_name"]

    def get(self) -> Dict:
        return json.loads(json.dumps(self._content))

    def update(self, fields: Dict) -> Dict:
        with self._lock:
            for field in SHARED_FIELDS:
                if isinstance(fields.get(field), str):
                    # data: URLs must keep their whitespace-free payload intact
                    self._content[field] = fields[field].strip()
            for lang in ("en", "fa"):
                block = fields.get(lang)
                if isinstance(block, dict):
                    for key, value in block.items():
                        if key in LANG_FIELDS and isinstance(value, str):
                            self._content[lang][key] = value
            try:
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, 'w') as f:
                    json.dump(self._content, f, indent=2, ensure_ascii=False)
                logger.info("Site content updated")
            except OSError as e:
                logger.error(f"Could not persist content: {e}")
            return self.get()


content_store = ContentStore()
