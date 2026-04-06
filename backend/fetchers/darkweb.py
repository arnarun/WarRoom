"""Dark web intelligence fetcher.

Clearnet RSS feeds that aggregate dark web threat intel (always available).
Optional Tor SOCKS5 proxy for .onion fetching — graceful fallback if Tor is down.

Setup Tor (once): brew install tor && brew services start tor
"""
from __future__ import annotations
import asyncio
import logging
import re
import socket
from datetime import datetime
from typing import Optional

import aiohttp
import feedparser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TOR_HOST = "127.0.0.1"
TOR_PORT = 9050

# Clearnet RSS feeds covering dark web activity — no Tor required
CLEARNET_FEEDS = [
    ("https://darkwebinformer.com/feed/",             "DarkWebInformer"),
    ("https://www.recordedfuture.com/feed",           "Recorded Future"),
    ("https://flashpoint.io/feed/",                   "Flashpoint"),
    ("https://socradar.io/feed/",                     "SOCRadar"),
]


def _tor_available() -> bool:
    """Quick TCP connect to Tor SOCKS5 port."""
    try:
        with socket.create_connection((TOR_HOST, TOR_PORT), timeout=2):
            return True
    except OSError:
        return False


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


def _infer_severity(title: str) -> str:
    tl = title.lower()
    if any(w in tl for w in ["ransomware", "critical", "breach", "zero-day", "exploit"]):
        return "critical"
    if any(w in tl for w in ["high", "leak", "credential", "malware"]):
        return "high"
    return "medium"


async def _ingest_clearnet(session: AsyncSession) -> int:
    inserted = 0
    for feed_url, source_name in CLEARNET_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:20]:
                title = getattr(entry, "title", "").strip()
                if not title:
                    continue
                desc = _clean(getattr(entry, "summary", "") or "")
                url = getattr(entry, "link", None)
                pub = _parse_date(entry)

                try:
                    await session.execute(
                        text("""
                            INSERT INTO osint_signals
                              (source, type, severity, title, description, url, published_at)
                            VALUES
                              (:source, 'darkweb', :severity, :title, :desc, :url, :pub)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "source":   "darkweb-news",
                            "severity": _infer_severity(title),
                            "title":    f"[{source_name}] {title}",
                            "desc":     desc,
                            "url":      url,
                            "pub":      pub,
                        },
                    )
                    inserted += 1
                except Exception as e:
                    logger.debug("Darkweb skip %s: %s", source_name, e)
        except Exception as e:
            logger.warning("Darkweb clearnet feed error %s: %s", feed_url, e)
    return inserted


async def _fetch_via_tor(url: str) -> Optional[str]:
    """Fetch content through Tor SOCKS5 proxy. Returns None on failure."""
    try:
        from aiohttp_socks import ProxyConnector  # type: ignore
        connector = ProxyConnector.from_url(f"socks5://{TOR_HOST}:{TOR_PORT}")
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                return await resp.text()
    except Exception as e:
        logger.debug("Tor fetch failed for %s: %s", url, e)
        return None


async def _ingest_tor(session: AsyncSession) -> int:
    """Fetch .onion RSS feeds via Tor. No-op if Tor is unavailable."""
    # These are legitimate read-only dark web monitoring sources
    onion_rss_feeds = [
        # Dread forum RSS (dark web Reddit equivalent) — public, read-only
        "http://dreadytofatroptsdj6io7l3xptbet6onoyno2yv7jicoxknyazubrad.onion/rss",
    ]
    inserted = 0
    for feed_url in onion_rss_feeds:
        raw = await _fetch_via_tor(feed_url)
        if not raw:
            continue
        try:
            feed = feedparser.parse(raw)
            for entry in feed.entries[:15]:
                title = getattr(entry, "title", "").strip()
                if not title:
                    continue
                desc = _clean(getattr(entry, "summary", "") or "")
                url = getattr(entry, "link", None)
                pub = _parse_date(entry)

                try:
                    await session.execute(
                        text("""
                            INSERT INTO osint_signals
                              (source, type, severity, title, description, url, published_at)
                            VALUES
                              ('tor', 'darkweb', :severity, :title, :desc, :url, :pub)
                            ON CONFLICT DO NOTHING
                        """),
                        {
                            "severity": _infer_severity(title),
                            "title":    title,
                            "desc":     desc,
                            "url":      url,
                            "pub":      pub,
                        },
                    )
                    inserted += 1
                except Exception as e:
                    logger.debug("Tor signal skip: %s", e)
        except Exception as e:
            logger.warning("Tor feed parse error %s: %s", feed_url, e)
    return inserted


async def fetch_darkweb(session: AsyncSession) -> int:
    tor_up = _tor_available()
    logger.info("[darkweb] Tor available: %s", tor_up)

    total = await _ingest_clearnet(session)

    if tor_up:
        total += await _ingest_tor(session)

    await session.commit()
    logger.info("Darkweb: inserted %d signals", total)
    return total
