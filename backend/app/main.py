"""HTTP API for the wind forecast monitor.

GET /api/health                 liveness
GET /api/meta                   what data is loaded
GET /api/series?...             actual vs chosen forecast, for the chart
GET /api/accuracy?...           error statistics for the same choice

Common query parameters (series and accuracy):
  start, end   UK delivery days, YYYY-MM-DD, inclusive, within January 2026
  mode         "horizon" (latest forecast published >= horizon hours ahead) or
               "cutoff"  (latest forecast published by `cutoff` UK time the day before)
  horizon      0-48 hours (mode=horizon)
  cutoff       HH:MM UK time on the day before delivery (mode=cutoff)
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from typing import Annotated, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from . import analysis
from .data import load

FIRST_DAY, LAST_DAY = date(2026, 1, 1), date(2026, 1, 31)

app = FastAPI(
    title="Wind Forecast Monitor API",
    description="UK national wind: actual generation vs Elexon WINDFOR forecasts, January 2026.",
    version="1.0.0",
)

Day = Annotated[date, Query(description="UK delivery day, YYYY-MM-DD")]
Mode = Annotated[Literal["horizon", "cutoff"], Query()]
Horizon = Annotated[float, Query(ge=0, le=analysis.MAX_HORIZON_H)]
Cutoff = Annotated[str, Query(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


def _window(start: date, end: date) -> tuple[pd.Timestamp, pd.Timestamp]:
    if not (FIRST_DAY <= start <= end <= LAST_DAY):
        raise HTTPException(422, f"start and end must satisfy {FIRST_DAY} <= start <= end <= {LAST_DAY}")
    lo = pd.Timestamp(datetime.combine(start, time()), tz=analysis.UK).tz_convert("UTC")
    hi = pd.Timestamp(datetime.combine(end + timedelta(days=1), time()), tz=analysis.UK).tz_convert("UTC")
    return lo, hi


def _selection(mode: str, horizon: float, cutoff: str) -> analysis.Selection:
    hh, mm = (int(x) for x in cutoff.split(":"))
    return analysis.Selection(mode=mode, horizon_h=horizon, cutoff=time(hh, mm))


def _in(df: pd.DataFrame, col: str, lo: pd.Timestamp, hi: pd.Timestamp) -> pd.DataFrame:
    return df[(df[col] >= lo) & (df[col] < hi)]


@lru_cache(maxsize=64)
def _paired(start: date, end: date, sel: analysis.Selection) -> pd.DataFrame:
    actuals, forecasts = load()
    lo, hi = _window(start, end)
    chosen = analysis.select_forecasts(_in(forecasts, "target", lo, hi), sel)
    return analysis.pair(_in(actuals, "time", lo, hi), chosen)


@lru_cache(maxsize=64)
def _horizon_curve(start: date, end: date) -> list[dict]:
    actuals, forecasts = load()
    lo, hi = _window(start, end)
    return analysis.horizon_curve(_in(forecasts, "target", lo, hi), _in(actuals, "time", lo, hi))


def _iso(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    actuals, forecasts = load()
    publishes = forecasts["publish"].drop_duplicates().sort_values()
    gaps = publishes.diff().dropna().dt.total_seconds() / 3600
    return {
        "first_day": FIRST_DAY.isoformat(),
        "last_day": LAST_DAY.isoformat(),
        "actuals": {"rows": len(actuals), "resolution_min": 30, "source": "Elexon BMRS FUELHH (fuelType WIND)"},
        "forecasts": {
            "rows": len(forecasts),
            "publishes": len(publishes),
            "resolution_min": 60,
            "median_publish_gap_h": float(gaps.median()) if len(gaps) else None,
            "max_horizon_h": analysis.MAX_HORIZON_H,
            "source": "Elexon BMRS WINDFOR",
        },
    }


@app.get("/api/series")
def series(
    start: Day = FIRST_DAY,
    end: Day = LAST_DAY,
    mode: Mode = "horizon",
    horizon: Horizon = 4,
    cutoff: Cutoff = "10:00",
) -> dict:
    actuals, _ = load()
    lo, hi = _window(start, end)
    p = _paired(start, end, _selection(mode, horizon, cutoff))
    a = _in(actuals, "time", lo, hi)
    actual_points = [{"t": _iso(t), "actual": v} for t, v in zip(a["time"], a["actual"], strict=True)]
    forecast_points = [
        {
            "t": _iso(r.target),
            "forecast": r.forecast,
            "published": _iso(r.publish),
            "horizon_h": r.horizon_h,
            "error": r.error,
        }
        for r in p.itertuples()
    ]
    return {"actual": actual_points, "forecast": forecast_points}


@app.get("/api/accuracy")
def accuracy(
    start: Day = FIRST_DAY,
    end: Day = LAST_DAY,
    mode: Mode = "horizon",
    horizon: Horizon = 4,
    cutoff: Cutoff = "10:00",
) -> dict:
    p = _paired(start, end, _selection(mode, horizon, cutoff))
    expected_hours = ((end - start).days + 1) * 24
    return {
        "metrics": analysis.metrics(p, expected_hours),
        "by_hour": analysis.by_hour_of_day(p),
        "histogram": analysis.histogram(p),
        "daily": analysis.daily(p),
        "horizon_curve": _horizon_curve(start, end),
    }
