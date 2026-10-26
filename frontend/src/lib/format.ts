// Display helpers. Times are shown in UK local time (GMT in January).

const uk = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/London", ...opts });
const dayHour = uk({ day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false });
const dayOnly = uk({ day: "numeric", month: "short" });

export const fmtTime = (iso: string) => dayHour.format(new Date(iso));
export const fmtDay = (iso: string) => dayOnly.format(new Date(iso));

/** 1834 -> "1,834 MW"; 12345 -> "12.3 GW". */
export function fmtMW(mw: number | undefined, { signed = false } = {}): string {
  if (mw === undefined || Number.isNaN(mw)) return "–";
  const sign = signed && mw > 0 ? "+" : mw < 0 ? "−" : "";
  const v = Math.abs(mw);
  return v >= 10_000 ? `${sign}${(v / 1000).toFixed(1)} GW` : `${sign}${Math.round(v).toLocaleString("en-GB")} MW`;
}

export const fmtGW = (mw: number | undefined, digits = 1) =>
  mw === undefined ? "–" : `${(mw / 1000).toFixed(digits)} GW`;

export const fmtPct = (x: number | undefined, digits = 0) =>
  x === undefined || x === null ? "–" : `${(x * 100).toFixed(digits)}%`;

export function fmtHours(h: number): string {
  return Number.isInteger(h) ? `${h} h` : `${h.toFixed(1)} h`;
}
