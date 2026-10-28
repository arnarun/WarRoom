"""Probe every outbound data source WarRoom depends on — no database needed.

Run this on a candidate server (e.g. a fresh Akamai/Linode instance) before
deploying, to find out which sources block or rate-limit that network.

    cd backend
    .venv/bin/python scripts/probe_sources.py                 # table to stdout
    .venv/bin/python scripts/probe_sources.py --json out.json # also save a report
    .venv/bin/python scripts/probe_sources.py --only rss      # one group

Uses the same HTTP clients, headers and URL lists as the real fetchers, so a
pass here means the fetcher can reach the source from this machine.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import socket
import sys
import time
import warnings
from dataclasses import dataclass, asdict
from pathlib import Path

warnings.filterwarnings("ignore")  # yfinance/pandas deprecation noise

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiohttp
import feedparser
from curl_cffi.requests import AsyncSession as CurlSession

import config
from fetchers.common import SSL_CONTEXT
from fetchers import abusech, alienvault, breach, cisa, darkweb, gdelt, hackernews, market, nvd, stocktwits
from fetchers.rss import load_sources

# Bot-wall fingerprints (Cloudflare, Akamai Bot Manager, generic CAPTCHA pages)
_BLOCK_MARKERS = (
    "just a moment", "cf-challenge", "cf_chl", "attention required",
    "access denied", "captcha", "are you a robot", "unusual traffic",
    "please limit requests", "too many requests", "blocked",
)


@dataclass
class Result:
    group:  str
    name:   str
    url:    str
    status: str          # OK | EMPTY | BLOCKED | ERROR | SKIPPED (no key)
    http:   int | None
    ms:     int
    detail: str = ""


def _classify(code: int | None, body: str, ok: bool) -> tuple[str, str]:
    low = body[:4000].lower()
    if code in (401, 403, 429, 451, 503) or (not ok and any(m in low for m in _BLOCK_MARKERS)):
        marker = next((m for m in _BLOCK_MARKERS if m in low), "")
        return "BLOCKED", f"HTTP {code}" + (f" · '{marker}'" if marker else "")
    if code and code >= 400:
        return "ERROR", f"HTTP {code}"
    return ("OK", "") if ok else ("EMPTY", body[:80].replace("\n", " ").strip())


# ── individual probe kinds ────────────────────────────────────────────────

async def probe_rss_curl(http: CurlSession, sem, group, name, url) -> Result:
    """RSS via curl_cffi Chrome impersonation (as fetchers/rss.py does)."""
    async with sem:
        t0 = time.monotonic()
        try:
            r = await http.get(url, timeout=20)
            n = len(feedparser.parse(r.content).entries)
            status, detail = _classify(r.status_code, r.text, n > 0)
            return Result(group, name, url, status, r.status_code, _ms(t0), detail or f"{n} entries")
        except Exception as e:
            return Result(group, name, url, "ERROR", None, _ms(t0), _err(e))


async def probe_rss_aiohttp(http: aiohttp.ClientSession, sem, group, name, url, headers=None) -> Result:
    """RSS via aiohttp + certifi TLS (as the OSINT fetchers do)."""
    async with sem:
        t0 = time.monotonic()
        try:
            async with http.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as r:
                body = await r.text(errors="replace")
            n = len(feedparser.parse(body).entries)
            status, detail = _classify(r.status, body, n > 0)
            return Result(group, name, url, status, r.status, _ms(t0), detail or f"{n} entries")
        except Exception as e:
            return Result(group, name, url, "ERROR", None, _ms(t0), _err(e))


async def probe_json(http: aiohttp.ClientSession, group, name, url, *, method="GET",
                     data=None, params=None, headers=None, check=lambda j: bool(j),
                     timeout=30) -> Result:
    t0 = time.monotonic()
    try:
        async with http.request(method, url, data=data, params=params, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            body = await r.text(errors="replace")
        try:
            ok = bool(check(json.loads(body)))
        except Exception:
            ok = False
        status, detail = _classify(r.status, body, ok)
        return Result(group, name, url, status, r.status, _ms(t0), detail)
    except Exception as e:
        return Result(group, name, url, "ERROR", None, _ms(t0), _err(e))


async def probe_json_curl(http: CurlSession, group, name, url, check=lambda j: bool(j)) -> Result:
    """JSON via curl_cffi Chrome impersonation (as fetchers/stocktwits.py does)."""
    t0 = time.monotonic()
    try:
        r = await http.get(url, timeout=20)
        try:
            ok = bool(check(r.json()))
        except Exception:
            ok = False
        status, detail = _classify(r.status_code, r.text, ok)
        return Result(group, name, url, status, r.status_code, _ms(t0), detail)
    except Exception as e:
        return Result(group, name, url, "ERROR", None, _ms(t0), _err(e))


def skipped(group, name, url, env) -> Result:
    return Result(group, name, url, "SKIPPED", None, 0, f"set {env} to enable")


async def probe_sync(group, name, url, fn) -> Result:
    """Library-based sources (yfinance, pycoingecko) — run in a thread."""
    t0 = time.monotonic()
    try:
        detail = await asyncio.to_thread(fn)
        return Result(group, name, url, "OK" if detail else "EMPTY", None, _ms(t0), detail or "no data")
    except Exception as e:
        msg = _err(e)
        status = "BLOCKED" if any(m in msg.lower() for m in ("429", "rate", "too many", "403")) else "ERROR"
        return Result(group, name, url, status, None, _ms(t0), msg)


def _ms(t0) -> int:
    return int((time.monotonic() - t0) * 1000)


def _err(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:160]


# ── groups ────────────────────────────────────────────────────────────────

async def group_rss() -> list[Result]:
    sem = asyncio.Semaphore(12)
    async with CurlSession(impersonate="chrome") as http:
        return await asyncio.gather(*[
            probe_rss_curl(http, sem, "rss", s["name"], s["url"]) for s in load_sources()
        ])


async def group_osint() -> list[Result]:
    sem = asyncio.Semaphore(8)
    feeds = (
        [(cisa._SOURCE_MAP.get(c, "cert"), u, cisa._HEADERS) for u, _, c in cisa.CISA_FEEDS]
        + [(n, u, breach._HEADERS) for u, _, n, _ in breach.BREACH_FEEDS + breach.PEOPLE_FEEDS]
        + [(n, u, None) for u, n in darkweb.CLEARNET_FEEDS]
    )
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
        results = await asyncio.gather(*[
            probe_rss_aiohttp(http, sem, "osint", n, u, h) for n, u, h in feeds
        ])
        abuse_hdr = {"Auth-Key": config.ABUSECH_AUTH_KEY}
        nvd_hdr = {"User-Agent": "WarRoom/2.0 (security research tool)"}
        if config.NVD_API_KEY:
            nvd_hdr["apiKey"] = config.NVD_API_KEY
        results += [
            await probe_json(http, "osint", "feodo tracker", abusech.FEODO_BLOCKLIST,
                             check=lambda j: len(j) > 0),
            await probe_json(http, "osint", "urlhaus", abusech.URLHAUS_API, method="POST",
                             data={"limit": "3"}, headers=abuse_hdr,
                             check=lambda j: j.get("query_status") == "ok")
            if config.ABUSECH_AUTH_KEY else skipped("osint", "urlhaus", abusech.URLHAUS_API, "ABUSECH_AUTH_KEY"),
            await probe_json(http, "osint", "malwarebazaar", abusech.MALWAREBAZAAR_API, method="POST",
                             data={"query": "get_recent", "selector": "100"}, headers=abuse_hdr,
                             check=lambda j: j.get("query_status") == "ok")
            if config.ABUSECH_AUTH_KEY else skipped("osint", "malwarebazaar", abusech.MALWAREBAZAAR_API, "ABUSECH_AUTH_KEY"),
            await probe_json(http, "osint", "alienvault otx", alienvault.OTX_PULSES,
                             params={"limit": "1"}, headers={"X-OTX-API-KEY": config.OTX_API_KEY},
                             check=lambda j: "results" in j)
            if config.OTX_API_KEY else skipped("osint", "alienvault otx", alienvault.OTX_PULSES, "OTX_API_KEY"),
            await probe_json(http, "osint", "nvd" + (" (key)" if config.NVD_API_KEY else ""), nvd.NVD_URL,
                             params={"resultsPerPage": "1"}, headers=nvd_hdr, timeout=nvd.NVD_TIMEOUT_S,
                             check=lambda j: j.get("totalResults", 0) > 0),
            await probe_json(http, "osint", "cisa kev", nvd.KEV_URL,
                             check=lambda j: len(j.get("vulnerabilities", [])) > 0),
        ]
    return results


async def group_social() -> list[Result]:
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
        return [
            await probe_json(http, "social", "hackernews", hackernews.FEEDS["topstories"],
                             check=lambda j: len(j) > 0),
            # Unauthenticated JSON is the strictest test of datacenter-IP blocking;
            # the app itself uses OAuth (PRAW) when credentials are configured.
            await probe_json(http, "social", "reddit (no auth)",
                             "https://www.reddit.com/r/worldnews/hot.json?limit=1",
                             headers={"User-Agent": "WarRoom/1.1 probe"},
                             check=lambda j: bool(j.get("data", {}).get("children"))),
            await probe_json(http, "social", "gdelt", gdelt.GDELT_API,
                             params={"query": "cybersecurity", "mode": "artlist",
                                     "maxrecords": "1", "format": "json"},
                             check=lambda j: bool(j.get("articles"))),
        ] + [await _stocktwits()]


async def _stocktwits() -> Result:
    async with CurlSession(impersonate="chrome") as http:
        return await probe_json_curl(http, "social", "stocktwits", stocktwits.ST_STREAM.format(sym="SPY"),
                                     check=lambda j: bool(j.get("messages")))


async def group_market() -> list[Result]:
    def coingecko():
        data = market.cg.get_coins_markets(vs_currency="usd", ids="bitcoin", per_page=1)
        return f"BTC ${data[0]['current_price']:,}" if data else ""

    def yfinance():
        import yfinance as yf
        hist = yf.Ticker("^GSPC").history(period="5d", interval="1d")
        return "" if hist.empty else f"S&P {float(hist['Close'].iloc[-1]):,.0f}"

    return [
        await probe_sync("market", "coingecko", "api.coingecko.com", coingecko),
        await probe_sync("market", "yfinance", "query1.finance.yahoo.com", yfinance),
    ]


GROUPS = {"rss": group_rss, "osint": group_osint, "social": group_social, "market": group_market}


async def egress_info() -> dict:
    info = {"hostname": socket.gethostname()}
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
            async with http.get("https://api.ipify.org?format=json", timeout=aiohttp.ClientTimeout(total=10)) as r:
                info["ip"] = (await r.json())["ip"]
        info["rdns"] = socket.gethostbyaddr(info["ip"])[0]
    except Exception:
        pass
    return info


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", choices=list(GROUPS), action="append", help="run only these groups")
    ap.add_argument("--json", metavar="PATH", help="write a JSON report")
    args = ap.parse_args()

    egress = await egress_info()
    print(f"Egress: {egress.get('ip', '?')}  rDNS: {egress.get('rdns', '?')}  host: {egress['hostname']}\n")

    results: list[Result] = []
    for g in args.only or GROUPS:
        results += await GROUPS[g]()

    icon = {"OK": "✓", "EMPTY": "∅", "BLOCKED": "⛔", "ERROR": "✗", "SKIPPED": "–"}
    for r in sorted(results, key=lambda r: (r.group, r.status == "OK", r.name)):
        print(f"{icon[r.status]} {r.status:<7} {r.group:<6} {r.name[:32]:<32} "
              f"{str(r.http or ''):>4} {r.ms:>6}ms  {r.detail[:70]}")

    summary = {}
    for r in results:
        summary.setdefault(r.group, {}).setdefault(r.status, 0)
        summary[r.group][r.status] += 1
    print("\nSummary:")
    for g, counts in summary.items():
        print(f"  {g:<7} " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"egress": egress, "summary": summary, "results": [asdict(r) for r in results]}, indent=2))
        print(f"\nReport written to {args.json}")


if __name__ == "__main__":
    asyncio.run(main())
