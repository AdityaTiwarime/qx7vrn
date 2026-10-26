"""Prints every number quoted in docs/analysis.md, from the committed snapshot.

python backend/scripts/findings.py
"""

from __future__ import annotations

import sys
from datetime import time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analysis  # noqa: E402
from app.data import load  # noqa: E402

HOURS = 31 * 24


def paired(sel: analysis.Selection) -> pd.DataFrame:
    actuals, forecasts = load()
    return analysis.pair(actuals, analysis.select_forecasts(forecasts, sel))


def show(name: str, m: dict) -> None:
    keys = ["mae", "bias", "mae_debiased", "rmse", "p50_abs", "shortfall_p90", "shortfall_p95", "max_abs"]
    values = "  ".join(f"{k}={m[k]:,.0f}" for k in keys)
    print(f"{name:<16}", values, f" nmae={m['nmae']:.1%}", f" lead={m['mean_horizon_h']:.1f}h")


def trailing_bias_correction(p: pd.DataFrame, days: int = 7) -> tuple[float, float, int]:
    """Subtract the mean error of the `days` delivery days that were complete when buying for day D
    (i.e. up to D-2). Uses only information available at decision time."""
    p = p.assign(day=p["target"].dt.tz_convert(analysis.UK).dt.date)
    daily_bias = p.groupby("day")["error"].mean()
    corrected, raw, used = [], [], 0
    for day, g in p.groupby("day"):
        known = [d for d in daily_bias.index if day - timedelta(days=2 + days) < d <= day - timedelta(days=2)]
        window = daily_bias[known]
        if len(window) < 3:
            continue
        used += 1
        corrected.append((g["error"] - window.mean()).abs())
        raw.append(g["error"].abs())
    return float(pd.concat(corrected).mean()), float(pd.concat(raw).mean()), used


def main() -> None:
    print("== Day-ahead cut-off (forecast on screen at T the day before), all of January")
    for c in ["06:00", "10:00", "14:00", "18:00"]:
        hh, mm = map(int, c.split(":"))
        show(f"cutoff {c}", analysis.metrics(paired(analysis.Selection("cutoff", cutoff=time(hh, mm))), HOURS))

    p = paired(analysis.Selection("cutoff", cutoff=time(10, 0)))
    print("\n== 10:00 cut-off details")
    print(f"mean actual {p['actual'].mean():,.0f} MW, mean forecast {p['forecast'].mean():,.0f} MW")
    print(f"hours where wind came in below forecast: {(p['error'] > 0).mean():.1%}")
    print(f"correlation forecast vs actual: {np.corrcoef(p['forecast'], p['actual'])[0, 1]:.3f}")
    hours = {r["hour"]: r for r in analysis.by_hour_of_day(p)}
    night = np.mean([hours[h]["bias"] for h in range(0, 7)])
    day = np.mean([hours[h]["bias"] for h in range(10, 20)])
    print(f"bias 00:00-06:59 UK {night:,.0f} MW, 10:00-19:59 UK {day:,.0f} MW")
    daily = analysis.daily(p)
    worst = sorted(daily, key=lambda d: -d["bias"])[:4]
    print("largest daily over-forecasts:", [(d["day"], round(d["bias"])) for d in worst])
    print("days where the forecast ran low on average:", sum(d["bias"] < 0 for d in daily))
    c, r, n = trailing_bias_correction(p)
    print(f"trailing 7-day bias correction: MAE {r:,.0f} -> {c:,.0f} MW ({1 - c / r:.0%} lower) over {n} days")

    print("\n== Fixed horizon")
    actuals, forecasts = load()
    for row in analysis.horizon_curve(forecasts, actuals):
        if row["horizon_h"] in (0, 1, 4, 12, 24, 36, 47):
            h, mae, bias, p90 = row["horizon_h"], row["mae"], row["bias"], row["p90_abs"]
            print(f"H={h:>2}h  mae={mae:,.0f}  bias={bias:,.0f}  p90={p90:,.0f}  hours={row['n']}")


if __name__ == "__main__":
    main()
