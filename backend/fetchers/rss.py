"""RSS fetcher — reads sources.json, parses feeds, upserts into articles table."""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent.parent / "sources.json"


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                pass
    return None


def _get_image(entry) -> Optional[str]:
    # media:thumbnail or enclosure
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("href")
    return None


async def fetch_all_rss(session: AsyncSession) -> int:
    sources = json.loads(SOURCES_PATH.read_text())
    total = 0
    for src in sources:
        try:
            count = await _fetch_one(session, src)
            total += count
        except Exception as e:
            logger.warning("RSS error %s: %s", src["name"], e)
    logger.info("RSS: inserted %d new articles", total)
    return total


async def _fetch_one(session: AsyncSession, src: dict) -> int:
    feed = feedparser.parse(src["url"])
    inserted = 0
    for entry in feed.entries[:30]:
        url = getattr(entry, "link", None)
        if not url:
            continue
        title = getattr(entry, "title", "").strip()
        if not title:
            continue
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        if summary:
            # strip HTML tags crudely
            import re
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:2000]

        try:
            await session.execute(
                text("""
                    INSERT INTO articles
                      (source, category, region, country, title, summary, url, image_url, published_at, tags)
                    VALUES
                      (:source, :category, :region, :country, :title, :summary, :url, :image_url, :published_at, :tags)
                    ON CONFLICT (url) DO NOTHING
                """),
                {
                    "source":       src["name"],
                    "category":     src.get("category"),
                    "region":       src.get("region"),
                    "country":      src.get("country"),
                    "title":        title,
                    "summary":      summary,
                    "url":          url,
                    "image_url":    _get_image(entry),
                    "published_at": _parse_date(entry),
                    "tags":         src.get("tags"),
                },
            )
            inserted += 1
        except Exception as e:
            logger.debug("Skip %s: %s", url, e)
    await session.commit()
    return inserted
