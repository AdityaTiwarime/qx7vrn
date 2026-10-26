import type { Metrics, Query } from "../lib/api";
import { fmtHours, fmtMW, fmtPct } from "../lib/format";

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: "warn" | "accent" }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-sub">{sub}</div>
    </div>
  );
}

export function Kpis({ m }: { m: Metrics }) {
  if (!m.n) return null;
  return (
    <section className="kpis" aria-label="Headline accuracy">
      <Kpi label="Typical error (MAE)" value={fmtMW(m.mae)} sub={`${fmtPct(m.nmae)} of average wind output`} />
      <Kpi
        label="Forecast bias"
        value={fmtMW(m.bias, { signed: true })}
        sub={(m.bias ?? 0) > 0 ? "forecast ran high on average" : "forecast ran low on average"}
        tone="warn"
      />
      <Kpi
        label="Error if bias removed"
        value={fmtMW(m.mae_debiased)}
        sub={`a steady offset explains ${fmtPct(m.mae && m.mae_debiased !== undefined ? 1 - m.mae_debiased / m.mae : undefined)} of the error · worst hour ${fmtMW(m.max_abs)}`}
      />
      <Kpi
        label="Buffer for 90% of hours"
        value={fmtMW(m.shortfall_p90)}
        sub={`wind fell short of forecast by less than this in 90% of hours · 95%: ${fmtMW(m.shortfall_p95)}`}
        tone="accent"
      />
      <Kpi
        label="Hours scored"
        value={m.n.toLocaleString("en-GB")}
        sub={`${fmtPct(m.coverage)} coverage · avg lead time ${fmtHours(Math.round((m.mean_horizon_h ?? 0) * 10) / 10)}`}
      />
    </section>
  );
}

export function Insight({ m, q }: { m: Metrics; q: Query }) {
  if (!m.n || m.mae === undefined) return null;
  const which =
    q.mode === "cutoff"
      ? `the forecast available at ${q.cutoff} the day before`
      : `the latest forecast made at least ${q.horizon} h ahead`;
  const high = (m.bias ?? 0) > 0;
  return (
    <p className="insight">
      Over these days, {which} was off by <b>{fmtMW(m.mae)}</b> in a typical hour ({fmtPct(m.nmae)} of output) and ran{" "}
      <b className={high ? "warn" : ""}>
        {fmtMW(Math.abs(m.bias ?? 0))} {high ? "high" : "low"}
      </b>{" "}
      on average. Planning for <b className="accent">{fmtMW(m.shortfall_p90)} less wind than forecast</b> would have covered
      the shortfall in 9 hours out of 10.
    </p>
  );
}
