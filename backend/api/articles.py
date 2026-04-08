from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Article
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/articles")
async def get_articles(
    category: Optional[str] = Query(None),
    region:   Optional[str] = Query(None),
    country:  Optional[str] = Query(None),
    source:   Optional[str] = Query(None),
    q:        Optional[str] = Query(None),
    hours:    Optional[int] = Query(None, le=168),
    limit:    int           = Query(500, le=1000),
    offset:   int           = Query(0),
    db:       AsyncSession  = Depends(get_db),
):
    stmt = select(Article).order_by(Article.published_at.desc().nulls_last())

    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = stmt.where(Article.published_at >= since)
    if category:
        stmt = stmt.where(Article.category == category)
    if region:
        stmt = stmt.where(Article.region == region)
    if country:
        stmt = stmt.where(Article.country.ilike(country))
    if source:
        stmt = stmt.where(Article.source.ilike(f"%{source}%"))
    if q:
        stmt = stmt.where(
            (Article.title.ilike(f"%{q}%")) | (Article.summary.ilike(f"%{q}%"))
        )

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id":           r.id,
            "source":       r.source,
            "category":     r.category,
            "region":       r.region,
            "country":      r.country,
            "title":        r.title,
            "summary":      r.summary,
            "url":          r.url,
            "image_url":    r.image_url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "fetched_at":   r.fetched_at.isoformat()   if r.fetched_at   else None,
            "tags":         r.tags or [],
        }
        for r in rows
    ]


@router.get("/articles/hot")
async def get_hot_articles(
    hours: int           = Query(6, le=24),
    limit: int           = Query(50, le=100),
    db:    AsyncSession  = Depends(get_db),
):
    """Most recent articles from the last N hours — used for the hot topics banner."""
    since = datetime.utcnow() - timedelta(hours=hours)
    stmt  = (
        select(Article)
        .where(Article.published_at >= since)
        .order_by(Article.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows   = result.scalars().all()
    return [
        {
            "id":           r.id,
            "source":       r.source,
            "category":     r.category,
            "country":      r.country,
            "title":        r.title,
            "summary":      r.summary,
            "url":          r.url,
            "image_url":    r.image_url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }
        for r in rows
    ]


@router.get("/articles/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT DISTINCT category FROM articles WHERE category IS NOT NULL ORDER BY category")
    )
    return [row[0] for row in result.fetchall()]


@router.get("/articles/sources")
async def get_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT DISTINCT source FROM articles ORDER BY source")
    )
    return [row[0] for row in result.fetchall()]
