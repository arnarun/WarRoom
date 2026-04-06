"""Hacker News fetcher — Firebase API, top/new/ask/show stories."""
import asyncio
import logging
from datetime import datetime

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

HN_BASE  = "https://hacker-news.firebaseio.com/v0"
ITEM_URL = HN_BASE + "/item/{id}.json"
FEEDS    = {
    "topstories":  HN_BASE + "/topstories.json",
    "showstories": HN_BASE + "/showstories.json",
    "askstories":  HN_BASE + "/askstories.json",
}
LIMIT = 30


async def _get_json(session: aiohttp.ClientSession, url: str):
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        return await resp.json()


async def fetch_hackernews(db: AsyncSession) -> int:
    inserted = 0
    async with aiohttp.ClientSession() as http:
        for feed_name, feed_url in FEEDS.items():
            try:
                ids = await _get_json(http, feed_url)
                ids = ids[:LIMIT]
                tasks = [_get_json(http, ITEM_URL.format(id=i)) for i in ids]
                items = await asyncio.gather(*tasks, return_exceptions=True)
                for item in items:
                    if isinstance(item, Exception) or not item:
                        continue
                    title = item.get("title", "").strip()
                    url   = item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}"
                    score = item.get("score", 0)
                    comments = item.get("descendants", 0)
                    ts    = item.get("time")
                    pub   = datetime.utcfromtimestamp(ts) if ts else None
                    try:
                        await db.execute(
                            text("""
                                INSERT INTO social_posts
                                  (platform, community, title, url, score, num_comments, published_at)
                                VALUES
                                  ('hackernews', :community, :title, :url, :score, :comments, :pub)
                                ON CONFLICT (url) DO UPDATE SET
                                  score=EXCLUDED.score, num_comments=EXCLUDED.num_comments
                            """),
                            {
                                "community": feed_name,
                                "title":     title,
                                "url":       url,
                                "score":     score,
                                "comments":  comments,
                                "pub":       pub,
                            },
                        )
                        inserted += 1
                    except Exception as e:
                        logger.debug("HN insert skip: %s", e)
            except Exception as e:
                logger.warning("HN feed %s error: %s", feed_name, e)
    await db.commit()
    logger.info("HN: upserted %d posts", inserted)
    return inserted
