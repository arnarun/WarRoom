"""abuse.ch fetcher — URLhaus + MalwareBazaar → osint_signals."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

URLHAUS_API       = "https://urlhaus-api.abuse.ch/v1/urls/recent/"
MALWAREBAZAAR_API = "https://mb-api.abuse.ch/api/v1/"


async def fetch_abusech(session: AsyncSession) -> int:
    inserted = 0

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as http:
        # --- URLhaus ---
        try:
            async with http.post(
                URLHAUS_API,
                data={"limit": "20"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json(content_type=None)
                logger.info("URLhaus status=%s, urls=%d", data.get("query_status"), len(data.get("urls", [])))
            for item in data.get("urls", []):
                try:
                    await session.execute(
                        text("""
                            INSERT INTO osint_signals
                              (source, type, severity, title, description, url, published_at)
                            VALUES
                              ('urlhaus', 'phishing', 'high', :title, :desc, :url, :pub)
                        """),
                        {
                            "title": f"Malicious URL: {item.get('url', '')[:200]}",
                            "desc":  f"Tags: {item.get('tags', [])}  Threat: {item.get('threat', '')}",
                            "url":   item.get("urlhaus_link"),
                            "pub":   _parse_dt(item.get("date_added")),
                        },
                    )
                    inserted += 1
                except Exception as e:
                    logger.debug("URLhaus insert skip: %s", e)
        except Exception as e:
            logger.warning("URLhaus API error: %s", e)

        # --- MalwareBazaar ---
        try:
            async with http.post(
                MALWAREBAZAAR_API,
                data={"query": "get_recent", "selector": "100"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json(content_type=None)
            for item in (data.get("data") or [])[:20]:
                try:
                    await session.execute(
                        text("""
                            INSERT INTO osint_signals
                              (source, type, severity, title, description, url, published_at)
                            VALUES
                              ('malwarebazaar', 'malware', 'high', :title, :desc, :url, :pub)
                        """),
                        {
                            "title": f"Malware Sample: {item.get('sha256_hash', '')[:16]}... ({item.get('file_name', '')})",
                            "desc":  f"Type: {item.get('file_type', '')}  Tags: {item.get('tags', [])}",
                            "url":   f"https://bazaar.abuse.ch/sample/{item.get('sha256_hash', '')}",
                            "pub":   _parse_dt(item.get("first_seen")),
                        },
                    )
                    inserted += 1
                except Exception as e:
                    logger.debug("MalwareBazaar insert skip: %s", e)
        except Exception as e:
            logger.warning("MalwareBazaar API error: %s", e)

    await session.commit()
    logger.info("abuse.ch: inserted %d signals", inserted)
    return inserted


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None
