"""CISA alerts fetcher — RSS → osint_signals."""
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

CISA_FEEDS = [
    ("https://www.cisa.gov/uscert/ncas/alerts.xml",           "cyber-threat", "US"),
    ("https://www.cisa.gov/uscert/ncas/current-activity.xml", "cyber-threat", "US"),
    ("https://www.cisa.gov/uscert/ncas/bulletins.xml",        "cyber-threat", "US"),
    ("https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml", "cyber-threat", "UK"),
    ("https://www.enisa.europa.eu/rss",                            "cyber-threat", "EU"),
    ("https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed_Aktuell/RSSNewsfeed_Aktuell_node.html", "cyber-threat", "Germany"),
]

_SOURCE_MAP = {
    "US":      "cisa",
    "UK":      "ncsc-uk",
    "EU":      "enisa",
    "Germany": "bsi",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WarRoomBot/1.0)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
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


async def fetch_cisa(session: AsyncSession) -> int:
    inserted = 0
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=_HEADERS) as http:
        for feed_url, signal_type, country in CISA_FEEDS:
            source_name = _SOURCE_MAP.get(country, "cert")
            try:
                async with http.get(feed_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    content = await resp.text(errors="replace")
                feed = feedparser.parse(content)
                for entry in feed.entries[:20]:
                    title = getattr(entry, "title", "").strip()
                    if not title:
                        continue
                    desc = getattr(entry, "summary", "") or ""
                    desc = re.sub(r"<[^>]+>", "", desc).strip()[:2000]

                    severity = "medium"
                    tl = title.lower()
                    if any(w in tl for w in ["critical", "actively exploited", "emergency"]):
                        severity = "critical"
                    elif any(w in tl for w in ["high", "severe", "remote code"]):
                        severity = "high"
                    elif any(w in tl for w in ["low", "informational"]):
                        severity = "low"

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
                                "url":      getattr(entry, "link", None),
                                "country":  country,
                                "pub":      _parse_date(entry),
                            },
                        )
                        inserted += 1
                    except Exception as e:
                        logger.debug("CERT feed skip: %s", e)
            except Exception as e:
                logger.warning("CERT feed error %s: %s", feed_url, e)

    await session.commit()
    logger.info("CISA/CERTs: inserted %d signals", inserted)
    return inserted
