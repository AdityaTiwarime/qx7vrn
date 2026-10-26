import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Insight, Kpis } from "../src/components/Kpis";
import { merge } from "../src/components/MainChart";
import { fmtMW } from "../src/lib/format";

describe("merge", () => {
  it("joins half-hourly actuals with hourly forecasts and draws the gap only where both exist", () => {
    const points = merge({
      actual: [
        { t: "2026-01-05T00:00:00Z", actual: 10_000 },
        { t: "2026-01-05T00:30:00Z", actual: 10_500 },
      ],
      forecast: [{ t: "2026-01-05T00:00:00Z", forecast: 12_000, published: "2026-01-04T10:00:00Z", horizon_h: 14, error: 2000 }],
    });
    expect(points).toHaveLength(2);
    expect(points[0].band).toEqual([10_000, 12_000]);
    expect(points[1].forecast).toBeUndefined();
    expect(points[1].band).toBeUndefined();
  });
});

describe("fmtMW", () => {
  it("formats megawatts and signs", () => {
    expect(fmtMW(1834)).toBe("1,834 MW");
    expect(fmtMW(12_345)).toBe("12.3 GW");
    expect(fmtMW(250, { signed: true })).toBe("+250 MW");
    expect(fmtMW(-250, { signed: true })).toBe("−250 MW");
    expect(fmtMW(undefined)).toBe("–");
  });
});

const metrics = { n: 744, coverage: 1, mae: 2107, nmae: 0.18, bias: 1840, mae_debiased: 1460, max_abs: 6857, shortfall_p90: 4377, shortfall_p95: 5401, mean_horizon_h: 26 };

describe("headline", () => {
  it("states the buffer that covers 9 hours in 10", () => {
    render(<Insight m={metrics} q={{ start: "2026-01-01", end: "2026-01-31", mode: "cutoff", horizon: 4, cutoff: "10:00" }} />);
    expect(screen.getByText(/4,377 MW less wind than forecast/)).toBeTruthy();
    expect(screen.getByText(/1,840 MW high/)).toBeTruthy();
  });

  it("shows nothing when no hours could be scored", () => {
    const { container } = render(<Kpis m={{ n: 0, coverage: 0 }} />);
    expect(container.innerHTML).toBe("");
  });
});
