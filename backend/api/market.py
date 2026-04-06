from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import MarketPrice
from typing import Optional

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
            "price":      float(r.price),
            "change_1h":  r.change_1h,
            "change_24h": r.change_24h,
            "change_7d":  r.change_7d,
            "volume_24h": r.volume_24h,
            "market_cap": r.market_cap,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
