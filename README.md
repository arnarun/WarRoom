# WarRoom — Global Intelligence Dashboard

A self-hosted dashboard aggregating OSINT signals, global news, live market prices, and social sentiment.

## Requirements
- Python **3.13** (managed via [uv](https://docs.astral.sh/uv/) locally; Docker image uses `python:3.13-slim`)
- Node **20.19+ / 22.12+** (Vite 8); Docker image uses `node:24-alpine`
- PostgreSQL 16

## Quick Start (Mac Local)

### 1. Backend
```bash
cd WarRoom/backend
cp ../.env.example ../.env   # API keys are optional
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn main:app --reload --port 8000
```
Schema creation and migrations run automatically on startup (`maintenance.py`).

### 2. Frontend
```bash
cd WarRoom/frontend
npm install
npm run dev      # → http://localhost:5173
```

## Verify
```bash
curl http://localhost:8000/api/health          # {"status":"ok","db":"up",...}
curl http://localhost:8000/api/status          # per-fetcher runs, failing feeds, table sizes
curl http://localhost:8000/api/articles        # JSON array (fills after ~20s)
curl http://localhost:8000/api/market          # prices
curl http://localhost:8000/api/osint           # signals
```

## Features
- **Feed** — one column per category, hot-topics carousel, debounced search (press `/`), NEW badges for articles fetched since your last visit
- **Market / OSINT / Social** — prices, CERT alerts, CVEs, malware, breaches, dark-web news, HN/Reddit/StockTwits
- **Saved** — star any article to keep it (stored in your browser)
- **Status** — fetcher health, last run/duration/new rows, failing & empty RSS feeds, data freshness; health dot in the footer

## Configuration
See `.env.example`. Notable settings:
- `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` — allowed frontend origins (API is GET-only)
- `RETENTION_DAYS_ARTICLES` / `_OSINT` / `_SOCIAL` — old rows are pruned every 6h
- `GUARDIAN_API_KEY`, `NEWSDATA_API_KEY`, `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` — optional sources
- `NVD_API_KEY`, `ABUSECH_AUTH_KEY`, `OTX_API_KEY` — free keys; without them NVD is throttled and URLhaus/MalwareBazaar/OTX are skipped

No key needed: CoinGecko, yfinance, Hacker News, StockTwits, CISA (alerts + KEV), NCSC/ENISA/BSI, NVD, Feodo Tracker, GDELT.

## VPS Deployment (Docker)
```bash
cp .env.example .env   # set POSTGRES_PASSWORD and keys
docker compose up -d
# → frontend at :5173, backend at :8000 (Postgres bound to 127.0.0.1:5433)
```
Containers run as non-root (backend), with health checks and security headers (nginx CSP, nosniff, frame-deny).

## Data Sources
- **106 RSS feeds** (`backend/sources.json`) — fetched concurrently every 15 min; `breaking: true` sources every 5 min
- **CISA / NCSC / ENISA / BSI** — CERT alerts
- **NVD** — CVEs from the last 7 days; **CISA KEV** — actively exploited CVEs
- **abuse.ch** — Feodo Tracker botnet C2s; URLhaus + MalwareBazaar with `ABUSECH_AUTH_KEY`
- **AlienVault OTX** (with `OTX_API_KEY`), breach trackers, clearnet dark-web news (+ Tor feeds if a local Tor proxy is running)
- **Hacker News**, **Reddit** (needs credentials), **StockTwits**
- **CoinGecko** (1 min), **yfinance** stocks/ETFs/forex (5 min)
- **GDELT** — global events (requests spaced ≥5s apart per GDELT's limit)
