"""NVD CVE fetcher — pulls recent CVEs from NVD 2.0 API (free, no API key needed)."""
from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
RESULTS_PER_PAGE = 20


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
    now   = datetime.utcnow()
    start = now - timedelta(days=7)

    params = {
        "pubStartDate":    start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "pubEndDate":      now.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "resultsPerPage":  RESULTS_PER_PAGE,
    }

    try:
        async with aiohttp.ClientSession() as http:
            async with http.get(
                NVD_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "WarRoom/2.0 (security research tool)"},
            ) as resp:
                if resp.status != 200:
                    logger.warning("NVD API returned %d", resp.status)
                    return 0
                data = await resp.json()
    except Exception as e:
        logger.warning("NVD fetch error: %s", e)
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
