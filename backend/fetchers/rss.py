"""RSS fetcher — reads sources.json, parses feeds, upserts into articles table."""
from __future__ import annotations
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent.parent / "sources.json"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WarRoomBot/1.0; +https://github.com/warroom)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}


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
    ok_count = 0
    fail_count = 0
    empty_count = 0
    connector = aiohttp.TCPConnector(ssl=False, limit=20)
    async with aiohttp.ClientSession(
        connector=connector, headers=_HEADERS, max_field_size=16384
    ) as http:
        for src in sources:
            try:
                count, status = await _fetch_one(session, src, http)
                total += count
                if status == "ok":     ok_count += 1
                elif status == "empty": empty_count += 1
                else:                  fail_count += 1
            except Exception as e:
                fail_count += 1
                logger.warning("RSS error %s: %s", src["name"], e)
    logger.info("RSS: inserted %d articles (ok=%d empty=%d fail=%d)",
                total, ok_count, empty_count, fail_count)
    return total


async def _fetch_one(session: AsyncSession, src: dict, http: aiohttp.ClientSession):
    try:
        async with http.get(src["url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status >= 400:
                logger.warning("RSS %s HTTP %d", src["name"], resp.status)
                return 0, "fail"
            content = await resp.text(errors="replace")
    except Exception as e:
        logger.warning("RSS fetch failed %s: %s", src["name"], e)
        return 0, "fail"

    feed = feedparser.parse(content)
    if not feed.entries:
        preview = content[:120].replace('\n', ' ').strip()
        logger.warning("RSS 0 entries %s — content preview: %s", src["name"], preview)
        return 0, "empty"

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
    return inserted, "ok"
