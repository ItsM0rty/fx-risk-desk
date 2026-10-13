import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import type { ForecastSeries, RiskSeries } from "@fx-risk-desk/client";
import { day, month, percent, usd } from "./format";

const axis = { fill: "#98a7b9", fontSize: 11 };
const grid = "#263449";
const tooltip = { background: "#162236", border: "1px solid #35445a", borderRadius: 8 };
const mint = "#67e8ba";
const blue = "#90a9f8";
const orange = "#f6ad7a";

function dollarTick(value: number) {
  return value === 0 ? "$0" : `${value < 0 ? "−" : ""}$${Math.abs(value / 1000)}k`;
}

export function RiskChart({ points }: { points: RiskSeries["points"] }) {
  const data = points.map((point) => ({
    ...point,
    threshold: -point.var,
  }));

  return (
    <div className="chart risk-chart" aria-label="Daily P&L, one-day VaR threshold, and breaches">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ left: -5, right: 14, top: 13, bottom: 0 }}>
          <CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="date" tickFormatter={month} tick={axis} tickLine={false} axisLine={false} minTickGap={33} />
          <YAxis tickFormatter={dollarTick} tick={axis} tickLine={false} axisLine={false} width={65} />
          <Tooltip contentStyle={tooltip} labelFormatter={day}
            formatter={(value: number) => usd(value)} />
          <ReferenceLine y={0} stroke="#495a71" />
          <Line type="linear" dataKey="unhedged_pnl" name="Unhedged P&L" stroke={blue}
            strokeWidth={1} dot={false} isAnimationActive={false} />
          <Line type="linear" dataKey="pnl" name="Selected policy P&L" stroke={mint}
            strokeWidth={1.45} dot={false} isAnimationActive={false} />
          <Line type="stepAfter" dataKey="threshold" name="VaR threshold" stroke={orange}
            strokeWidth={1.6} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
          {points.filter(({ breach }) => breach).map((point) => (
            <ReferenceDot key={point.date} x={point.date} y={point.pnl} r={4}
              fill={orange} stroke="#111b2c" />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ForecastChart({ points }: { points: ForecastSeries["points"] }) {
  const data = points.map((point) => ({ ...point, band: [point.low, point.high] }));

  return (
    <div className="chart forecast-chart" aria-label="Actual EUR/USD returns and the walk-forward forecast interval">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ left: -7, right: 14, top: 12, bottom: 0 }}>
          <CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="date" tickFormatter={month} tick={axis} tickLine={false} axisLine={false} minTickGap={34} />
          <YAxis tickFormatter={(value) => percent(value)} tick={axis} tickLine={false} axisLine={false} width={62} />
          <Tooltip contentStyle={tooltip} labelFormatter={day} formatter={(value) =>
            Array.isArray(value) ? value.map((v) => percent(Number(v), 2)).join(" to ") : percent(Number(value), 2)} />
          <ReferenceLine y={0} stroke="#495a71" />
          <Area dataKey="band" name="P10–P90 interval" fill={blue} fillOpacity={0.2}
            stroke="none" isAnimationActive={false} />
          <Line type="linear" dataKey="median" name="Median forecast" stroke={blue}
            strokeDasharray="4 4" dot={false} isAnimationActive={false} />
          <Line type="linear" dataKey="actual" name="Observed return" stroke={mint}
            strokeWidth={1.3} dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
