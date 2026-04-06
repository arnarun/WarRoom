"""Market data fetcher — CoinGecko (crypto) + yfinance history() (stocks/ETFs/forex)."""
import logging
from datetime import datetime

import yfinance as yf
from pycoingecko import CoinGeckoAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

cg = CoinGeckoAPI()

CRYPTO_IDS = [
    "bitcoin", "ethereum", "solana", "binancecoin", "ripple",
    "cardano", "avalanche-2", "polkadot", "chainlink", "dogecoin",
]

# Symbol → display name, type
STOCK_SYMBOLS = {
    "^GSPC":    ("S&P 500",  "stock"),
    "^DJI":     ("Dow Jones","stock"),
    "^IXIC":    ("NASDAQ",   "stock"),
    "GLD":      ("Gold",     "stock"),
    "SLV":      ("Silver",   "stock"),
    "AAPL":     ("Apple",    "stock"),
    "MSFT":     ("Microsoft","stock"),
    "NVDA":     ("NVIDIA",   "stock"),
    "TSLA":     ("Tesla",    "stock"),
    "AMZN":     ("Amazon",   "stock"),
    "GOOGL":    ("Alphabet", "stock"),
    "META":     ("Meta",     "stock"),
    "EURUSD=X": ("EUR/USD",  "forex"),
    "GBPUSD=X": ("GBP/USD",  "forex"),
    "JPYUSD=X": ("JPY/USD",  "forex"),
    "INRUSD=X": ("INR/USD",  "forex"),
}


async def fetch_crypto(session: AsyncSession) -> int:
    try:
        data = cg.get_coins_markets(
            vs_currency="usd",
            ids=",".join(CRYPTO_IDS),
            price_change_percentage="1h,24h,7d",
            per_page=len(CRYPTO_IDS),
        )
    except Exception as e:
        logger.error("CoinGecko error: %s", e)
        return 0

    inserted = 0
    for coin in data:
        try:
            await session.execute(
                text("""
                    INSERT INTO market_prices
                      (symbol, type, name, price, change_1h, change_24h, change_7d,
                       volume_24h, market_cap, updated_at)
                    VALUES
                      (:symbol, 'crypto', :name, :price, :ch1h, :ch24h, :ch7d,
                       :vol, :mcap, :updated_at)
                    ON CONFLICT (symbol) DO UPDATE SET
                      price=EXCLUDED.price, change_1h=EXCLUDED.change_1h,
                      change_24h=EXCLUDED.change_24h, change_7d=EXCLUDED.change_7d,
                      volume_24h=EXCLUDED.volume_24h, market_cap=EXCLUDED.market_cap,
                      updated_at=EXCLUDED.updated_at
                """),
                {
                    "symbol":     coin["symbol"].upper(),
                    "name":       coin["name"],
                    "price":      float(coin.get("current_price") or 0),
                    "ch1h":       coin.get("price_change_percentage_1h_in_currency"),
                    "ch24h":      coin.get("price_change_percentage_24h"),
                    "ch7d":       coin.get("price_change_percentage_7d_in_currency"),
                    "vol":        coin.get("total_volume"),
                    "mcap":       coin.get("market_cap"),
                    "updated_at": datetime.utcnow(),
                },
            )
            inserted += 1
        except Exception as e:
            logger.warning("Crypto upsert error %s: %s", coin.get("symbol"), e)
    await session.commit()
    logger.info("Market: upserted %d crypto prices", inserted)
    return inserted


async def fetch_stocks(session: AsyncSession) -> int:
    inserted = 0
    for symbol, (name, asset_type) in STOCK_SYMBOLS.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d", interval="1d")
            if hist.empty:
                logger.warning("No history data for %s", symbol)
                continue

            price = float(hist["Close"].iloc[-1])
            prev  = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
            change_24h = ((price - prev) / prev * 100) if prev and prev != 0 else None

            # For forex store as-is; for gold/stocks use standard display symbol
            display_symbol = symbol.replace("=X", "").replace("^", "")

            await session.execute(
                text("""
                    INSERT INTO market_prices
                      (symbol, type, name, price, change_24h, updated_at)
                    VALUES
                      (:symbol, :type, :name, :price, :ch24h, :updated_at)
                    ON CONFLICT (symbol) DO UPDATE SET
                      price=EXCLUDED.price, change_24h=EXCLUDED.change_24h,
                      updated_at=EXCLUDED.updated_at
                """),
                {
                    "symbol":     display_symbol,
                    "type":       asset_type,
                    "name":       name,
                    "price":      price,
                    "ch24h":      change_24h,
                    "updated_at": datetime.utcnow(),
                },
            )
            inserted += 1
        except Exception as e:
            logger.warning("Stock fetch error %s: %s", symbol, e)

    await session.commit()
    logger.info("Market: upserted %d stock/forex prices", inserted)
    return inserted
