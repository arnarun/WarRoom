import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import MarketPrice
from typing import Optional


def _f(v):
    """Convert float to None if NaN/Infinity — JSON can't serialize those."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return None

router = APIRouter()


@router.get("/market")
async def get_market(
    type: Optional[str] = Query(None),  # crypto, stock, forex
    db:   AsyncSession  = Depends(get_db),
):
    stmt = select(MarketPrice).order_by(MarketPrice.updated_at.desc())
    if type:
        stmt = stmt.where(MarketPrice.type == type)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "symbol":     r.symbol,
            "type":       r.type,
            "name":       r.name,
            "price":      _f(r.price),
            "change_1h":  _f(r.change_1h),
            "change_24h": _f(r.change_24h),
            "change_7d":  _f(r.change_7d),
            "volume_24h": _f(r.volume_24h),
            "market_cap": _f(r.market_cap),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
