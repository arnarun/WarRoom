"""AlienVault OTX threat intelligence fetcher → osint_signals.

The public RSS feed was discontinued; this uses the OTX API, which needs a
free key (OTX_API_KEY). Skipped without one.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import config
from fetchers.common import SSL_CONTEXT, utcnow

logger = logging.getLogger(__name__)

OTX_PULSES = "https://otx.alienvault.com/api/v1/pulses/subscribed"
OTX_LIMIT  = 30


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s[:19])
    except ValueError:
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
    if not config.OTX_API_KEY:
        logger.info("AlienVault OTX: OTX_API_KEY not set — skipping")
        return 0

    params = {
        "limit": OTX_LIMIT,
        "modified_since": (utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
            async with http.get(
                OTX_PULSES,
                params=params,
                headers={"X-OTX-API-KEY": config.OTX_API_KEY},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    logger.warning("AlienVault OTX HTTP %d", resp.status)
                    return 0
                data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("AlienVault fetch error: %s", e)
        return 0

    inserted = 0
    for pulse in data.get("results", []):
        title = (pulse.get("name") or "").strip()
        if not title or not pulse.get("id"):
            continue
        desc = (pulse.get("description") or "").strip()
        tags = ", ".join((pulse.get("tags") or [])[:8])
        if tags:
            desc = f"{desc}\nTags: {tags}".strip()
        try:
            result = await session.execute(
                text("""
                    INSERT INTO osint_signals
                      (source, type, severity, title, description, url, published_at)
                    VALUES
                      ('alienvault', 'threat-intel', :severity, :title, :desc, :url, :pub)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "severity": _infer_severity(title, desc),
                    "title":    title[:500],
                    "desc":     desc[:2000],
                    "url":      f"https://otx.alienvault.com/pulse/{pulse['id']}",
                    "pub":      _parse_date(pulse.get("created")),
                },
            )
            inserted += result.rowcount or 0
        except Exception as e:
            logger.debug("AlienVault skip: %s", e)

    await session.commit()
    logger.info("AlienVault OTX: inserted %d signals", inserted)
    return inserted
