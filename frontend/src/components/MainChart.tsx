import { useMemo } from "react";
import { Area, Brush, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Series } from "../lib/api";
import { fmtDay, fmtHours, fmtMW, fmtTime } from "../lib/format";

interface Point {
  t: number;
  iso: string;
  actual?: number;
  forecast?: number;
  published?: string;
  horizon_h?: number;
  band?: [number, number];
}

/** Actuals are half-hourly, forecasts hourly: merge on time, leave gaps where one is missing. */
export function merge(s: Series): Point[] {
  const byTime = new Map<string, Point>();
  for (const a of s.actual) byTime.set(a.t, { t: Date.parse(a.t), iso: a.t, actual: a.actual });
  for (const f of s.forecast) {
    const p = byTime.get(f.t) ?? { t: Date.parse(f.t), iso: f.t };
    p.forecast = f.forecast;
    p.published = f.published;
    p.horizon_h = f.horizon_h;
    if (p.actual !== undefined) p.band = [Math.min(p.actual, f.forecast), Math.max(p.actual, f.forecast)];
    byTime.set(f.t, p);
  }
  return [...byTime.values()].sort((a, b) => a.t - b.t);
}

function TooltipBody({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const err = p.actual !== undefined && p.forecast !== undefined ? p.forecast - p.actual : undefined;
  return (
    <div className="tip">
      <div className="tip-title">{fmtTime(p.iso)}</div>
      {p.actual !== undefined && (
        <div>
          <i className="dot actual" /> Actual <b>{fmtMW(p.actual)}</b>
        </div>
      )}
      {p.forecast !== undefined && (
        <div>
          <i className="dot forecast" /> Forecast <b>{fmtMW(p.forecast)}</b>
        </div>
      )}
      {err !== undefined && (
        <div className={err > 0 ? "warn" : "ok"}>
          Error {fmtMW(err, { signed: true })} {err > 0 ? "(wind short)" : "(wind extra)"}
        </div>
      )}
      {p.published && (
        <div className="muted small">
          Forecast published {fmtTime(p.published)} · {fmtHours(p.horizon_h ?? 0)} ahead
        </div>
      )}
    </div>
  );
}

export function MainChart({ series }: { series: Series }) {
  const data = useMemo(() => merge(series), [series]);
  const days = data.length ? (data[data.length - 1].t - data[0].t) / 86_400_000 : 0;
  return (
    <div className="chart-main">
      <ResponsiveContainer width="100%" height={380}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="gap" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--rose)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--rose)" stopOpacity={0.12} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(t: number) => (days > 2 ? fmtDay(new Date(t).toISOString()) : fmtTime(new Date(t).toISOString()))}
            stroke="var(--axis)"
            tick={{ fontSize: 12 }}
            minTickGap={40}
          />
          <YAxis
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)} GW`}
            stroke="var(--axis)"
            tick={{ fontSize: 12 }}
            width={52}
          />
          <Tooltip content={<TooltipBody />} />
          <Legend verticalAlign="top" height={30} iconType="plainline" />
          <Area dataKey="band" name="Gap" fill="url(#gap)" stroke="none" connectNulls isAnimationActive={false} legendType="square" />
          <Line dataKey="actual" name="Actual (half-hourly)" stroke="var(--sky)" strokeWidth={2} dot={false} connectNulls isAnimationActive={false} />
          <Line
            dataKey="forecast"
            name="Forecast (hourly)"
            stroke="var(--amber)"
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
          <Brush dataKey="t" height={26} stroke="var(--axis)" fill="var(--panel-2)" travellerWidth={8} tickFormatter={() => ""} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
