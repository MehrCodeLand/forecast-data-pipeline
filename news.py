"""News/announcement posts shown on the public News page.

Bilingual, like the rest of the site: every post carries an "en" and a "fa"
block. Stored as a JSON file (no database in this version). Posts are managed
from the admin panel and served read-only at /news; a post can be saved as a
draft and stays invisible to visitors until it is published.
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

NEWS_FILE = os.getenv("NEWS_FILE", "data/news.json")

MAX_TITLE = 160
MAX_SUMMARY = 400
MAX_BODY = 8000
MAX_TAG = 40


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class NewsStore:
    """JSON-backed list of news posts (newest first when served)."""

    def __init__(self, path: str = NEWS_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._items: List[Dict] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                stored = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid news file {self.path}: {e}")
            return

        if not isinstance(stored, list):
            logger.error(f"News file {self.path} is not a list; ignoring it")
            return

        for raw in stored:
            if isinstance(raw, dict) and raw.get("id"):
                self._items.append(self._clean(raw, post_id=str(raw["id"])))

    def _clean(self, raw: Dict, post_id: str) -> Dict:
        """Normalise one post: known fields only, trimmed to sane lengths."""

        def block(lang: str) -> Dict:
            source = raw.get(lang) if isinstance(raw.get(lang), dict) else {}
            return {
                "title": str(source.get("title", "")).strip()[:MAX_TITLE],
                "summary": str(source.get("summary", "")).strip()[:MAX_SUMMARY],
                "body": str(source.get("body", "")).strip()[:MAX_BODY],
            }

        return {
            "id": post_id,
            "tag": str(raw.get("tag", "")).strip()[:MAX_TAG],
            "published": bool(raw.get("published", True)),
            "published_at": str(raw.get("published_at") or _now()),
            "updated_at": str(raw.get("updated_at") or raw.get("published_at") or _now()),
            "en": block("en"),
            "fa": block("fa"),
        }

    def _persist(self) -> None:
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self._items, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Could not persist news: {e}")

    @staticmethod
    def _has_content(post: Dict) -> bool:
        """A post needs a title in at least one language to be worth showing."""
        return bool(post["en"]["title"] or post["fa"]["title"])

    def _sorted(self, items: List[Dict]) -> List[Dict]:
        return sorted(items, key=lambda p: p.get("published_at", ""), reverse=True)

    def all(self) -> List[Dict]:
        """Every post, drafts included (admin view), newest first."""
        return [dict(p) for p in self._sorted(self._items)]

    def published(self) -> List[Dict]:
        """Posts visitors may see, newest first."""
        return [dict(p) for p in self._sorted(self._items)
                if p.get("published") and self._has_content(p)]

    def get(self, post_id: str) -> Optional[Dict]:
        for post in self._items:
            if post["id"] == post_id:
                return dict(post)
        return None

    def add(self, fields: Dict) -> Dict:
        post = self._clean(fields, post_id=uuid.uuid4().hex[:12])
        if not self._has_content(post):
            raise ValueError("A post needs a title in at least one language")
        with self._lock:
            self._items.append(post)
            self._persist()
        logger.info(f"News post created: {post['id']}")
        return dict(post)

    def update(self, post_id: str, fields: Dict) -> Optional[Dict]:
        with self._lock:
            for index, existing in enumerate(self._items):
                if existing["id"] != post_id:
                    continue
                # Merge onto the stored post so a partial edit keeps the
                # fields it did not touch (e.g. editing only the Farsi text).
                merged = dict(existing)
                for lang in ("en", "fa"):
                    if isinstance(fields.get(lang), dict):
                        merged[lang] = {**existing[lang], **fields[lang]}
                for key in ("tag", "published", "published_at"):
                    if fields.get(key) is not None:
                        merged[key] = fields[key]
                merged["updated_at"] = _now()

                post = self._clean(merged, post_id=post_id)
                if not self._has_content(post):
                    raise ValueError("A post needs a title in at least one language")
                self._items[index] = post
                self._persist()
                logger.info(f"News post updated: {post_id}")
                return dict(post)
        return None

    def delete(self, post_id: str) -> bool:
        with self._lock:
            for index, post in enumerate(self._items):
                if post["id"] == post_id:
                    del self._items[index]
                    self._persist()
                    logger.info(f"News post deleted: {post_id}")
                    return True
        return False


news_store = NewsStore()
