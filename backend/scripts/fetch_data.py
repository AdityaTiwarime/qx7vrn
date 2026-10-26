"""Download the January 2026 snapshot from Elexon into backend/data/.

    python backend/scripts/fetch_data.py

Scope (from the brief): purchase decisions made in January 2026, national wind only.
- actuals.csv:   FUELHH wind outturn, every half hour of January 2026 (UTC).
- forecasts.csv: WINDFOR forecasts whose target hour is in January 2026 and that were
                 published 0-48 hours before that target hour. Forecasts published after
                 their target (hindcasts) can't inform a purchase decision, so they're dropped.

The app reads these files instead of calling Elexon on every page load: answers are fast,
reproducible, and the demo still works if the public API is slow or down.
"""

from __future__ import annotations

import csv
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.elexon import fetch_actuals, fetch_forecasts  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data"
MONTH_START = datetime(2026, 1, 1, tzinfo=UTC)
MONTH_END = datetime(2026, 2, 1, tzinfo=UTC)
MAX_HORIZON = timedelta(hours=48)


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    OUT.mkdir(exist_ok=True)

    actuals = {}
    for r in fetch_actuals(date(2026, 1, 1), date(2026, 1, 31)):
        t = parse(r["startTime"])
        if MONTH_START <= t < MONTH_END:
            actuals[t] = r["generation"]
    with open(OUT / "actuals.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start_time", "generation_mw"])
        for t in sorted(actuals):
            w.writerow([iso(t), actuals[t]])

    forecasts = {}
    for r in fetch_forecasts(MONTH_START - MAX_HORIZON - timedelta(days=1), MONTH_END):
        pub, t = parse(r["publishTime"]), parse(r["startTime"])
        if MONTH_START <= t < MONTH_END and timedelta(0) <= t - pub <= MAX_HORIZON:
            forecasts[(pub, t)] = r["generation"]  # dict key also removes chunk-edge duplicates
    with open(OUT / "forecasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["publish_time", "start_time", "generation_mw"])
        for pub, t in sorted(forecasts):
            w.writerow([iso(pub), iso(t), forecasts[(pub, t)]])

    print(f"actuals: {len(actuals)} half-hours, forecasts: {len(forecasts)} values")


if __name__ == "__main__":
    main()
