"""RSS fetcher — reads sources.json, parses feeds, upserts into articles table."""
from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path

import feedparser
from curl_cffi.requests import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession as DBSession

from fetchers.common import clean_text, get_entry_image, parse_entry_date, safe_url, utcnow
from models import Article

logger = logging.getLogger(__name__)

SOURCES_PATH = Path(__file__).parent.parent / "sources.json"

# Feeds are fetched concurrently; DB writes stay sequential on one session
CONCURRENCY = 12

# Outcome of the last full sweep — surfaced on /api/status for spotting dead feeds
LAST_SWEEP: dict = {}

# RETURNING gives an accurate count of genuinely new rows per batch
_INSERT = (
    insert(Article)
    .on_conflict_do_nothing(index_elements=["url"])
    .returning(Article.id)
)


def load_sources() -> list[dict]:
    return json.loads(SOURCES_PATH.read_text())


async def _download(http: AsyncSession, sem: asyncio.Semaphore, src: dict):
    """Return (src, feed) or (src, None) on failure. Never raises."""
    async with sem:
        try:
            resp = await http.get(src["url"], timeout=15)
        except Exception as e:
            logger.warning("RSS fetch failed %s: %s", src["name"], e)
            return src, None
    if resp.status_code >= 400:
        logger.warning("RSS %s HTTP %d", src["name"], resp.status_code)
        return src, None
    feed = feedparser.parse(resp.content)
    if not feed.entries:
        preview = resp.text[:120].replace("\n", " ").strip()
        logger.warning("RSS 0 entries %s — content preview: %s", src["name"], preview)
    return src, feed


def _rows(src: dict, feed, max_entries: int) -> list[dict]:
    rows = []
    for entry in feed.entries[:max_entries]:
        url   = safe_url(getattr(entry, "link", None))
        title = clean_text(getattr(entry, "title", ""), 1000)
        if not url or not title:
            continue
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        rows.append({
            "source":       src["name"],
            "category":     src.get("category"),
            "region":       src.get("region"),
            "country":      src.get("country"),
            "title":        title,
            "summary":      clean_text(summary),
            "url":          url,
            "image_url":    get_entry_image(entry),
            "published_at": parse_entry_date(entry),
            "tags":         src.get("tags"),
        })
    return rows


async def ingest_sources(session: DBSession, sources: list[dict], max_entries: int = 30) -> dict:
    """Fetch the given sources concurrently and insert new articles. Returns stats."""
    sem = asyncio.Semaphore(CONCURRENCY)
    async with AsyncSession(impersonate="chrome") as http:
        results = await asyncio.gather(*[_download(http, sem, s) for s in sources])

    stats = {"inserted": 0, "ok": 0, "empty": 0, "fail": 0, "failing": [], "empty_sources": []}
    for src, feed in results:
        if feed is None:
            stats["fail"] += 1
            stats["failing"].append(src["name"])
            continue
        rows = _rows(src, feed, max_entries)
        if not rows:
            stats["empty"] += 1
            stats["empty_sources"].append(src["name"])
            continue
        stats["ok"] += 1
        try:
            result = await session.execute(_INSERT, rows)
            stats["inserted"] += len(result.all())
            await session.commit()
        except Exception as e:
            await session.rollback()
            stats["fail"] += 1
            stats["failing"].append(src["name"])
            logger.warning("RSS insert failed %s: %s", src["name"], e)
    return stats


async def fetch_all_rss(session: DBSession) -> int:
    sources = load_sources()
    stats = await ingest_sources(session, sources)
    LAST_SWEEP.clear()
    LAST_SWEEP.update(stats, total=len(sources), at=utcnow().isoformat() + "Z")
    logger.info("RSS: inserted %d articles (ok=%d empty=%d fail=%d)",
                stats["inserted"], stats["ok"], stats["empty"], stats["fail"])
    return stats["inserted"]
