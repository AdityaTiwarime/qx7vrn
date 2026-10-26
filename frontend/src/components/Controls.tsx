import type { Mode, Query } from "../lib/api";

const FIRST = "2026-01-01";
const LAST = "2026-01-31";

interface Props {
  q: Query;
  onChange: (q: Query) => void;
}

const PRESETS: { label: string; start: string; end: string }[] = [
  { label: "All January", start: FIRST, end: LAST },
  { label: "Week 1", start: "2026-01-01", end: "2026-01-07" },
  { label: "Week 2", start: "2026-01-08", end: "2026-01-14" },
  { label: "Week 3", start: "2026-01-15", end: "2026-01-21" },
  { label: "Week 4+", start: "2026-01-22", end: LAST },
];

export function Controls({ q, onChange }: Props) {
  const set = (patch: Partial<Query>) => onChange({ ...q, ...patch });
  const setMode = (mode: Mode) => set({ mode });

  return (
    <section className="controls" aria-label="What to show">
      <div className="control">
        <span className="label">Delivery days</span>
        <div className="row">
          <input
            type="date"
            aria-label="From"
            min={FIRST}
            max={q.end}
            value={q.start}
            onChange={(e) => e.target.value && set({ start: e.target.value })}
          />
          <span className="muted">to</span>
          <input
            type="date"
            aria-label="To"
            min={q.start}
            max={LAST}
            value={q.end}
            onChange={(e) => e.target.value && set({ end: e.target.value })}
          />
        </div>
        <div className="chips">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              className={`chip ${q.start === p.start && q.end === p.end ? "on" : ""}`}
              onClick={() => set({ start: p.start, end: p.end })}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div className="control">
        <span className="label">Which forecast</span>
        <div className="segmented" role="tablist">
          <button role="tab" aria-selected={q.mode === "cutoff"} className={q.mode === "cutoff" ? "on" : ""} onClick={() => setMode("cutoff")}>
            Day-ahead decision
          </button>
          <button role="tab" aria-selected={q.mode === "horizon"} className={q.mode === "horizon" ? "on" : ""} onClick={() => setMode("horizon")}>
            Fixed horizon
          </button>
        </div>
        {q.mode === "cutoff" ? (
          <label className="row hint">
            Latest forecast published by
            <input
              type="time"
              step={1800}
              aria-label="Decision time"
              value={q.cutoff}
              onChange={(e) => e.target.value && set({ cutoff: e.target.value })}
            />
            UK time, the day before delivery
          </label>
        ) : (
          <label className="row hint slider">
            <span>
              Latest forecast published at least <b>{q.horizon} h</b> before each hour
            </span>
            <input
              type="range"
              min={0}
              max={47}
              step={1}
              aria-label="Forecast horizon in hours"
              value={q.horizon}
              onChange={(e) => set({ horizon: Number(e.target.value) })}
            />
          </label>
        )}
      </div>
    </section>
  );
}
