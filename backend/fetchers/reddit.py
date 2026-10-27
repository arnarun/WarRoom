"""Reddit fetcher — PRAW → social_posts. Skipped gracefully if no credentials."""
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import config
from fetchers.common import from_timestamp

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "worldnews", "geopolitics", "investing",
    "technology", "startups", "venturecapital", "entrepreneur",
]


async def fetch_reddit(session: AsyncSession) -> int:
    if not config.REDDIT_CLIENT_ID or not config.REDDIT_CLIENT_SECRET:
        logger.info("Reddit: no credentials, skipping")
        return 0

    try:
        import praw
    except ImportError:
        logger.warning("praw not installed")
        return 0

    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
    )

    def _hot(sub_name):
        # PRAW is synchronous — run it off the event loop
        return [
            {
                "sub":      sub_name,
                "title":    post.title,
                "url":      f"https://reddit.com{post.permalink}",
                "score":    post.score,
                "comments": post.num_comments,
                "pub":      from_timestamp(post.created_utc),
            }
            for post in reddit.subreddit(sub_name).hot(limit=25)
        ]

    inserted = 0
    for sub_name in SUBREDDITS:
        try:
            posts = await asyncio.to_thread(_hot, sub_name)
        except Exception as e:
            logger.warning("Reddit r/%s error: %s", sub_name, e)
            continue
        for row in posts:
            try:
                await session.execute(
                    text("""
                        INSERT INTO social_posts
                          (platform, community, title, url, score, num_comments, published_at)
                        VALUES
                          ('reddit', :sub, :title, :url, :score, :comments, :pub)
                        ON CONFLICT (url) DO UPDATE SET
                          score=EXCLUDED.score, num_comments=EXCLUDED.num_comments
                    """),
                    row,
                )
                inserted += 1
            except Exception as e:
                logger.debug("Reddit insert skip: %s", e)

    await session.commit()
    logger.info("Reddit: upserted %d posts", inserted)
    return inserted
