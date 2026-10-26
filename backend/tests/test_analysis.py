from datetime import time

import pandas as pd
import pytest

from app import analysis
from app.analysis import Selection


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def frame(rows):
    fc = pd.DataFrame(rows, columns=["publish", "target", "forecast"])
    fc["publish"] = fc["publish"].map(ts)
    fc["target"] = fc["target"].map(ts)
    fc["horizon_h"] = (fc["target"] - fc["publish"]).dt.total_seconds() / 3600
    return fc


FC = frame(
    [
        ("2026-01-10T00:00", "2026-01-10T12:00", 100),  # 12 h ahead
        ("2026-01-10T06:00", "2026-01-10T12:00", 200),  # 6 h ahead
        ("2026-01-10T10:00", "2026-01-10T12:00", 300),  # 2 h ahead
        ("2026-01-10T09:30", "2026-01-11T03:00", 400),  # day before, 09:30 UK
        ("2026-01-10T11:00", "2026-01-11T03:00", 500),  # after the cutoff
    ]
)


def test_fixed_horizon_takes_latest_forecast_at_least_h_ahead():
    got = analysis.select_forecasts(FC, Selection("horizon", 4))
    row = got[got["target"] == ts("2026-01-10T12:00")].iloc[0]
    assert row["forecast"] == 200 and row["horizon_h"] == 6


def test_horizon_zero_takes_the_newest():
    got = analysis.select_forecasts(FC, Selection("horizon", 0))
    assert got[got["target"] == ts("2026-01-10T12:00")]["forecast"].item() == 300


def test_target_with_no_old_enough_forecast_is_left_out():
    got = analysis.select_forecasts(FC, Selection("horizon", 13))
    assert ts("2026-01-10T12:00") not in set(got["target"])


def test_cutoff_uses_what_was_published_by_cutoff_on_the_day_before():
    got = analysis.select_forecasts(FC, Selection("cutoff", cutoff=time(10, 0)))
    assert got[got["target"] == ts("2026-01-11T03:00")]["forecast"].item() == 400


def test_cutoff_excludes_forecasts_published_later():
    got = analysis.select_forecasts(FC, Selection("cutoff", cutoff=time(9, 0)))
    assert ts("2026-01-11T03:00") not in set(got["target"])


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError):
        analysis.select_forecasts(FC, Selection("tomorrow"))


def paired(forecasts, actuals):
    targets = [ts(f"2026-01-10T{h:02d}:00") for h in range(len(forecasts))]
    chosen = pd.DataFrame({"target": targets, "forecast": forecasts, "publish": targets, "horizon_h": 0.0})
    act = pd.DataFrame({"time": targets, "actual": actuals})
    return analysis.pair(act, chosen)


def test_error_sign_positive_means_wind_below_forecast():
    p = paired([1000.0], [800.0])
    assert p["error"].item() == 200


def test_metrics_known_values():
    p = paired([110.0, 90.0, 100.0, 140.0], [100.0, 100.0, 100.0, 100.0])  # errors 10, -10, 0, 40
    m = analysis.metrics(p, expected_hours=8)
    assert m["n"] == 4 and m["coverage"] == 0.5
    assert m["mae"] == pytest.approx(15)
    assert m["rmse"] == pytest.approx((1800 / 4) ** 0.5)
    assert m["bias"] == pytest.approx(10)
    assert m["nmae"] == pytest.approx(0.15)
    assert m["max_abs"] == 40
    assert m["mae_debiased"] == pytest.approx((0 + 20 + 10 + 30) / 4)


def test_metrics_empty():
    assert analysis.metrics(paired([], []), expected_hours=24) == {"n": 0, "coverage": 0.0}


def test_pair_skips_hours_without_an_actual():
    targets = [ts("2026-01-10T00:00"), ts("2026-01-10T01:00")]
    chosen = pd.DataFrame({"target": targets, "forecast": [1.0, 2.0], "publish": targets, "horizon_h": 0.0})
    act = pd.DataFrame({"time": [targets[0]], "actual": [1.0]})
    assert len(analysis.pair(act, chosen)) == 1


def test_histogram_counts_every_hour():
    p = paired([100.0, 900.0, -400.0 + 1000], [0.0, 0.0, 1000.0])
    assert sum(b["count"] for b in analysis.histogram(p)) == 3


def test_horizon_curve_error_grows_with_horizon_on_this_toy_data():
    act = pd.DataFrame({"time": [ts("2026-01-10T12:00")], "actual": [300.0]})
    curve = {r["horizon_h"]: r["mae"] for r in analysis.horizon_curve(FC, act, range(0, 13))}
    assert curve[0] == 0 and curve[4] == 100 and curve[12] == 200
