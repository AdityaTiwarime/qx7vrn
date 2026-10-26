"""Loads the January 2026 snapshot (backend/data/*.csv, made by scripts/fetch_data.py)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parents[1] / "data"))


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(actuals, forecasts). Times are tz-aware UTC.

    actuals:   time, actual       (MW, half-hourly)
    forecasts: publish, target, forecast, horizon_h   (MW, hourly targets, horizon 0-48 h)
    """
    a = pd.read_csv(DATA_DIR / "actuals.csv")
    actuals = pd.DataFrame(
        {"time": pd.to_datetime(a["start_time"], utc=True), "actual": a["generation_mw"].astype(float)}
    )
    f = pd.read_csv(DATA_DIR / "forecasts.csv")
    forecasts = pd.DataFrame(
        {
            "publish": pd.to_datetime(f["publish_time"], utc=True),
            "target": pd.to_datetime(f["start_time"], utc=True),
            "forecast": f["generation_mw"].astype(float),
        }
    )
    forecasts["horizon_h"] = (forecasts["target"] - forecasts["publish"]).dt.total_seconds() / 3600
    return actuals.sort_values("time").reset_index(drop=True), forecasts
