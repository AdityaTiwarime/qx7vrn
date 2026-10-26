from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta_describes_the_snapshot():
    m = client.get("/api/meta").json()
    assert m["actuals"]["rows"] == 31 * 48
    assert m["forecasts"]["max_horizon_h"] == 48


def test_series_one_day():
    r = client.get("/api/series", params={"start": "2026-01-15", "end": "2026-01-15", "horizon": 4}).json()
    assert len(r["actual"]) == 48
    assert 0 < len(r["forecast"]) <= 24
    assert all(p["horizon_h"] >= 4 for p in r["forecast"])
    assert all(p["published"] < p["t"] for p in r["forecast"])


def test_series_cutoff_publishes_before_the_day():
    params = {"start": "2026-01-15", "end": "2026-01-15", "mode": "cutoff", "cutoff": "10:00"}
    r = client.get("/api/series", params=params).json()
    assert r["forecast"] and all(p["published"] <= "2026-01-14T10:00:00Z" for p in r["forecast"])


def test_accuracy_whole_month():
    r = client.get("/api/accuracy").json()
    assert r["metrics"]["n"] == 744 and r["metrics"]["coverage"] == 1
    # WINDFOR is published at :30 past the hour, so the longest horizon kept (<= 48 h) is 47.5 h.
    assert [p["horizon_h"] for p in r["horizon_curve"]] == list(range(48))
    assert len(r["by_hour"]) == 24 and len(r["daily"]) == 31


def test_rejects_dates_outside_january():
    assert client.get("/api/series", params={"start": "2025-12-31"}).status_code == 422
    assert client.get("/api/series", params={"start": "2026-01-20", "end": "2026-01-10"}).status_code == 422


def test_rejects_bad_parameters():
    assert client.get("/api/accuracy", params={"horizon": 49}).status_code == 422
    assert client.get("/api/accuracy", params={"mode": "cutoff", "cutoff": "25:00"}).status_code == 422
    assert client.get("/api/accuracy", params={"mode": "weekly"}).status_code == 422
