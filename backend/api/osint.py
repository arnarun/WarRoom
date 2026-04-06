from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import OsintSignal
from typing import Optional

router = APIRouter()


@router.get("/osint")
async def get_osint(
    source:   Optional[str] = Query(None),
    type:     Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    country:  Optional[str] = Query(None),
    limit:    int           = Query(50, le=200),
    offset:   int           = Query(0),
    db:       AsyncSession  = Depends(get_db),
):
    stmt = select(OsintSignal).order_by(OsintSignal.published_at.desc().nulls_last())
    if source:
        stmt = stmt.where(OsintSignal.source == source)
    if type:
        stmt = stmt.where(OsintSignal.type == type)
    if severity:
        stmt = stmt.where(OsintSignal.severity == severity)
    if country:
        stmt = stmt.where(OsintSignal.country.ilike(country))
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id":           r.id,
            "source":       r.source,
            "type":         r.type,
            "severity":     r.severity,
            "title":        r.title,
            "description":  r.description,
            "url":          r.url,
            "country":      r.country,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "fetched_at":   r.fetched_at.isoformat()   if r.fetched_at   else None,
        }
        for r in rows
    ]
