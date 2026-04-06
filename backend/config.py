import os
from dotenv import load_dotenv

load_dotenv()

_raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://arunaachalam@localhost:5432/warroom"
)
# Railway provides postgresql:// — asyncpg needs postgresql+asyncpg://
if _raw_db_url.startswith("postgresql://"):
    _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = _raw_db_url

# Set DATABASE_SSL=true on Railway (internal connections may still need SSL)
DATABASE_SSL = os.getenv("DATABASE_SSL", "false").lower() == "true"

# CORS allowed origins — use * for Railway or comma-separated list
CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",")]

GUARDIAN_API_KEY   = os.getenv("GUARDIAN_API_KEY", "")
NEWSDATA_API_KEY   = os.getenv("NEWSDATA_API_KEY", "")
ALPHA_VANTAGE_KEY  = os.getenv("ALPHA_VANTAGE_KEY", "")
ACLED_API_KEY      = os.getenv("ACLED_API_KEY", "")
REDDIT_CLIENT_ID   = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT  = os.getenv("REDDIT_USER_AGENT", "WarRoom/1.0")
CRUNCHBASE_API_KEY = os.getenv("CRUNCHBASE_API_KEY", "")

# Fetch intervals (seconds)
INTERVAL_RSS           = 900   # 15 min — full RSS sweep
INTERVAL_BREAKING      = 300   # 5 min  — breaking/high-priority sources only
INTERVAL_MARKET_CRYPTO = 60    # 1 min
INTERVAL_MARKET_STOCKS = 300   # 5 min
INTERVAL_HN            = 900   # 15 min
INTERVAL_OSINT         = 1800  # 30 min
INTERVAL_NVD           = 1800  # 30 min — NVD CVE feed
INTERVAL_SOCIAL        = 1800  # 30 min
INTERVAL_GDELT         = 1800  # 30 min
