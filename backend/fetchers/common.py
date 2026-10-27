"""Shared helpers for fetchers — UTC time, TLS, feed-entry parsing."""
from __future__ import annotations
import html
import re
import ssl
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
import certifi

# Verified TLS for every outbound fetch (certifi bundle works on macOS/slim images)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

# Feeds sometimes carry event dates far in the future; clamp anything beyond this
_MAX_FUTURE = timedelta(hours=1)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE  = re.compile(r"\s+")


def utcnow() -> datetime:
    """Naive UTC datetime — matches the TIMESTAMP (without tz) columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def from_timestamp(ts) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)


def clamp_future(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    now = utcnow()
    return now if dt > now + _MAX_FUTURE else dt


def parse_entry_date(entry) -> Optional[datetime]:
    """feedparser *_parsed fields are already normalized to UTC."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return clamp_future(datetime(*t[:6]))
            except Exception:
                pass
    return None


def get_entry_image(entry) -> Optional[str]:
    if getattr(entry, "media_thumbnail", None):
        return safe_url(entry.media_thumbnail[0].get("url"))
    if getattr(entry, "media_content", None):
        for m in entry.media_content:
            if m.get("medium") == "image" or m.get("type", "").startswith("image"):
                return safe_url(m.get("url"))
    for enc in getattr(entry, "enclosures", None) or []:
        if enc.get("type", "").startswith("image"):
            return safe_url(enc.get("href"))
    return None


def clean_text(s: Optional[str], limit: int = 2000) -> Optional[str]:
    """Strip HTML tags/entities and collapse whitespace."""
    if not s:
        return None
    s = html.unescape(_TAG_RE.sub(" ", s))
    s = _WS_RE.sub(" ", s).strip()
    return s[:limit] or None


def safe_url(url: Optional[str]) -> Optional[str]:
    """Only allow http(s) links — feeds are untrusted input rendered as hrefs."""
    if not url:
        return None
    url = url.strip()
    return url if url.lower().startswith(("http://", "https://")) else None


def http_session(**kwargs) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT), **kwargs)
