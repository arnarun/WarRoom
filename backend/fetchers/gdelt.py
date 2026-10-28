"""GDELT DOC 2.0 API fetcher → articles table."""
import asyncio
import json
import logging
from datetime import datetime

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fetchers.common import SSL_CONTEXT

logger = logging.getLogger(__name__)

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
# GDELT rejects more than one request per 5 seconds with a plain-text error
GDELT_SPACING_S = 6

QUERIES = [
    {"query": "geopolitics conflict",    "category": "geopolitics", "region": "global"},
    {"query": "technology startups AI",  "category": "technology",  "region": "global"},
    {"query": "financial markets economy", "category": "business",  "region": "global"},
    {"query": "cybersecurity hack breach", "category": "security",  "region": "global"},
]


async def fetch_gdelt(session: AsyncSession) -> int:
    inserted = 0
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
        for i, q in enumerate(QUERIES):
            if i:
                await asyncio.sleep(GDELT_SPACING_S)
            try:
                params = {
                    "query":      q["query"],
                    "mode":       "artlist",
                    "maxrecords": "25",
                    "format":     "json",
                    "sort":       "DateDesc",
                }
                async with http.get(
                    GDELT_API, params=params, timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    body = await resp.text(errors="replace")
                if body.startswith("Please limit requests"):
                    # IP-wide limit; more queries now only extend the penalty
                    logger.warning("GDELT rate-limited — skipping remaining queries this cycle")
                    break
                data = json.loads(body)

                for art in (data.get("articles") or []):
                    url   = art.get("url", "")
                    title = art.get("title", "").strip()
                    if not url or not title:
                        continue
                    pub_str = art.get("seendate", "")
                    pub = None
                    if pub_str:
                        try:
                            pub = datetime.strptime(pub_str[:14], "%Y%m%dT%H%M%S")
                        except Exception:
                            pass
                    try:
                        await session.execute(
                            text("""
                                INSERT INTO articles
                                  (source, category, region, title, image_url, url, published_at)
                                VALUES
                                  ('GDELT', :cat, :region, :title, :image, :url, :pub)
                                ON CONFLICT (url) DO NOTHING
                            """),
                            {
                                "cat":     q["category"],
                                "region":  q["region"],
                                "title":   title,
                                "image":   art.get("socialimage") or None,
                                "url":     url,
                                "pub":     pub,
                            },
                        )
                        inserted += 1
                    except Exception as e:
                        logger.debug("GDELT insert skip: %s", e)
            except Exception as e:
                logger.warning("GDELT query '%s' error: %s", q["query"], e)
    await session.commit()
    logger.info("GDELT: inserted %d articles", inserted)
    return inserted
