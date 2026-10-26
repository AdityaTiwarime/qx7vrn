// Typed client for the backend (see backend/app/main.py).

export type Mode = "cutoff" | "horizon";

export interface Query {
  start: string; // YYYY-MM-DD, UK delivery day
  end: string;
  mode: Mode;
  horizon: number; // hours, mode=horizon
  cutoff: string; // HH:MM UK, day before delivery, mode=cutoff
}

export interface ActualPoint {
  t: string;
  actual: number;
}

export interface ForecastPoint {
  t: string;
  forecast: number;
  published: string;
  horizon_h: number;
  error: number;
}

export interface Series {
  actual: ActualPoint[];
  forecast: ForecastPoint[];
}

export interface Metrics {
  n: number;
  coverage: number;
  mae?: number;
  rmse?: number;
  bias?: number;
  nmae?: number;
  mae_debiased?: number;
  p50_abs?: number;
  p90_abs?: number;
  p99_abs?: number;
  max_abs?: number;
  shortfall_p90?: number;
  shortfall_p95?: number;
  mean_actual?: number;
  mean_forecast?: number;
  mean_horizon_h?: number;
}

export interface HorizonRow {
  horizon_h: number;
  n: number;
  mae: number;
  rmse: number;
  bias: number;
  p90_abs: number;
}

export interface Accuracy {
  metrics: Metrics;
  by_hour: { hour: number; mae: number; bias: number; n: number }[];
  histogram: { from: number; to: number; count: number }[];
  daily: { day: string; mae: number; bias: number; actual_mwh: number; forecast_mwh: number }[];
  horizon_curve: HorizonRow[];
}

export class ApiError extends Error {}

function qs(q: Query): string {
  const p = new URLSearchParams({ start: q.start, end: q.end, mode: q.mode });
  if (q.mode === "horizon") p.set("horizon", String(q.horizon));
  else p.set("cutoff", q.cutoff);
  return p.toString();
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, { signal });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  series: (q: Query, signal?: AbortSignal) => get<Series>(`/api/series?${qs(q)}`, signal),
  accuracy: (q: Query, signal?: AbortSignal) => get<Accuracy>(`/api/accuracy?${qs(q)}`, signal),
};
