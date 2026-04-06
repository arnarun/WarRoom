"""WarRoom — FastAPI backend with APScheduler for periodic data fetching."""
import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

import config
from database import AsyncSessionLocal
from fetchers.rss        import fetch_all_rss
from fetchers.market     import fetch_crypto, fetch_stocks
from fetchers.hackernews import fetch_hackernews
from fetchers.cisa       import fetch_cisa
from fetchers.abusech    import fetch_abusech
from fetchers.gdelt      import fetch_gdelt
from fetchers.reddit     import fetch_reddit
from fetchers.stocktwits import fetch_stocktwits
from fetchers.alienvault import fetch_alienvault
from fetchers.breach     import fetch_breach
from fetchers.darkweb    import fetch_darkweb
from fetchers.nvd        import fetch_nvd
from fetchers.breaking   import fetch_breaking_rss
from api.articles import router as articles_router
from api.market   import router as market_router
from api.osint    import router as osint_router
from api.social   import router as social_router
from api.stream   import router as stream_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run(fetcher, *args):
    """Wrap a fetcher in a fresh DB session."""
    name = fetcher.__name__
    logger.info("[scheduler] Starting %s", name)
    try:
        async with AsyncSessionLocal() as session:
            await fetcher(session, *args)
        logger.info("[scheduler] Finished %s", name)
    except Exception as exc:
        logger.error("[scheduler] %s FAILED: %s", name, exc, exc_info=True)


def _schedule_job(fetcher, interval_seconds: int, run_now: bool = True):
    if run_now:
        scheduler.add_job(_run, "date", args=[fetcher], misfire_grace_time=60)
    scheduler.add_job(
        _run, "interval", seconds=interval_seconds, args=[fetcher], misfire_grace_time=60
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WarRoom starting — scheduling fetchers…")

    _schedule_job(fetch_all_rss,      config.INTERVAL_RSS)
    _schedule_job(fetch_crypto,        config.INTERVAL_MARKET_CRYPTO)
    _schedule_job(fetch_stocks,        config.INTERVAL_MARKET_STOCKS)
    _schedule_job(fetch_hackernews,    config.INTERVAL_HN)
    _schedule_job(fetch_cisa,          config.INTERVAL_OSINT)
    _schedule_job(fetch_abusech,       config.INTERVAL_OSINT)
    _schedule_job(fetch_gdelt,         config.INTERVAL_GDELT)
    _schedule_job(fetch_reddit,        config.INTERVAL_SOCIAL)
    _schedule_job(fetch_stocktwits,    config.INTERVAL_SOCIAL)
    _schedule_job(fetch_alienvault,    config.INTERVAL_OSINT)
    _schedule_job(fetch_breach,        config.INTERVAL_OSINT)
    _schedule_job(fetch_darkweb,       config.INTERVAL_OSINT)
    _schedule_job(fetch_nvd,           config.INTERVAL_NVD)
    _schedule_job(fetch_breaking_rss,  config.INTERVAL_BREAKING)

    scheduler.start()
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="WarRoom Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.up\.railway\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response

app.add_middleware(NoCacheMiddleware)

app.include_router(articles_router, prefix="/api")
app.include_router(market_router,   prefix="/api")
app.include_router(osint_router,    prefix="/api")
app.include_router(social_router,   prefix="/api")
app.include_router(stream_router,   prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
