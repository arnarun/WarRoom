"""abuse.ch fetcher → osint_signals.

URLhaus + MalwareBazaar APIs require a free Auth-Key (ABUSECH_AUTH_KEY, from
auth.abuse.ch) and are skipped without one. Feodo Tracker's botnet C2
blocklist is a public download and always runs.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import config
from fetchers.common import SSL_CONTEXT

logger = logging.getLogger(__name__)

URLHAUS_API       = "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/20/"  # GET only
MALWAREBAZAAR_API = "https://mb-api.abuse.ch/api/v1/"
FEODO_BLOCKLIST   = "https://feodotracker.abuse.ch/downloads/ipblocklist.json"
FEODO_LIMIT       = 30


async def fetch_abusech(session: AsyncSession) -> int:
    inserted = 0

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
        inserted += await _fetch_feodo(session, http)
        if not config.ABUSECH_AUTH_KEY:
            logger.info("abuse.ch: ABUSECH_AUTH_KEY not set — skipping URLhaus/MalwareBazaar")
        else:
            http.headers["Auth-Key"] = config.ABUSECH_AUTH_KEY
            inserted += await _fetch_urlhaus(session, http)
            inserted += await _fetch_malwarebazaar(session, http)

    await session.commit()
    logger.info("abuse.ch: inserted %d signals", inserted)
    return inserted


async def _fetch_feodo(session: AsyncSession, http: aiohttp.ClientSession) -> int:
    inserted = 0
    try:
        async with http.get(FEODO_BLOCKLIST, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                logger.warning("Feodo Tracker returned %d", resp.status)
                return 0
            data = await resp.json(content_type=None)
        data = sorted(data or [], key=lambda d: d.get("first_seen") or "", reverse=True)
        for item in data[:FEODO_LIMIT]:
            ip = item.get("ip_address")
            if not ip:
                continue
            online = item.get("status") == "online"
            result = await session.execute(
                text("""
                    INSERT INTO osint_signals
                      (source, type, severity, title, description, url, country, published_at)
                    VALUES
                      ('feodo', 'malware', :sev, :title, :desc, :url, :country, :pub)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "sev":     "high" if online else "medium",
                    "title":   f"{item.get('malware', 'Botnet')} C2: {ip}:{item.get('port', '')}",
                    "desc":    f"Status: {item.get('status', '?')}  AS: {item.get('as_name', '')}  "
                               f"Last online: {item.get('last_online', '?')}",
                    "url":     f"https://feodotracker.abuse.ch/browse/host/{ip}/",
                    "country": (item.get("country") or None),
                    "pub":     _parse_dt(item.get("first_seen")),
                },
            )
            inserted += result.rowcount or 0
    except Exception as e:
        logger.warning("Feodo Tracker error: %s", e)
    return inserted


async def _fetch_urlhaus(session: AsyncSession, http: aiohttp.ClientSession) -> int:
    inserted = 0
    try:
        async with http.get(
            URLHAUS_API,
            timeout=aiohttp.ClientTimeout(total=30),
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
                        ON CONFLICT DO NOTHING
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
        logger.warning("URLhaus API error: %r", e)
    return inserted


async def _fetch_malwarebazaar(session: AsyncSession, http: aiohttp.ClientSession) -> int:
    inserted = 0
    try:
        async with http.post(
            MALWAREBAZAAR_API,
            data={"query": "get_recent", "selector": "100"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            data = await resp.json(content_type=None)
            logger.info("MalwareBazaar status=%s, samples=%d", data.get("query_status"), len(data.get("data") or []))
        for item in (data.get("data") or [])[:20]:
            try:
                await session.execute(
                    text("""
                        INSERT INTO osint_signals
                          (source, type, severity, title, description, url, published_at)
                        VALUES
                          ('malwarebazaar', 'malware', 'high', :title, :desc, :url, :pub)
                        ON CONFLICT DO NOTHING
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
        logger.warning("MalwareBazaar API error: %r", e)
    return inserted


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None
