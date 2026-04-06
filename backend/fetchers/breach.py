"""Breach notifications and people/executive news fetcher."""
from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Optional

import aiohttp
import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WarRoomBot/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

BREACH_FEEDS = [
    ("https://www.databreaches.net/feed/",                         "breach",  "DataBreaches.net", None),
    ("https://feeds.feedburner.com/HaveIBeenPwnedLatestBreaches",  "breach",  "haveibeenpwned",   None),
]

PEOPLE_FEEDS = [
    ("https://techcrunch.com/category/startups/feed/",             "people",  "TechCrunch",       "US"),
    ("https://feeds.feedburner.com/venturebeat/SZYF",              "people",  "VentureBeat",      "US"),
]

THREAT_ACTOR_FEEDS = [
    ("https://www.cisa.gov/uscert/ncas/alerts.xml",                "threat-actor", "cisa",        "US"),
]


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                pass
    return None


def _clean(text_val: str) -> str:
    return re.sub(r"<[^>]+>", "", text_val or "").strip()[:2000]


async def _ingest_feed(
    session: AsyncSession,
    http: aiohttp.ClientSession,
    feed_url: str,
    signal_type: str,
    source_name: str,
    country: Optional[str],
    limit: int = 20,
) -> int:
    inserted = 0
    try:
        async with http.get(feed_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            content = await resp.text(errors="replace")
        feed = feedparser.parse(content)
        logger.debug("Breach feed %s: %d entries", source_name, len(feed.entries))

        for entry in feed.entries[:limit]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            desc  = _clean(getattr(entry, "summary", "") or "")
            url   = getattr(entry, "link", None)
            pub   = _parse_date(entry)
            severity = "high" if signal_type == "breach" else "low"

            try:
                await session.execute(
                    text("""
                        INSERT INTO osint_signals
                          (source, type, severity, title, description, url, country, published_at)
                        VALUES
                          (:source, :type, :severity, :title, :desc, :url, :country, :pub)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "source":   source_name,
                        "type":     signal_type,
                        "severity": severity,
                        "title":    title,
                        "desc":     desc,
                        "url":      url,
                        "country":  country,
                        "pub":      pub,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.debug("Breach/people skip %s: %s", source_name, e)
    except Exception as e:
        logger.warning("Feed error %s: %s", feed_url, e)
    return inserted


async def fetch_breach(session: AsyncSession) -> int:
    total = 0
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=_HEADERS) as http:
        for feed_url, signal_type, source_name, country in BREACH_FEEDS + PEOPLE_FEEDS + THREAT_ACTOR_FEEDS:
            total += await _ingest_feed(session, http, feed_url, signal_type, source_name, country)
    await session.commit()
    logger.info("Breach/People: inserted %d signals", total)
    return total
