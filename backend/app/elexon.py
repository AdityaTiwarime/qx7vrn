"""Thin client for the two Elexon BMRS datasets this product uses.

Both are public "stream" endpoints (no API key, plain JSON lists):

- FUELHH: actual half-hourly generation by fuel type. We keep fuelType == "WIND".
- WINDFOR: national wind generation forecasts. Each row is one forecast value for one
  target hour, stamped with the time the forecast was published.

Requests are split into small date chunks so no single call is large, and each chunk is
retried a few times because a public API can blip.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

import httpx

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"


def _get(client: httpx.Client, url: str, params: dict[str, str], tries: int = 3) -> list[dict]:
    for attempt in range(1, tries + 1):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError):
            if attempt == tries:
                raise
            time.sleep(2 * attempt)
    return []


def fetch_actuals(start: date, end: date, chunk_days: int = 7) -> list[dict]:
    """Wind outturn for settlement dates start..end (inclusive)."""
    rows: list[dict] = []
    with httpx.Client(timeout=60) as client:
        day = start
        while day <= end:
            last = min(end, day + timedelta(days=chunk_days - 1))
            rows += _get(
                client,
                f"{BASE}/FUELHH/stream",
                {
                    "settlementDateFrom": day.isoformat(),
                    "settlementDateTo": last.isoformat(),
                    "fuelType": "WIND",
                },
            )
            day = last + timedelta(days=1)
    return [r for r in rows if r.get("fuelType") == "WIND"]


def fetch_forecasts(published_from: datetime, published_to: datetime, chunk_days: int = 3) -> list[dict]:
    """Every WINDFOR forecast published in [published_from, published_to)."""
    rows: list[dict] = []
    with httpx.Client(timeout=120) as client:
        lo = published_from
        while lo < published_to:
            hi = min(published_to, lo + timedelta(days=chunk_days))
            rows += _get(
                client,
                f"{BASE}/WINDFOR/stream",
                {
                    "publishDateTimeFrom": lo.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": hi.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            lo = hi
    return rows
