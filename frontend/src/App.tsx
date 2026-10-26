import { useState } from "react";

import { ByHour, Daily, HorizonCurve, Histogram } from "./components/AccuracyCharts";
import { Controls } from "./components/Controls";
import { Insight, Kpis } from "./components/Kpis";
import { MainChart } from "./components/MainChart";
import type { Query } from "./lib/api";
import { useData } from "./lib/useData";

export const DEFAULT_QUERY: Query = { start: "2026-01-01", end: "2026-01-31", mode: "cutoff", horizon: 4, cutoff: "10:00" };

function Logo() {
  return (
    <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--panel-2)" stroke="var(--line)" />
      <path d="M16 16 L16 5.5 M16 16 L25 21.2 M16 16 L7 21.2" stroke="var(--sky)" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="16" cy="16" r="2.4" fill="var(--amber)" />
    </svg>
  );
}

export default function App() {
  const [q, setQ] = useState<Query>(DEFAULT_QUERY);
  const { series, accuracy, loading, error } = useData(q);
  const m = accuracy?.metrics;
  const marker = q.mode === "horizon" ? q.horizon : m?.mean_horizon_h;

  return (
    <div className="page">
      <header className="top">
        <div className="brand">
          <Logo />
          <div>
            <h1>Wind Forecast Monitor</h1>
            <p className="muted">GB national wind · Elexon actuals vs WINDFOR forecasts · January 2026</p>
          </div>
        </div>
        <div className={`status ${loading ? "busy" : error ? "bad" : "ok"}`} role="status">
          {loading ? "Updating…" : error ? "Couldn't load" : "Analysis ready"}
        </div>
      </header>

      <Controls q={q} onChange={setQ} />

      {error && (
        <div className="banner" role="alert">
          {error} {series && "· showing the last result"}
        </div>
      )}

      {!series && !error && <div className="skeleton" aria-busy="true" />}

      {series && accuracy && m && (
        <main className={loading ? "stale" : ""}>
          <Insight m={m} q={q} />
          <Kpis m={m} />

          <section className="card big">
            <div className="card-head">
              <div>
                <h2>Actual vs forecast wind generation</h2>
                <p className="muted small">
                  Shaded: the gap the trading team had to cover. Drag the handles below the chart to zoom. Times in UK time.
                </p>
              </div>
            </div>
            {series.forecast.length === 0 ? (
              <p className="empty">No forecast was published early enough for these hours. Try a shorter horizon or a later cut-off.</p>
            ) : (
              <MainChart series={series} />
            )}
          </section>

          <section className="grid">
            <HorizonCurve rows={accuracy.horizon_curve} marker={marker} />
            <ByHour rows={accuracy.by_hour} />
            <Histogram rows={accuracy.histogram} />
            <Daily rows={accuracy.daily} />
          </section>

          <section className="card notes">
            <h2>How to read this</h2>
            <ul>
              <li>
                <b>Day-ahead decision</b> shows, for every hour of a delivery day, the newest forecast that existed at the chosen time on the
                day before: what was on screen when buying. <b>Fixed horizon</b> instead takes the newest forecast made at least N hours
                before each hour.
              </li>
              <li>
                <b>Error = forecast − actual.</b> Positive means wind came in below the forecast, a shortfall to cover from other sources.
              </li>
              <li>
                <b>Buffer for 90% of hours</b> is the 90th percentile of that error: holding this much extra capacity would have covered the
                wind shortfall in 9 hours out of 10.
              </li>
              <li>
                Forecasts are hourly and actuals half-hourly, so accuracy is scored on the hours where both exist. Only forecasts made 0–48 h
                ahead are used.
              </li>
            </ul>
          </section>
        </main>
      )}

      <footer className="muted small">
        Data: Elexon BMRS — FUELHH (fuel type WIND) and WINDFOR, January 2026 snapshot. Pilot analysis, not a trading recommendation.
      </footer>
    </div>
  );
}
