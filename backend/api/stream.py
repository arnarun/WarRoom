"""Server-Sent Events endpoint for live market price streaming."""
import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models import MarketPrice

router = APIRouter()
logger = logging.getLogger(__name__)


async def _price_generator():
    while True:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MarketPrice).order_by(MarketPrice.updated_at.desc())
                )
                rows = result.scalars().all()
                prices = [
                    {
                        "symbol":     r.symbol,
                        "type":       r.type,
                        "name":       r.name,
                        "price":      float(r.price),
                        "change_24h": r.change_24h,
                        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    }
                    for r in rows
                ]
                yield f"data: {json.dumps(prices)}\n\n"
        except Exception as e:
            logger.error("SSE error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(30)


@router.get("/stream/prices")
async def stream_prices():
    return StreamingResponse(
        _price_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
