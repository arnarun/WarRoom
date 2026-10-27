"""Startup migrations and periodic data retention."""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import config
from database import engine
from models import Base

logger = logging.getLogger(__name__)

# Idempotent — safe to run on every boot (local, Docker, Railway)
_MIGRATIONS = [
    # UTC defaults (tables created by create_all previously had no server default)
    "ALTER TABLE articles      ALTER COLUMN fetched_at SET DEFAULT timezone('utc', now())",
    "ALTER TABLE osint_signals ALTER COLUMN fetched_at SET DEFAULT timezone('utc', now())",
    "ALTER TABLE social_posts  ALTER COLUMN fetched_at SET DEFAULT timezone('utc', now())",
    "ALTER TABLE market_prices ALTER COLUMN updated_at SET DEFAULT timezone('utc', now())",
    # osint_signals had no unique key, so ON CONFLICT never fired and every run
    # re-inserted the same items. Collapse duplicates, then enforce uniqueness.
    """
    DELETE FROM osint_signals a
     USING osint_signals b
     WHERE a.source = b.source AND a.url = b.url AND a.id > b.id
       AND NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'uq_osint_source_url')
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_osint_source_url ON osint_signals(source, url)",
    "CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_osint_fetched    ON osint_signals(fetched_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_social_fetched   ON social_posts(fetched_at DESC)",
    # Future-dated items (event announcements) used to pin themselves to the top
    """
    UPDATE articles SET published_at = COALESCE(fetched_at, timezone('utc', now()))
     WHERE published_at > timezone('utc', now()) + interval '1 hour'
    """,
]


async def migrate() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _MIGRATIONS:
            await conn.execute(text(stmt))
    logger.info("Database schema ready (%d migrations applied)", len(_MIGRATIONS))


async def prune_old_data(session: AsyncSession) -> int:
    """Delete rows past their retention window so tables don't grow unbounded."""
    plan = [
        ("articles",      config.RETENTION_DAYS_ARTICLES),
        ("osint_signals", config.RETENTION_DAYS_OSINT),
        ("social_posts",  config.RETENTION_DAYS_SOCIAL),
    ]
    total = 0
    for table, days in plan:
        if days <= 0:
            continue
        result = await session.execute(
            text(f"""
                DELETE FROM {table}
                 WHERE COALESCE(fetched_at, published_at) < timezone('utc', now()) - make_interval(days => :days)
            """),
            {"days": days},
        )
        logger.info("Retention: pruned %d rows from %s (> %d days)", result.rowcount, table, days)
        total += result.rowcount
    await session.commit()
    return total
