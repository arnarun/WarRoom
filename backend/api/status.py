"""Health and fetcher-status endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import jobs
from fetchers.rss import LAST_SWEEP
from database import get_db

router = APIRouter()

VERSION = "1.1.0"


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "degraded", "db": "down", "version": VERSION}, status_code=503)
    return {"status": "ok", "db": "up", "version": VERSION}


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    """Per-job run history plus table sizes and data freshness."""
    result = await db.execute(text("""
        SELECT 'articles' AS t, count(*), max(COALESCE(fetched_at, published_at)) FROM articles
        UNION ALL SELECT 'osint_signals', count(*), max(COALESCE(fetched_at, published_at)) FROM osint_signals
        UNION ALL SELECT 'social_posts',  count(*), max(COALESCE(fetched_at, published_at)) FROM social_posts
        UNION ALL SELECT 'market_prices', count(*), max(updated_at) FROM market_prices
    """))
    tables = {
        name: {"rows": count, "latest": (latest.isoformat() + "Z") if latest else None}
        for name, count, latest in result.fetchall()
    }
    return {"version": VERSION, "jobs": jobs.snapshot(), "tables": tables, "rss": LAST_SWEEP}
