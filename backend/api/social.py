from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import SocialPost
from typing import Optional

router = APIRouter()


@router.get("/social")
async def get_social(
    platform:  Optional[str] = Query(None),
    community: Optional[str] = Query(None),
    limit:     int           = Query(50, ge=1, le=500),
    offset:    int           = Query(0, ge=0),
    db:        AsyncSession  = Depends(get_db),
):
    stmt = select(SocialPost).order_by(SocialPost.published_at.desc().nulls_last())
    if platform:
        stmt = stmt.where(SocialPost.platform == platform)
    if community:
        stmt = stmt.where(SocialPost.community == community)
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id":           r.id,
            "platform":     r.platform,
            "community":    r.community,
            "title":        r.title,
            "url":          r.url,
            "score":        r.score,
            "num_comments": r.num_comments,
            "sentiment":    r.sentiment,
            "published_at": (r.published_at.isoformat() + "Z") if r.published_at else None,
            "fetched_at":   (r.fetched_at.isoformat()   + "Z") if r.fetched_at   else None,
        }
        for r in rows
    ]
