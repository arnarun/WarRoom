"""Vulnerability fetchers → osint_signals.

NVD 2.0 API: recent CVEs. Works without a key but is slow and heavily
rate-limited from datacenter IPs; set NVD_API_KEY (free) for 10x the limit.
CISA KEV: catalog of actively exploited CVEs — static JSON, fast, no key.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
import asyncio
from typing import Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import config
from fetchers.common import SSL_CONTEXT, utcnow

logger = logging.getLogger(__name__)

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RESULTS_PER_PAGE = 20
NVD_TIMEOUT_S    = 90   # NVD routinely takes 30s+ for date-range queries
NVD_ATTEMPTS     = 2

KEV_URL   = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
KEV_LIMIT = 30          # most recently added entries


def _cvss_severity(metrics: dict) -> str:
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        if key in metrics:
            try:
                score = float(metrics[key][0]["cvssData"]["baseScore"])
                if score >= 9.0:  return "critical"
                if score >= 7.0:  return "high"
                if score >= 4.0:  return "medium"
                return "low"
            except (KeyError, IndexError, TypeError):
                pass
    return "medium"


def _parse_nvd_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


async def fetch_nvd(session: AsyncSession) -> int:
    now   = utcnow()
    start = now - timedelta(days=7)

    params = {
        "pubStartDate":    start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":      now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage":  RESULTS_PER_PAGE,
    }

    headers = {"User-Agent": "WarRoom/2.0 (security research tool)"}
    if config.NVD_API_KEY:
        headers["apiKey"] = config.NVD_API_KEY

    data = None
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
        for attempt in range(1, NVD_ATTEMPTS + 1):
            try:
                async with http.get(
                    NVD_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=NVD_TIMEOUT_S),
                    headers=headers,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        logger.info("NVD response: totalResults=%s, returned=%s",
                                    data.get("totalResults"), data.get("resultsPerPage"))
                        break
                    logger.warning("NVD API returned %d (attempt %d)", resp.status, attempt)
            except Exception as e:
                logger.warning("NVD fetch error (attempt %d): %s", attempt, type(e).__name__)
            if attempt < NVD_ATTEMPTS:
                await asyncio.sleep(10)
    if data is None:
        return 0

    inserted = 0
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")
        if not cve_id:
            continue

        # English description
        descriptions = cve.get("descriptions", [])
        desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

        # CVSS severity
        severity = _cvss_severity(cve.get("metrics", {}))

        # Short title = CVE-ID + first 120 chars of description
        title = f"{cve_id}: {desc[:120]}" if desc else cve_id

        url   = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        pub   = _parse_nvd_date(cve.get("published"))

        try:
            await session.execute(
                text("""
                    INSERT INTO osint_signals
                      (source, type, severity, title, description, url, published_at)
                    VALUES
                      ('nvd', 'vulnerability', :severity, :title, :desc, :url, :pub)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "severity": severity,
                    "title":    title,
                    "desc":     desc[:2000],
                    "url":      url,
                    "pub":      pub,
                },
            )
            inserted += 1
        except Exception as e:
            logger.debug("NVD skip %s: %s", cve_id, e)

    await session.commit()
    logger.info("NVD: inserted %d CVEs", inserted)
    return inserted


async def fetch_cisa_kev(session: AsyncSession) -> int:
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=SSL_CONTEXT)) as http:
            async with http.get(KEV_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning("CISA KEV returned %d", resp.status)
                    return 0
                data = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("CISA KEV fetch error: %s", e)
        return 0

    vulns = sorted(data.get("vulnerabilities", []), key=lambda v: v.get("dateAdded", ""), reverse=True)
    inserted = 0
    for v in vulns[:KEV_LIMIT]:
        cve_id = v.get("cveID", "")
        if not cve_id:
            continue
        name = v.get("vulnerabilityName") or f"{v.get('vendorProject', '')} {v.get('product', '')}".strip()
        desc = v.get("shortDescription", "")
        if v.get("requiredAction"):
            desc += f"\nRequired action: {v['requiredAction']} (due {v.get('dueDate', '?')})"
        if v.get("knownRansomwareCampaignUse") == "Known":
            desc += "\nUsed in ransomware campaigns."
        try:
            result = await session.execute(
                text("""
                    INSERT INTO osint_signals
                      (source, type, severity, title, description, url, country, published_at)
                    VALUES
                      ('cisa-kev', 'vulnerability', 'critical', :title, :desc, :url, 'US', :pub)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "title": f"Exploited: {cve_id}: {name}"[:500],
                    "desc":  desc[:2000],
                    "url":   f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                    "pub":   _parse_nvd_date(v.get("dateAdded", "") + "T00:00:00"),
                },
            )
            inserted += result.rowcount or 0
        except Exception as e:
            logger.debug("CISA KEV skip %s: %s", cve_id, e)

    await session.commit()
    logger.info("CISA KEV: inserted %d exploited CVEs", inserted)
    return inserted
