"""StockTwits fetcher — trending + symbol streams → social_posts."""
import logging
from datetime import datetime

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SYMBOLS = ["SPY", "AAPL", "NVDA", "BTC.X", "ETH.X", "TSLA"]
ST_TRENDING = "https://api.stocktwits.com/api/2/trending/symbols.json"
ST_STREAM   = "https://api.stocktwits.com/api/2/streams/symbol/{sym}.json"


async def fetch_stocktwits(session: AsyncSession) -> int:
    inserted = 0
    async with aiohttp.ClientSession() as http:
        for sym in SYMBOLS:
            try:
                url = ST_STREAM.format(sym=sym)
                async with http.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json(content_type=None)

                for msg in (data.get("messages") or [])[:10]:
                    body = msg.get("body", "").strip()
                    if not body:
                        continue
                    sentiment = None
                    ent = msg.get("entities", {}).get("sentiment")
                    if ent:
                        sentiment = ent.get("basic", "").lower() or None

                    created = msg.get("created_at", "")
                    pub = None
                    if created:
                        try:
                            pub = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                        except Exception:
                            pass

                    st_url = f"https://stocktwits.com/message/{msg.get('id', '')}"
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO social_posts
                                  (platform, community, title, url, score, sentiment, published_at)
                                VALUES
                                  ('stocktwits', :sym, :title, :url, :likes, :sent, :pub)
                                ON CONFLICT (url) DO UPDATE SET
                                  score=EXCLUDED.score
                            """),
                            {
                                "sym":   sym,
                                "title": body[:500],
                                "url":   st_url,
                                "likes": msg.get("likes", {}).get("total", 0),
                                "sent":  sentiment,
                                "pub":   pub,
                            },
                        )
                        inserted += 1
                    except Exception as e:
                        logger.debug("StockTwits insert skip: %s", e)
            except Exception as e:
                logger.warning("StockTwits %s error: %s", sym, e)

    await session.commit()
    logger.info("StockTwits: upserted %d posts", inserted)
    return inserted
