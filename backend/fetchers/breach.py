"""Breach notifications and people/executive news fetcher."""
from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Optional

import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

BREACH_FEEDS = [
    # DataBreaches.net — comprehensive breach reporting RSS
    ("https://www.databreaches.net/feed/", "breach", "DataBreaches.net", None),
    # HaveIBeenPwned latest breach notifications (public Atom feed)
    ("https://feeds.feedburner.com/HaveIBeenPwnedLatestBreaches", "breach", "haveibeenpwned", None),
]

PEOPLE_FEEDS = [
    # Reuters People news
    ("https://feeds.reuters.com/reuters/peopleNews", "people", "Reuters People", None),
    # TechCrunch founder/executive category
    ("https://techcrunch.com/category/startups/feed/", "people", "TechCrunch", "US"),
]

THREAT_ACTOR_FEEDS = [
    # CISA named-actor advisories (already covered in cisa.py but we mirror here for type=threat-actor)
    ("https://www.cisa.gov/uscert/ncas/alerts.xml", "threat-actor", "cisa", "US"),
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
    feed_url: str,
    signal_type: str,
    source_name: str,
    country: Optional[str],
    limit: int = 20,
) -> int:
    inserted = 0
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            desc = _clean(getattr(entry, "summary", "") or "")
            url = getattr(entry, "link", None)
            pub = _parse_date(entry)

            # Severity: breaches are generally high, people news is low
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
    for feed_url, signal_type, source_name, country in BREACH_FEEDS + PEOPLE_FEEDS:
        total += await _ingest_feed(session, feed_url, signal_type, source_name, country)
    await session.commit()
    logger.info("Breach/People: inserted %d signals", total)
    return total
