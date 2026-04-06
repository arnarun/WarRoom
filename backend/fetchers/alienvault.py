"""AlienVault OTX threat intelligence fetcher (public RSS feed — no API key required)."""
from __future__ import annotations
import logging
import re
from datetime import datetime
from typing import Optional

import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Public OTX RSS feed — no authentication required
OTX_RSS = "https://otx.alienvault.com/rss.xml"


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                pass
    return None


def _infer_severity(title: str, desc: str) -> str:
    text_lower = (title + " " + desc).lower()
    if any(w in text_lower for w in ["critical", "actively exploited", "zero-day", "0-day"]):
        return "critical"
    if any(w in text_lower for w in ["high", "severe", "remote code", "ransomware"]):
        return "high"
    if any(w in text_lower for w in ["low", "informational"]):
        return "low"
    return "medium"


async def fetch_alienvault(session: AsyncSession) -> int:
    inserted = 0
    try:
        feed = feedparser.parse(OTX_RSS)
        for entry in feed.entries[:30]:
            title = getattr(entry, "title", "").strip()
            if not title:
                continue
            desc = getattr(entry, "summary", "") or ""
            desc = re.sub(r"<[^>]+>", "", desc).strip()[:2000]
            url = getattr(entry, "link", None)
            pub = _parse_date(entry)
            severity = _infer_severity(title, desc)

            try:
                await session.execute(
                    text("""
                        INSERT INTO osint_signals
                          (source, type, severity, title, description, url, published_at)
                        VALUES
                          ('alienvault', 'threat-intel', :severity, :title, :desc, :url, :pub)
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "severity": severity,
                        "title":    title,
                        "desc":     desc,
                        "url":      url,
                        "pub":      pub,
                    },
                )
                inserted += 1
            except Exception as e:
                logger.debug("AlienVault skip: %s", e)
    except Exception as e:
        logger.warning("AlienVault fetch error: %s", e)

    await session.commit()
    logger.info("AlienVault OTX: inserted %d signals", inserted)
    return inserted
