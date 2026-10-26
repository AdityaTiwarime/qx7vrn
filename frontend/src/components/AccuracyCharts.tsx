import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Accuracy } from "../lib/api";
import { fmtDay, fmtMW } from "../lib/format";

const gw = (v: number) => `${(v / 1000).toFixed(1)}`;
const axis = { stroke: "var(--axis)", tick: { fontSize: 12 } };
const tip = {
  contentStyle: { background: "var(--panel-2)", border: "1px solid var(--line)", borderRadius: 10 },
  labelStyle: { color: "var(--text)" },
  formatter: (v: number) => fmtMW(v, { signed: true }),
};

function Card({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <p className="muted small">{sub}</p>
      {children}
    </div>
  );
}

export function HorizonCurve({ rows, marker }: { rows: Accuracy["horizon_curve"]; marker?: number }) {
  return (
    <Card title="Error vs lead time" sub="How accuracy falls the earlier the forecast is made (all hours in the selected days). GW.">
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 8 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="horizon_h" {...axis} label={{ value: "hours ahead", position: "insideBottom", offset: -4, fill: "var(--muted)", fontSize: 12 }} />
          <YAxis tickFormatter={gw} {...axis} />
          <Tooltip {...tip} labelFormatter={(h) => `${h} h ahead`} />
          <Legend verticalAlign="top" height={26} iconType="plainline" />
          {marker !== undefined && <ReferenceLine x={Math.round(marker)} stroke="var(--violet)" strokeDasharray="4 4" label={{ value: "selected", fill: "var(--violet)", fontSize: 11, position: "insideTop" }} />}
          <Line dataKey="p90_abs" name="P90 error" stroke="var(--rose)" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line dataKey="mae" name="MAE" stroke="var(--amber)" dot={false} strokeWidth={2} isAnimationActive={false} />
          <Line dataKey="bias" name="Bias" stroke="var(--sky)" dot={false} strokeWidth={2} strokeDasharray="5 4" isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function ByHour({ rows }: { rows: Accuracy["by_hour"] }) {
  return (
    <Card title="Error by time of day" sub="UK hour of the delivery period. Bars: MAE, line: bias. GW.">
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 8 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="hour" {...axis} tickFormatter={(h: number) => `${String(h).padStart(2, "0")}:00`} minTickGap={16} />
          <YAxis tickFormatter={gw} {...axis} />
          <Tooltip {...tip} labelFormatter={(h) => `${String(h).padStart(2, "0")}:00 UK`} />
          <Bar dataKey="mae" name="MAE" fill="var(--amber)" fillOpacity={0.75} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          <Line dataKey="bias" name="Bias" stroke="var(--sky)" dot={false} strokeWidth={2} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function Histogram({ rows }: { rows: Accuracy["histogram"] }) {
  const data = rows.map((r) => ({ ...r, mid: (r.from + r.to) / 2 }));
  return (
    <Card title="How big the misses were" sub="Hours by forecast − actual. Right of zero (red): wind came in short. GW.">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 12, left: -8, bottom: 8 }} barCategoryGap={1}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="from" {...axis} tickFormatter={gw} />
          <YAxis {...axis} allowDecimals={false} />
          <Tooltip
            contentStyle={tip.contentStyle}
            labelStyle={tip.labelStyle}
            formatter={(v: number) => [`${v} hours`, "count"]}
            labelFormatter={(_, p) => (p?.[0] ? `${fmtMW(p[0].payload.from, { signed: true })} to ${fmtMW(p[0].payload.to, { signed: true })}` : "")}
          />
          <ReferenceLine x={0} stroke="var(--axis)" />
          <Bar dataKey="count" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {data.map((r) => (
              <Cell key={r.from} fill={r.mid > 0 ? "var(--rose)" : "var(--sky)"} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function Daily({ rows }: { rows: Accuracy["daily"] }) {
  return (
    <Card title="Day by day" sub="Average forecast − actual per delivery day. Tall red bars: days to have bought more. GW.">
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 12, left: -8, bottom: 8 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="day" {...axis} tickFormatter={(d: string) => fmtDay(d)} minTickGap={12} />
          <YAxis tickFormatter={gw} {...axis} />
          <Tooltip {...tip} labelFormatter={(d) => fmtDay(String(d))} />
          <ReferenceLine y={0} stroke="var(--axis)" />
          <Bar dataKey="bias" name="Bias" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {rows.map((r) => (
              <Cell key={r.day} fill={r.bias > 0 ? "var(--rose)" : "var(--sky)"} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
