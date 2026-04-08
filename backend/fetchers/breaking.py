"""Breaking news RSS fetcher — polls only high-priority sources every 5 minutes."""
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
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


async def fetch_breaking_rss(session: AsyncSession) -> int:
    sources = json.loads(SOURCES_PATH.read_text())
    breaking = [s for s in sources if s.get("breaking")]
    total = 0

    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    async with aiohttp.ClientSession(
        connector=connector, headers=_HEADERS, max_field_size=16384
    ) as http:
        for src in breaking:
            try:
                async with http.get(src["url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    content = await resp.text(errors="replace")
                feed = feedparser.parse(content)
                for entry in feed.entries[:10]:
                    url   = getattr(entry, "link", None)
                    title = getattr(entry, "title", "").strip()
                    if not url or not title:
                        continue
                    summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
                    if summary:
                        summary = re.sub(r"<[^>]+>", "", summary).strip()[:2000]
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO articles
                                  (source, category, region, country, title, summary,
                                   url, image_url, published_at, tags)
                                VALUES
                                  (:source, :category, :region, :country, :title, :summary,
                                   :url, :image_url, :published_at, :tags)
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
                        total += 1
                    except Exception as e:
                        logger.debug("Breaking skip %s: %s", url, e)
            except Exception as e:
                logger.warning("Breaking RSS error %s: %s", src["name"], e)

    await session.commit()
    logger.info("Breaking RSS: checked %d sources, inserted %d articles", len(breaking), total)
    return total
