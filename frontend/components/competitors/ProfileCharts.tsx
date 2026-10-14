"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPoint, ScoreSeries } from "@/lib/api";
import styles from "./CompetitorProfile.module.css";

const COMPETITOR_FILL = "#55466f";
const SCADABLE_FILL = "#4d64b9";
const ACTIVITY_STROKE = "#a64f45";

export function ScoresChart({ data }: { data: ScoreSeries[] }) {
  if (!data.length) {
    return <p className={styles.empty}>No score comparison yet.</p>;
  }

  return (
    <div className={styles.chartWrap}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--sub)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--line)" }}
            interval={0}
          />
          <YAxis
            domain={[0, 10]}
            tick={{ fill: "var(--sub)", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              borderRadius: 6,
              border: "1px solid var(--line)",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="competitor" name="Competitor" fill={COMPETITOR_FILL} radius={[3, 3, 0, 0]} />
          <Bar dataKey="scadable" name="SCADABLE" fill={SCADABLE_FILL} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActivityChart({ data }: { data: ChartPoint[] }) {
  if (!data.length) {
    return <p className={styles.empty}>No activity series yet.</p>;
  }

  return (
    <div className={styles.chartWrap}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--sub)", fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: "var(--line)" }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "var(--sub)", fontSize: 10 }}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              fontSize: 11,
              borderRadius: 6,
              border: "1px solid var(--line)",
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            name="Signals"
            stroke={ACTIVITY_STROKE}
            strokeWidth={2}
            dot={{ r: 3, fill: ACTIVITY_STROKE }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
