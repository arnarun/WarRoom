# WarRoom — Global Intelligence Dashboard

A self-hosted dashboard aggregating OSINT signals, global news, live market prices, and social sentiment.

## Quick Start (Mac Local)

### 1. Backend
```bash
cd WarRoom/backend
cp ../.env.example ../.env   # add API keys (optional for Phase 1)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd WarRoom/frontend
npm install
npm run dev      # → http://localhost:5173
```

### 3. Database
```bash
# DB already created via schema.sql. To re-create:
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
psql -U $USER -d warroom -f backend/schema.sql
```

## Verify
```bash
curl http://localhost:8000/api/health          # {"status":"ok"}
curl http://localhost:8000/api/articles        # JSON array (fills after ~60s)
curl http://localhost:8000/api/market          # prices
curl http://localhost:8000/api/osint           # signals
curl -N http://localhost:8000/api/stream/prices # SSE stream
```

## API Keys (Optional — more sources)
Copy `.env.example` to `.env` and fill in:
- `GUARDIAN_API_KEY`   — https://open-platform.theguardian.com
- `NEWSDATA_API_KEY`   — https://newsdata.io
- `REDDIT_CLIENT_ID`   — https://www.reddit.com/prefs/apps
- `REDDIT_CLIENT_SECRET`

No key needed: CoinGecko, yfinance, Hacker News, abuse.ch, CISA RSS, GDELT.

## VPS Deployment (Docker)
```bash
cp .env.example .env   # fill in keys
docker compose up -d
# → frontend at :5173, backend at :8000
```

## Data Sources (Phase 1)
- **53 RSS feeds** — BBC, Reuters, Al Jazeera, FT, WSJ, TechCrunch, Ars Technica, etc.
- **CISA** — US cybersecurity alerts
- **abuse.ch** — URLhaus + MalwareBazaar threat intel
- **Hacker News** — Top/Show/Ask HN via Firebase API
- **CoinGecko** — 10 crypto prices (1-min refresh)
- **yfinance** — 14 stocks/ETFs + forex (5-min refresh)
- **GDELT** — Global events & tone
- **Reddit/StockTwits** — social sentiment (needs credentials)
