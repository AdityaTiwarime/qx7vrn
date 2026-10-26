"""Forecast selection and accuracy analysis. Pure functions over pandas frames, no I/O.

Vocabulary
- target time:   the hour the forecast is about (Elexon "startTime").
- publish time:  when the forecast was issued (Elexon "publishTime").
- horizon:       target time - publish time, in hours. Only 0-48 h is kept (see data.py).
- error:         forecast - actual, in MW. Positive = wind came in BELOW forecast, i.e. a
                 shortfall the trading team would have had to buy elsewhere.

Two ways to pick "the forecast you would have had":
- fixed horizon H:  for each target, the latest forecast published at least H hours before it.
- day-ahead cutoff: for each target on UK delivery day D, the latest forecast published by
                    a set time (e.g. 10:00 UK) on day D-1 - what was on screen when buying.

WINDFOR is hourly and FUELHH is half-hourly, so accuracy is scored on the hours where both
exist (the :00 half-hours). Nothing is interpolated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

import numpy as np
import pandas as pd

UK = "Europe/London"
MAX_HORIZON_H = 48


@dataclass(frozen=True)
class Selection:
    mode: str  # "horizon" | "cutoff"
    horizon_h: float = 4.0
    cutoff: time = time(10, 0)


def select_forecasts(fc: pd.DataFrame, sel: Selection) -> pd.DataFrame:
    """One forecast per target time: columns target, forecast, publish, horizon_h."""
    if sel.mode == "horizon":
        eligible = fc[fc["horizon_h"] >= sel.horizon_h]
    elif sel.mode == "cutoff":
        local_day = fc["target"].dt.tz_convert(UK).dt.normalize()
        cutoff_local = local_day - pd.Timedelta(days=1) + pd.Timedelta(hours=sel.cutoff.hour, minutes=sel.cutoff.minute)
        eligible = fc[fc["publish"] <= cutoff_local.dt.tz_convert("UTC")]
    else:
        raise ValueError(f"unknown mode {sel.mode!r}")
    if eligible.empty:
        return pd.DataFrame(columns=["target", "forecast", "publish", "horizon_h"])
    latest = eligible.loc[eligible.groupby("target")["publish"].idxmax()]
    return latest[["target", "forecast", "publish", "horizon_h"]].sort_values("target").reset_index(drop=True)


def pair(actuals: pd.DataFrame, chosen: pd.DataFrame) -> pd.DataFrame:
    """Hours that have both an actual and a chosen forecast, with the error."""
    out = chosen.merge(actuals, left_on="target", right_on="time", how="inner").drop(columns="time")
    out["error"] = out["forecast"] - out["actual"]
    return out


def metrics(paired: pd.DataFrame, expected_hours: int) -> dict:
    n = len(paired)
    if n == 0:
        return {"n": 0, "coverage": 0.0}
    e = paired["error"].to_numpy(dtype=float)
    a = np.abs(e)
    mean_actual = float(paired["actual"].mean())
    return {
        "n": n,
        "coverage": n / expected_hours if expected_hours else 0.0,
        "mae": float(a.mean()),
        "rmse": float(np.sqrt((e**2).mean())),
        "bias": float(e.mean()),
        "nmae": float(a.mean() / mean_actual) if mean_actual else None,
        # MAE once the average bias is subtracted: how much of the error is a steady offset.
        # In-sample (uses this window's own bias), so indicative only.
        "mae_debiased": float(np.abs(e - e.mean()).mean()),
        "p50_abs": float(np.percentile(a, 50)),
        "p90_abs": float(np.percentile(a, 90)),
        "p99_abs": float(np.percentile(a, 99)),
        "max_abs": float(a.max()),
        # How far wind fell short of the forecast in the worst 10% / 5% of hours:
        # a buffer of this size covers 90% / 95% of hours.
        "shortfall_p90": float(max(np.percentile(e, 90), 0.0)),
        "shortfall_p95": float(max(np.percentile(e, 95), 0.0)),
        "mean_actual": mean_actual,
        "mean_forecast": float(paired["forecast"].mean()),
        "mean_horizon_h": float(paired["horizon_h"].mean()),
    }


def horizon_curve(fc: pd.DataFrame, actuals: pd.DataFrame, hours: range = range(0, MAX_HORIZON_H + 1)) -> list[dict]:
    """Accuracy as a function of how far ahead the forecast was made."""
    rows = []
    for h in hours:
        p = pair(actuals, select_forecasts(fc, Selection("horizon", float(h))))
        if p.empty:
            continue
        e = p["error"].to_numpy(dtype=float)
        rows.append(
            {
                "horizon_h": h,
                "n": len(p),
                "mae": float(np.abs(e).mean()),
                "rmse": float(np.sqrt((e**2).mean())),
                "bias": float(e.mean()),
                "p90_abs": float(np.percentile(np.abs(e), 90)),
            }
        )
    return rows


def by_hour_of_day(paired: pd.DataFrame) -> list[dict]:
    if paired.empty:
        return []
    hour = paired["target"].dt.tz_convert(UK).dt.hour
    g = paired.assign(hour=hour, abs_error=paired["error"].abs()).groupby("hour")
    return [
        {"hour": int(h), "mae": float(r["abs_error"].mean()), "bias": float(r["error"].mean()), "n": int(len(r))}
        for h, r in g
    ]


def histogram(paired: pd.DataFrame, width: int = 500) -> list[dict]:
    if paired.empty:
        return []
    e = paired["error"].to_numpy(dtype=float)
    lo = int(np.floor(e.min() / width) * width)
    hi = int(np.ceil(e.max() / width) * width) + width
    counts, edges = np.histogram(e, bins=np.arange(lo, hi + 1, width))
    return [{"from": int(edges[i]), "to": int(edges[i + 1]), "count": int(c)} for i, c in enumerate(counts)]


def daily(paired: pd.DataFrame) -> list[dict]:
    if paired.empty:
        return []
    day = paired["target"].dt.tz_convert(UK).dt.date
    g = paired.assign(day=day, abs_error=paired["error"].abs()).groupby("day")
    return [
        {
            "day": d.isoformat(),
            "mae": float(r["abs_error"].mean()),
            "bias": float(r["error"].mean()),
            "actual_mwh": float(r["actual"].sum()),
            "forecast_mwh": float(r["forecast"].sum()),
        }
        for d, r in g
    ]
