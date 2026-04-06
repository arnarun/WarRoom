-- WarRoom Database Schema
-- Run: psql warroom -f schema.sql

CREATE TABLE IF NOT EXISTS articles (
  id           SERIAL PRIMARY KEY,
  source       VARCHAR(100) NOT NULL,
  category     VARCHAR(50),           -- business, politics, geopolitics, tech, security, startups, venture-capital
  region       VARCHAR(50),           -- global, us, eu, asia, middle-east, etc.
  title        TEXT NOT NULL,
  summary      TEXT,
  url          TEXT UNIQUE NOT NULL,
  image_url    TEXT,
  published_at TIMESTAMP,
  fetched_at   TIMESTAMP DEFAULT NOW(),
  tags         TEXT[],
  country      VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_articles_category  ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_source    ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_country   ON articles(country);

CREATE TABLE IF NOT EXISTS market_prices (
  symbol      VARCHAR(20) PRIMARY KEY,
  type        VARCHAR(20) NOT NULL,  -- crypto, stock, forex
  name        VARCHAR(100),
  price       NUMERIC(20,8) NOT NULL,
  change_1h   FLOAT,
  change_24h  FLOAT,
  change_7d   FLOAT,
  volume_24h  FLOAT,
  market_cap  FLOAT,
  updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS osint_signals (
  id           SERIAL PRIMARY KEY,
  source       VARCHAR(50) NOT NULL,  -- cisa, urlhaus, malwarebazaar, acled
  type         VARCHAR(50) NOT NULL,  -- cyber-threat, conflict, malware, phishing
  severity     VARCHAR(20),           -- critical, high, medium, low
  title        TEXT NOT NULL,
  description  TEXT,
  url          TEXT,
  country      VARCHAR(100),
  published_at TIMESTAMP,
  fetched_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_osint_source    ON osint_signals(source);
CREATE INDEX IF NOT EXISTS idx_osint_type      ON osint_signals(type);
CREATE INDEX IF NOT EXISTS idx_osint_published ON osint_signals(published_at DESC);

CREATE TABLE IF NOT EXISTS social_posts (
  id           SERIAL PRIMARY KEY,
  platform     VARCHAR(30) NOT NULL,  -- reddit, hackernews, stocktwits
  community    VARCHAR(100),          -- subreddit name or HN
  title        TEXT NOT NULL,
  url          TEXT UNIQUE,
  score        INTEGER,
  num_comments INTEGER,
  sentiment    VARCHAR(20),           -- bullish, bearish, neutral or null
  published_at TIMESTAMP,
  fetched_at   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_social_platform  ON social_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_published ON social_posts(published_at DESC);
