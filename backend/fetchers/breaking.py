"""Breaking news RSS fetcher — polls only high-priority sources every 5 minutes."""
from __future__ import annotations
import logging

from sqlalchemy.ext.asyncio import AsyncSession as DBSession

from fetchers.rss import ingest_sources, load_sources

logger = logging.getLogger(__name__)


async def fetch_breaking_rss(session: DBSession) -> int:
    breaking = [s for s in load_sources() if s.get("breaking")]
    stats = await ingest_sources(session, breaking, max_entries=10)
    logger.info("Breaking RSS: checked %d sources, inserted %d articles",
                len(breaking), stats["inserted"])
    return stats["inserted"]
