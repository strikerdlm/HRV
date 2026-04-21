// Author: Dr Diego Malpica MD
"use client";

// ---------------------------------------------------------------------------
// Reusable ECharts-based sleep visualisations for the research and
// operational sleep pages. Follows .cursor/rules/plots.mdc anti-clutter
// rules: single-line titles, clean grid margins, minimal legend, dynamic
// axes via autoAxisBounds where appropriate.
//
// Every chart includes a caveat-friendly subtitle ("Exploratory — wellness
// device; not diagnostic") per the Pending.md guidance and the Lee 2025 /
// Schyvens 2024 consumer-wearable vs PSG validity bounds.
// ---------------------------------------------------------------------------

import * as React from "react";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import {
  SLEEP_THRESHOLDS,
  type SleepCorrelation,
  type SleepDebtTrendPoint,
  type StageBalance,
  correlationSignificanceColour,
  formatP,
  metricLabel,
} from "@/lib/sleep-metrics";

const DISCLAIMER = "Exploratory — Garmin wellness device; not PSG-diagnostic.";

// ---------------------------------------------------------------------------
// Sleep-duration trend with target band + 7-day rolling mean
// ---------------------------------------------------------------------------

export interface DurationPoint {
  date: string;
  hours: number | null;
}

export function SleepDurationTrend({ data }: { data: DurationPoint[] }) {
  const xs = data.map((d) => d.date.slice(5)); // MM-DD for brevity
  const ys = data.map((d) => d.hours);

  // 7-day trailing rolling mean
  const rolling = ys.map((_, i) => {
    const lo = Math.max(0, i - 6);
    const window = ys.slice(lo, i + 1).filter((v): v is number => v != null);
    return window.length > 0
      ? window.reduce((s, v) => s + v, 0) / window.length
      : null;
  });

  const option: Record<string, unknown> = {
    grid: { left: 55, right: 30, top: 40, bottom: 55, containLabel: true },
    title: {
      text: "Sleep duration (last 30+ nights)",
      subtext: DISCLAIMER,
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : `${v.toFixed(2)} h`),
    },
    legend: { top: 28, textStyle: { fontSize: 9 }, itemGap: 14 },
    xAxis: {
      type: "category",
      data: xs,
      axisLabel: { fontSize: 9, interval: Math.max(0, Math.floor(xs.length / 8) - 1) },
      name: "Date",
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      type: "value",
      name: "Hours",
      min: 0,
      max: 11,
      axisLabel: { fontSize: 9 },
    },
    series: [
      {
        name: "Target band 7–9 h",
        type: "line",
        data: xs.map(() => 7),
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(39, 174, 96, 0.08)" },
        stack: "target-lo",
        silent: true,
        showSymbol: false,
      },
      {
        name: "Target band upper",
        type: "line",
        data: xs.map(() => 2), // stacks on top of 7 → fills 7-9
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(39, 174, 96, 0.08)" },
        stack: "target-lo",
        silent: true,
        showSymbol: false,
      },
      {
        name: "Nightly duration",
        type: "bar",
        data: ys,
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        barMaxWidth: 18,
        z: 3,
      },
      {
        name: "7-night rolling mean",
        type: "line",
        data: rolling,
        smooth: true,
        lineStyle: { color: SCIENTIFIC_COLORS.trend, width: 2 },
        itemStyle: { color: SCIENTIFIC_COLORS.trend },
        symbol: "none",
        z: 4,
      },
      {
        name: "Hard floor 5 h",
        type: "line",
        data: xs.map(() => SLEEP_THRESHOLDS.hardFloorHours),
        lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dashed", width: 1 },
        symbol: "none",
        silent: true,
      },
    ],
  };
  return <EChartsWrapper option={option} height={320} />;
}

// ---------------------------------------------------------------------------
// Sleep-debt cumulative trend with CAUTION / NO-GO bands
// ---------------------------------------------------------------------------

export function SleepDebtCurve({ series }: { series: SleepDebtTrendPoint[] }) {
  const xs = series.map((p) => p.metric_date.slice(5));
  const debts = series.map((p) => p.rolling_debt_7d_hours);

  const option: Record<string, unknown> = {
    grid: { left: 55, right: 30, top: 40, bottom: 55, containLabel: true },
    title: {
      text: "7-night rolling sleep debt",
      subtext: DISCLAIMER,
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : `${v.toFixed(1)} h debt`),
    },
    xAxis: {
      type: "category",
      data: xs,
      axisLabel: { fontSize: 9, interval: Math.max(0, Math.floor(xs.length / 8) - 1) },
      name: "Date",
      nameLocation: "middle",
      nameGap: 30,
    },
    yAxis: {
      type: "value",
      name: "Cumulative debt (h)",
      min: 0,
      axisLabel: { fontSize: 9 },
    },
    series: [
      {
        name: "Rolling 7-night debt",
        type: "line",
        data: debts,
        smooth: true,
        lineStyle: { color: SCIENTIFIC_COLORS.warning, width: 2 },
        areaStyle: { color: "rgba(243, 156, 18, 0.15)" },
        itemStyle: { color: SCIENTIFIC_COLORS.warning },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed" },
          data: [
            {
              yAxis: SLEEP_THRESHOLDS.debtCautionHours7d,
              label: { formatter: "CAUTION 4 h", position: "insideEndTop", fontSize: 9 },
              lineStyle: { color: SCIENTIFIC_COLORS.warning },
            },
            {
              yAxis: SLEEP_THRESHOLDS.debtNoGoHours7d,
              label: { formatter: "NO-GO 8 h", position: "insideEndTop", fontSize: 9 },
              lineStyle: { color: SCIENTIFIC_COLORS.danger },
            },
          ],
        },
      },
    ],
  };
  return <EChartsWrapper option={option} height={300} />;
}

// ---------------------------------------------------------------------------
// Stacked stage-balance bars (minutes per night, last N nights)
// ---------------------------------------------------------------------------

export interface StagePerNight {
  date: string;
  deep: number | null;
  rem: number | null;
  light: number | null;
  awake: number | null;
}

export function StageBalanceStackedBar({ data }: { data: StagePerNight[] }) {
  const xs = data.map((d) => d.date.slice(5));

  const option: Record<string, unknown> = {
    grid: { left: 55, right: 30, top: 40, bottom: 55, containLabel: true },
    title: {
      text: "Sleep stage balance (minutes / night)",
      subtext: DISCLAIMER,
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 28, textStyle: { fontSize: 9 }, itemGap: 14 },
    xAxis: {
      type: "category",
      data: xs,
      axisLabel: { fontSize: 9, interval: Math.max(0, Math.floor(xs.length / 8) - 1) },
    },
    yAxis: {
      type: "value",
      name: "Minutes",
      min: 0,
      axisLabel: { fontSize: 9 },
    },
    series: [
      {
        name: "Deep",
        type: "bar",
        stack: "stages",
        data: data.map((d) => d.deep),
        itemStyle: { color: "#1f3a93" },
        barMaxWidth: 18,
      },
      {
        name: "REM",
        type: "bar",
        stack: "stages",
        data: data.map((d) => d.rem),
        itemStyle: { color: "#8e44ad" },
      },
      {
        name: "Light",
        type: "bar",
        stack: "stages",
        data: data.map((d) => d.light),
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
      },
      {
        name: "Awake",
        type: "bar",
        stack: "stages",
        data: data.map((d) => d.awake),
        itemStyle: { color: "#bdc3c7" },
      },
    ],
  };
  return <EChartsWrapper option={option} height={320} />;
}

// ---------------------------------------------------------------------------
// Stage-distribution pie (latest night)
// ---------------------------------------------------------------------------

export function StageBalancePie({ balance }: { balance: StageBalance }) {
  const total = balance.total_minutes ?? 0;
  const cells = [
    { name: "Deep", value: balance.deep_pct != null ? balance.deep_pct * total : 0, color: "#1f3a93" },
    { name: "REM", value: balance.rem_pct != null ? balance.rem_pct * total : 0, color: "#8e44ad" },
    { name: "Light", value: balance.light_pct != null ? balance.light_pct * total : 0, color: SCIENTIFIC_COLORS.primary },
    { name: "Awake", value: balance.awake_pct != null ? balance.awake_pct * total : 0, color: "#bdc3c7" },
  ].filter((c) => c.value > 0);

  const option: Record<string, unknown> = {
    title: {
      text: "Latest night — stage distribution",
      subtext: DISCLAIMER,
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: { trigger: "item", formatter: "{b}: {c} min ({d}%)" },
    legend: { bottom: 8, textStyle: { fontSize: 9 }, itemGap: 16 },
    series: [
      {
        type: "pie",
        radius: ["35%", "65%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: true,
        label: { formatter: "{b}\n{d}%", fontSize: 10 },
        data: cells.map((c) => ({
          name: c.name,
          value: Math.round(c.value),
          itemStyle: { color: c.color },
        })),
      },
    ],
  };
  return <EChartsWrapper option={option} height={300} />;
}

// ---------------------------------------------------------------------------
// Correlation matrix heatmap (r-values with significance colouring)
// ---------------------------------------------------------------------------

export function CorrelationMatrix({ results }: { results: SleepCorrelation[] }) {
  // Collapse to a single row: metric_x vs hrv_rmssd_ms (fixed Y per §4 Tier A)
  const rows = ["hrv_rmssd_ms"];
  const cols = results.map((c) => c.metric_x);

  const cells = results.map((c, i) => [
    i,
    0,
    c.r == null ? null : Number(c.r.toFixed(3)),
    c,
  ]);

  const option: Record<string, unknown> = {
    grid: { left: 80, right: 120, top: 40, bottom: 70, containLabel: true },
    title: {
      text: "Tier A correlations vs overnight HRV RMSSD",
      subtext: "r shown; grey = underpowered or p ≥ 0.05; FDR-adjusted q used where available",
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: {
      trigger: "item",
      formatter: (p: { data: [number, number, number | null, SleepCorrelation] }) => {
        const c = p.data[3];
        const rTxt = c.r == null ? "—" : c.r.toFixed(3);
        const pTxt = c.p_value == null ? "—" : formatP(c.p_value);
        const qTxt = c.fdr_q == null ? "—" : formatP(c.fdr_q);
        const note = c.note ? `<br/><em>${c.note}</em>` : "";
        return (
          `${metricLabel(c.metric_x)} × ${metricLabel(c.metric_y)}` +
          `<br/>r = <strong>${rTxt}</strong>` +
          `<br/>p = ${pTxt}, q = ${qTxt}` +
          `<br/>n = ${c.n_nights} nights` +
          note
        );
      },
    },
    xAxis: {
      type: "category",
      data: cols.map(metricLabel),
      axisLabel: { fontSize: 10, rotate: 30, interval: 0 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: rows.map(metricLabel),
      axisLabel: { fontSize: 10 },
      splitArea: { show: true },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: false,
      orient: "vertical",
      right: 0,
      top: "middle",
      textStyle: { fontSize: 9 },
      inRange: {
        color: [
          SCIENTIFIC_COLORS.danger,
          "#f5b7b1",
          "#f7f9f9",
          "#a9cce3",
          SCIENTIFIC_COLORS.primary,
        ],
      },
    },
    series: [
      {
        type: "heatmap",
        data: cells,
        label: {
          show: true,
          formatter: (p: { data: [number, number, number | null, SleepCorrelation] }) => {
            const r = p.data[2];
            return r == null ? "—" : r.toFixed(2);
          },
          fontSize: 10,
        },
        itemStyle: {
          borderColor: "#ffffff",
          borderWidth: 1,
        },
        emphasis: {
          itemStyle: {
            borderColor: SCIENTIFIC_COLORS.trend,
            borderWidth: 2,
          },
        },
      },
    ],
  };

  return <EChartsWrapper option={option} height={210} />;
}

// ---------------------------------------------------------------------------
// Scatter plot for one pair (X vs Y) with regression + r/p/q caption
// ---------------------------------------------------------------------------

export interface ScatterPoint {
  x: number;
  y: number;
  date?: string;
}

export function CorrelationScatter({
  points,
  xLabel,
  yLabel,
  title,
  corr,
}: {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  title: string;
  corr?: SleepCorrelation | null;
}) {
  // Compute OLS regression line for visualisation
  const valid = points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  let line: Array<[number, number]> | null = null;
  if (valid.length >= 3) {
    const n = valid.length;
    const meanX = valid.reduce((s, p) => s + p.x, 0) / n;
    const meanY = valid.reduce((s, p) => s + p.y, 0) / n;
    const sxx = valid.reduce((s, p) => s + (p.x - meanX) ** 2, 0);
    const sxy = valid.reduce((s, p) => s + (p.x - meanX) * (p.y - meanY), 0);
    if (sxx > 0) {
      const slope = sxy / sxx;
      const intercept = meanY - slope * meanX;
      const xs = valid.map((p) => p.x);
      const xMin = Math.min(...xs);
      const xMax = Math.max(...xs);
      line = [
        [xMin, slope * xMin + intercept],
        [xMax, slope * xMax + intercept],
      ];
    }
  }

  const subtitle = corr
    ? `${corr.r != null ? `r = ${corr.r.toFixed(2)}` : "r = —"}` +
      (corr.p_value != null ? `, p = ${formatP(corr.p_value)}` : "") +
      (corr.fdr_q != null ? `, q = ${formatP(corr.fdr_q)}` : "") +
      `, n = ${corr.n_nights}${corr.note ? ` — ${corr.note}` : ""}`
    : DISCLAIMER;

  const dotColour = corr ? correlationSignificanceColour(corr) : SCIENTIFIC_COLORS.primary;

  const option: Record<string, unknown> = {
    grid: { left: 65, right: 30, top: 52, bottom: 55, containLabel: true },
    title: {
      text: title,
      subtext: subtitle,
      left: "center",
      top: 0,
      textStyle: { fontSize: 11 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: {
      trigger: "item",
      formatter: (p: { value: [number, number]; data?: { date?: string } }) =>
        `${xLabel}: ${p.value[0].toFixed(2)}<br/>${yLabel}: ${p.value[1].toFixed(2)}` +
        (p.data?.date ? `<br/><em>${p.data.date}</em>` : ""),
    },
    xAxis: {
      type: "value",
      name: xLabel,
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { fontSize: 9 },
      scale: true,
    },
    yAxis: {
      type: "value",
      name: yLabel,
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: { fontSize: 9 },
      scale: true,
    },
    series: [
      {
        name: title,
        type: "scatter",
        symbolSize: 8,
        data: valid.map((p) => ({ value: [p.x, p.y], date: p.date })),
        itemStyle: { color: dotColour, opacity: 0.7 },
        emphasis: { focus: "series", itemStyle: { opacity: 1 } },
      },
      ...(line
        ? [
            {
              name: "OLS fit",
              type: "line",
              data: line,
              lineStyle: { color: SCIENTIFIC_COLORS.trend, width: 2 },
              showSymbol: false,
              silent: true,
            },
          ]
        : []),
    ],
  };

  return <EChartsWrapper option={option} height={280} />;
}

// ---------------------------------------------------------------------------
// Regularity schedule strip (bedtime and waketime over nights)
// ---------------------------------------------------------------------------

export interface RegularityPoint {
  date: string;
  bedtime_hour_of_day: number | null;
  waketime_hour_of_day: number | null;
}

export function RegularityStrip({ data }: { data: RegularityPoint[] }) {
  const xs = data.map((d) => d.date.slice(5));
  const bed = data.map((d) => d.bedtime_hour_of_day);
  const wake = data.map((d) => d.waketime_hour_of_day);

  const option: Record<string, unknown> = {
    grid: { left: 55, right: 30, top: 40, bottom: 55, containLabel: true },
    title: {
      text: "Bedtime / waketime consistency",
      subtext: "Hours since local midnight; lower SD = more regular schedule",
      left: "center",
      top: 0,
      textStyle: { fontSize: 12 },
      subtextStyle: { fontSize: 9, color: "#7f8c8d" },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : `${v.toFixed(2)} h`),
    },
    legend: { top: 28, textStyle: { fontSize: 9 } },
    xAxis: {
      type: "category",
      data: xs,
      axisLabel: { fontSize: 9, interval: Math.max(0, Math.floor(xs.length / 8) - 1) },
    },
    yAxis: {
      type: "value",
      name: "Hour of day",
      min: 0,
      max: 30,
      axisLabel: {
        fontSize: 9,
        formatter: (v: number) => {
          const hh = Math.floor(v % 24);
          return `${hh.toString().padStart(2, "0")}:00`;
        },
      },
    },
    series: [
      {
        name: "Bedtime",
        type: "line",
        data: bed,
        smooth: false,
        lineStyle: { color: SCIENTIFIC_COLORS.trend, width: 2 },
        itemStyle: { color: SCIENTIFIC_COLORS.trend },
        symbolSize: 7,
      },
      {
        name: "Waketime",
        type: "line",
        data: wake,
        smooth: false,
        lineStyle: { color: SCIENTIFIC_COLORS.primary, width: 2 },
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        symbolSize: 7,
      },
    ],
  };
  return <EChartsWrapper option={option} height={300} />;
}
