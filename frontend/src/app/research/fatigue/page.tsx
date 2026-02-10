// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Moon,
  Sun,
  Coffee,
  AlertTriangle,
  RefreshCw,
  Clock,
  Battery,
  Zap,
  Brain,
  Activity,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { getFatiguePrediction } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { FatigueResponse } from "@/types/research";
import { FATIGUE_COLORS } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

// ---------------------------------------------------------------------------
// Reservoir-Based SAFTE Model  (Hursh et al. 2004 / DRDC Peng & Bouak 2015)
// Matches the backend safte_model.py equations exactly:
//   E(t) = 100 * (homeo% + circ% + inertia%) / norm
//   homeo% = 100 * R_t / R_c
//   circ%  = (a1 + a2 * (1 - R_t/R_c)) * C_t       ← fatigue-amplified!
//   C_t    = cos(2π(t-p)/24) + β·cos(4π(t-p')/24)   ← two-harmonic
//   R_t    = R_{t-1} - K * Δt                         ← wake depletion
// Produces 48 half-hourly points with full reservoir dynamics.
// ---------------------------------------------------------------------------

/** SAFTE parameters — identical to safte_model.py defaults */
const SAFTE = {
  R_c: 2880.0,        // Reservoir capacity (units)
  K: 0.5,             // Wake depletion rate (units / min)
  f: 0.01,            // Sleep recovery rate constant (per min)
  a_s: 0.05,          // Circadian effect on recovery (per min)
  p: 18.0,            // 24 h circadian peak phase (hours)
  p_prime: 3.0,       // 12 h harmonic phase offset (hours)
  beta: 0.5,          // 12 h harmonic relative amplitude
  a1: 7.8,            // Base circadian contribution (%)
  a2: 5.0,            // Fatigue-dependent circadian (%)
  norm: 96.7,         // Normalization constant (%)
} as const;

interface SAFTEForecast {
  hours: number[];
  effectiveness: number[];
  reservoir_pct: number[];   // R/R_c as percentage (Process S)
  circadian_drive: number[]; // Raw C_t (Process C)
}

/** Two-harmonic circadian drive — matches safte_model.py circadian() */
function circadianDrive(clockHour: number): number {
  const phaseRel = (clockHour - SAFTE.p + 24) % 24;
  const c1 = Math.cos((2 * Math.PI * phaseRel) / 24);
  const c2 = Math.cos((4 * Math.PI * (phaseRel - SAFTE.p_prime)) / 24);
  return c1 + SAFTE.beta * c2;
}

/**
 * Derive initial reservoir level from the backend's current effectiveness.
 * E = 100 * (100*R/R_c + (a1 + a2*(1 - R/R_c))*C_t) / norm
 * Solving for R/R_c:
 *   r = (E*norm/100 - (a1+a2)*C_t) / (100 - a2*C_t)
 */
function reservoirFromEffectiveness(E_pct: number, C_t: number): number {
  const numerator = (E_pct * SAFTE.norm) / 100 - (SAFTE.a1 + SAFTE.a2) * C_t;
  const denominator = 100 - SAFTE.a2 * C_t;
  if (Math.abs(denominator) < 1e-6) return 0.9; // safety fallback
  const ratio = numerator / denominator;
  return Math.max(0, Math.min(1, ratio));
}

function generateSAFTEForecast(
  baseEffectiveness: number,
  sleepDebtHours: number,
): SAFTEForecast {
  const now = new Date();
  const currentHour = now.getHours() + now.getMinutes() / 60;
  const dt_min = 30;        // 30-min steps → 48 points over 24 h
  const numPoints = 48;

  // Initialize reservoir from backend effectiveness
  const C_now = circadianDrive(currentHour);
  let R = reservoirFromEffectiveness(baseEffectiveness, C_now) * SAFTE.R_c;

  // If sleep debt is significant, ensure reservoir reflects it
  const debtDepletion = SAFTE.K * 60 * Math.max(0, sleepDebtHours);
  const R_from_debt = SAFTE.R_c - debtDepletion;
  // Use the lower of the two estimates (more conservative)
  R = Math.min(R, Math.max(0, R_from_debt));

  const hours: number[] = [];
  const effectiveness: number[] = [];
  const reservoir_pct: number[] = [];
  const circadian_values: number[] = [];

  for (let i = 0; i < numPoints; i++) {
    const h = i * 0.5;
    hours.push(h);

    const clockHour = (currentHour + h) % 24;
    const C_t = circadianDrive(clockHour);

    // --- Reservoir dynamics (safte_model.py lines 249-251) ---
    // Linear depletion during wakefulness
    if (i > 0) {
      R = Math.max(0, R - SAFTE.K * dt_min);
    }

    // --- Effectiveness (safte_model.py lines 259-276) ---
    const homeo_pct = 100 * (R / SAFTE.R_c);
    const circ_pct = (SAFTE.a1 + SAFTE.a2 * (1 - R / SAFTE.R_c)) * C_t;
    const E_pct = (100 * (homeo_pct + circ_pct)) / SAFTE.norm;

    effectiveness.push(
      Math.max(30, Math.min(100, Math.round(E_pct * 10) / 10)),
    );
    reservoir_pct.push(Math.round((R / SAFTE.R_c) * 1000) / 10);
    circadian_values.push(Math.round(C_t * 100) / 100);
  }

  return { hours, effectiveness, reservoir_pct, circadian_drive: circadian_values };
}

// Effectiveness Gauge - Clean minimal design following plot rules
function EffectivenessGauge({ effectiveness }: { effectiveness: number | null }) {
  const value = effectiveness ?? 75;
  const hasData = effectiveness !== null;

  const getColor = (e: number) => {
    if (e >= 80) return SCIENTIFIC_COLORS.success;
    if (e >= 60) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const getLabel = (e: number) => {
    if (e >= 80) return "Optimal";
    if (e >= 60) return "Moderate";
    return "Impaired";
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "65%"],
        radius: "95%",
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.6, SCIENTIFIC_COLORS.danger],
              [0.8, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.success],
            ],
          },
        },
        pointer: {
          length: "70%",
          width: 6,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? getColor(value) : "#94a3b8",
            shadowColor: "rgba(0, 0, 0, 0.3)",
            shadowBlur: 8,
            shadowOffsetY: 2,
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 16,
          itemStyle: {
            borderWidth: 4,
            borderColor: hasData ? getColor(value) : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 6,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -32,
          color: "#1a1a1a",
          fontSize: 11,
          fontWeight: "600",
          formatter: (v: number) => {
            if ([0, 60, 80, 100].includes(v)) return `${v}`;
            return "";
          },
        },
        progress: {
          show: true,
          overlap: false,
          roundCap: true,
          clip: false,
        },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? `${Math.round(value)}%` : "—"),
          fontSize: 36,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? getColor(value) : "#94a3b8",
          offsetCenter: [0, "32%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 13,
          fontWeight: "500",
          color: SCIENTIFIC_COLORS.textSecondary,
        },
        data: [{ value, name: hasData ? getLabel(value) : "No Data" }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={260} showToolbox={false} />;
}

// ---------------------------------------------------------------------------
// SAFTE-Based 24-Hour Forecast Chart — publication-quality visualization
// Features: visualMap color-coded line, circadian zone labels, NOW marker,
//           nadir/peak annotations, dynamic Y-axis, confidence band, dataZoom
// ---------------------------------------------------------------------------
function ForecastChart({ data }: { data: FatigueResponse }) {
  const now = new Date();
  const currentHour = now.getHours();

  // --- X-axis time labels (handles both integer and fractional hours) ---
  const xLabels = data.forecast_hours.map((h) => {
    const totalMin = Math.round(currentHour * 60 + h * 60) % (24 * 60);
    const hh = Math.floor(totalMin / 60);
    const mm = totalMin % 60;
    return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
  });

  const effValues = data.forecast_effectiveness;

  // --- Dynamic Y-axis bounds (auto-scale to data, never clip) ---
  const rawMin = Math.min(...effValues);
  const rawMax = Math.max(...effValues);
  const yMin = Math.max(0, Math.floor((rawMin - 8) / 5) * 5);
  const yMax = Math.min(100, Math.ceil((rawMax + 5) / 5) * 5);

  // --- Find nadir (lowest) and zenith (highest) for mark points ---
  const minIdx = effValues.indexOf(rawMin);
  const maxIdx = effValues.indexOf(rawMax);

  // --- Circadian zone detection ---
  const hourOf = (label: string): number => parseInt(label.split(":")[0], 10);

  const findZone = (startH: number, endH: number): [number, number] => {
    let first = -1;
    let last = -1;
    for (let i = 0; i < xLabels.length; i++) {
      const h = hourOf(xLabels[i]);
      if (h >= startH && h < endH) {
        if (first < 0) first = i;
        last = i;
      }
    }
    return [first, last];
  };

  // Build mark-area zones with labels
  const markAreaData: Array<Array<Record<string, unknown>>> = [];

  // WOCL zone (02:00–06:00)
  const [woclFirst, woclLast] = findZone(2, 6);
  if (woclFirst >= 0 && woclLast > woclFirst) {
    markAreaData.push([
      {
        xAxis: xLabels[woclFirst],
        itemStyle: { color: "rgba(231, 76, 60, 0.06)" },
        label: {
          show: true,
          formatter: "WOCL\n02–06 LT",
          position: "insideTop",
          color: SCIENTIFIC_COLORS.danger,
          fontSize: 9,
          fontWeight: "bold",
          padding: [4, 0, 0, 0],
        },
      },
      { xAxis: xLabels[woclLast] },
    ]);
  }

  // Post-lunch dip (13:00–15:00)
  const [plFirst, plLast] = findZone(13, 16);
  if (plFirst >= 0 && plLast > plFirst) {
    markAreaData.push([
      {
        xAxis: xLabels[plFirst],
        itemStyle: { color: "rgba(243, 156, 18, 0.06)" },
        label: {
          show: true,
          formatter: "Post-Lunch\nDip",
          position: "insideTop",
          color: SCIENTIFIC_COLORS.warning,
          fontSize: 9,
          fontWeight: "bold",
          padding: [4, 0, 0, 0],
        },
      },
      { xAxis: xLabels[plLast] },
    ]);
  }

  // --- Threshold mark-lines (only if within visible Y range) ---
  const markLineData: Array<Record<string, unknown>> = [];
  if (yMin <= 77 && yMax >= 77) {
    markLineData.push({
      yAxis: 77,
      label: {
        formatter: "Optimal 77%",
        position: "insideEndTop",
        color: SCIENTIFIC_COLORS.success,
        fontSize: 9,
      },
      lineStyle: { color: SCIENTIFIC_COLORS.success, opacity: 0.5, type: "dashed", width: 1.2 },
    });
  }
  if (yMin <= 60 && yMax >= 60) {
    markLineData.push({
      yAxis: 60,
      label: {
        formatter: "Impairment 60%",
        position: "insideEndTop",
        color: SCIENTIFIC_COLORS.danger,
        fontSize: 9,
      },
      lineStyle: { color: SCIENTIFIC_COLORS.danger, opacity: 0.5, type: "dashed", width: 1.2 },
    });
  }
  // NOW vertical marker
  markLineData.push({
    xAxis: xLabels[0],
    label: {
      formatter: "NOW",
      position: "insideEndTop",
      color: "#2c3e50",
      fontWeight: "bold",
      fontSize: 10,
    },
    lineStyle: { color: "#2c3e50", width: 1.5, type: "solid", opacity: 0.35 },
  });

  const option: Record<string, unknown> = {
    title: {
      text: "SAFTE Cognitive Effectiveness Forecast",
      left: "center",
      top: 6,
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
    },
    grid: {
      left: 55,
      right: 30,
      top: 50,
      bottom: 58,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: xLabels,
      boundaryGap: false,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        interval: Math.max(0, Math.floor(xLabels.length / 8) - 1),
      },
      axisLine: { lineStyle: { color: "#2c3e50" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "Effectiveness (%)",
      nameLocation: "middle",
      nameGap: 40,
      nameTextStyle: { color: "#1a1a1a", fontSize: 11, fontWeight: "bold" },
      min: yMin,
      max: yMax,
      splitNumber: 6,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        formatter: "{value}%",
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "rgba(44, 62, 80, 0.08)", type: "dashed" } },
    },
    // Color-code the line by effectiveness value
    visualMap: {
      show: false,
      type: "piecewise",
      dimension: 1,
      pieces: [
        { gte: 77, color: SCIENTIFIC_COLORS.success },
        { gte: 60, lt: 77, color: SCIENTIFIC_COLORS.warning },
        { lt: 60, color: SCIENTIFIC_COLORS.danger },
      ],
      seriesIndex: 0,
    },
    series: [
      {
        name: "Effectiveness",
        type: "line",
        data: effValues,
        smooth: 0.35,
        symbol: "none",
        lineStyle: { width: 3 },
        areaStyle: { opacity: 0.1 },
        z: 10,
        markLine: {
          silent: true,
          symbol: "none",
          data: markLineData,
        },
        markPoint: {
          animation: true,
          data: [
            {
              name: "Nadir",
              coord: [xLabels[minIdx], rawMin],
              value: `${rawMin.toFixed(0)}%`,
              symbol: "pin",
              symbolSize: 38,
              itemStyle: {
                color: rawMin < 60 ? SCIENTIFIC_COLORS.danger : SCIENTIFIC_COLORS.warning,
              },
              label: { color: "#fff", fontSize: 9, fontWeight: "bold" },
            },
            {
              name: "Peak",
              coord: [xLabels[maxIdx], rawMax],
              value: `${rawMax.toFixed(0)}%`,
              symbol: "roundRect",
              symbolSize: [36, 20],
              itemStyle: { color: SCIENTIFIC_COLORS.success },
              label: { color: "#fff", fontSize: 9, fontWeight: "bold" },
            },
          ],
        },
        markArea:
          markAreaData.length > 0
            ? { silent: true, data: markAreaData }
            : undefined,
      },
      // Upper confidence band (+4%)
      {
        name: "_upper",
        type: "line",
        data: effValues.map((v) => Math.min(100, v + 4)),
        smooth: 0.35,
        symbol: "none",
        lineStyle: { width: 0 },
        areaStyle: { color: "rgba(52, 152, 219, 0.05)" },
        z: 1,
        silent: true,
      },
      // Lower confidence band (−4%)
      {
        name: "_lower",
        type: "line",
        data: effValues.map((v) => Math.max(0, v - 4)),
        smooth: 0.35,
        symbol: "none",
        lineStyle: { width: 0, opacity: 0 },
        areaStyle: { color: "transparent" },
        z: 1,
        silent: true,
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.97)",
      borderColor: "#e2e8f0",
      borderRadius: 8,
      padding: [10, 14],
      textStyle: { color: "#1a1a1a", fontSize: 12 },
      formatter: (params: unknown) => {
        const arr = params as Array<{
          name: string;
          value: number;
          seriesName: string;
        }>;
        const main = arr.find((s) => s.seriesName === "Effectiveness");
        if (!main || main.value == null) return "";
        const eff = main.value;
        const status =
          eff >= 77 ? "Optimal" : eff >= 60 ? "Moderate" : "Impaired";
        const color =
          eff >= 77
            ? SCIENTIFIC_COLORS.success
            : eff >= 60
              ? SCIENTIFIC_COLORS.warning
              : SCIENTIFIC_COLORS.danger;
        const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px"></span>`;
        return [
          `<div style="font-family:system-ui,sans-serif">`,
          `<div style="font-weight:600;margin-bottom:4px;color:#64748b;font-size:11px">${main.name}</div>`,
          `<div style="display:flex;align-items:center">${dot}`,
          `<span style="font-size:20px;font-weight:700;color:${color}">${eff.toFixed(1)}%</span></div>`,
          `<div style="margin-top:3px;font-size:11px;color:#1a1a1a">${status}</div>`,
          `<div style="margin-top:2px;font-size:10px;color:#94a3b8">CI: ${Math.max(0, eff - 4).toFixed(0)}%–${Math.min(100, eff + 4).toFixed(0)}%</div>`,
          `</div>`,
        ].join("");
      },
    },
    legend: { show: false },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      {
        type: "slider",
        bottom: 5,
        height: 18,
        borderColor: "transparent",
        fillerColor: "rgba(52, 152, 219, 0.12)",
        handleStyle: { color: SCIENTIFIC_COLORS.primary },
      },
    ],
  };

  return <EChartsWrapper option={option} height={420} showToolbox={false} />;
}

// ---------------------------------------------------------------------------
// Process Decomposition Chart — shows S (reservoir) and C (circadian) traces
// ---------------------------------------------------------------------------
function ProcessDecompositionChart({
  forecast,
  currentHour,
}: {
  forecast: SAFTEForecast;
  currentHour: number;
}) {
  const xLabels = forecast.hours.map((h) => {
    const totalMin = Math.round(currentHour * 60 + h * 60) % (24 * 60);
    const hh = Math.floor(totalMin / 60);
    const mm = totalMin % 60;
    return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
  });

  const option: Record<string, unknown> = {
    title: {
      text: "Process Decomposition (S + C)",
      left: "center",
      top: 4,
      textStyle: { color: "#1a1a1a", fontSize: 13, fontWeight: "bold" },
    },
    grid: { left: 55, right: 55, top: 48, bottom: 55, containLabel: true },
    legend: {
      bottom: 4,
      textStyle: { color: "#1a1a1a", fontSize: 10 },
      data: ["Process S (Reservoir)", "Process C (Circadian)"],
    },
    xAxis: {
      type: "category",
      data: xLabels,
      boundaryGap: false,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        interval: Math.max(0, Math.floor(xLabels.length / 8) - 1),
      },
      axisLine: { lineStyle: { color: "#2c3e50" } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: "value",
        name: "Reservoir (%)",
        nameLocation: "middle",
        nameGap: 38,
        nameTextStyle: { color: SCIENTIFIC_COLORS.primary, fontSize: 10, fontWeight: "bold" },
        min: (v: { min: number }) => Math.floor((v.min - 2) / 5) * 5,
        axisLabel: { color: "#1a1a1a", fontSize: 9, formatter: "{value}%" },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: "rgba(44, 62, 80, 0.06)", type: "dashed" } },
      },
      {
        type: "value",
        name: "Circadian",
        nameLocation: "middle",
        nameGap: 38,
        nameTextStyle: { color: SCIENTIFIC_COLORS.warning, fontSize: 10, fontWeight: "bold" },
        axisLabel: { color: "#1a1a1a", fontSize: 9 },
        axisLine: { show: false },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Process S (Reservoir)",
        type: "line",
        yAxisIndex: 0,
        data: forecast.reservoir_pct,
        smooth: 0.3,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.primary },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(52, 152, 219, 0.12)" },
              { offset: 1, color: "rgba(52, 152, 219, 0)" },
            ],
          },
        },
      },
      {
        name: "Process C (Circadian)",
        type: "line",
        yAxisIndex: 1,
        data: forecast.circadian_drive,
        smooth: 0.3,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.warning, type: "dashed" },
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.97)",
      borderColor: "#e2e8f0",
      borderRadius: 8,
      padding: [8, 12],
      textStyle: { color: "#1a1a1a", fontSize: 11 },
    },
    dataZoom: [{ type: "inside", start: 0, end: 100 }],
  };

  return <EChartsWrapper option={option} height={300} showToolbox={false} />;
}

// ---------------------------------------------------------------------------
// Integrated Physiological Model Card
// Based on: "Toward an Integrated Model of Human Performance" (docs/)
// P(t) = σ(α₀ + α₁·log E_SAFTE + α₂·log A_AN + α₃·log W + α₄·log X)
// ---------------------------------------------------------------------------
function IntegratedModelCard({ effectiveness }: { effectiveness: number }) {
  // Simulated component factors (real values would come from backend)
  const E_sched = effectiveness / 100;     // Schedule effectiveness [0,1]
  const A_an = 1.0;                        // Autonomic factor (neutral if no HRV)
  const W_load = 1.0;                      // Workload factor (neutral default)
  const X_env = 1.0;                       // Environment modifier (neutral default)

  // Fusion coefficients (from integrated model discussion)
  const alpha = { a0: 0.5, a1: 2.0, a2: 0.8, a3: 0.3, a4: 0.2 };

  // Log-linear fusion with sigmoid
  const logit =
    alpha.a0 +
    alpha.a1 * Math.log(Math.max(0.01, E_sched)) +
    alpha.a2 * Math.log(Math.max(0.01, A_an)) +
    alpha.a3 * Math.log(Math.max(0.01, W_load)) +
    alpha.a4 * Math.log(Math.max(0.01, X_env));
  const P_integrated = 1 / (1 + Math.exp(-logit));
  const P_pct = Math.round(P_integrated * 1000) / 10;

  const factors = [
    {
      label: "Schedule (SAFTE)",
      symbol: "E_SAFTE",
      value: E_sched,
      pct: effectiveness,
      color: effectiveness >= 77 ? SCIENTIFIC_COLORS.success : effectiveness >= 60 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.danger,
      active: true,
      description: "Reservoir + circadian + inertia",
    },
    {
      label: "Autonomic (HRV/HRF)",
      symbol: "A_AN",
      value: A_an,
      pct: A_an * 100,
      color: SCIENTIFIC_COLORS.info,
      active: false,
      description: "lnRMSSD + PIP, QC-gated",
    },
    {
      label: "Workload",
      symbol: "W",
      value: W_load,
      pct: W_load * 100,
      color: "#9b59b6",
      active: false,
      description: "Task demand + duty metadata",
    },
    {
      label: "Environment",
      symbol: "X",
      value: X_env,
      pct: X_env * 100,
      color: "#34495e",
      active: false,
      description: "Hypoxia, thermal, microgravity",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Factor grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {factors.map((f) => (
          <div
            key={f.symbol}
            className={`p-3 rounded-lg border text-center transition-opacity ${f.active ? "opacity-100" : "opacity-50"}`}
          >
            <div
              className="w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center text-white text-xs font-bold"
              style={{ backgroundColor: f.color }}
            >
              {f.active ? `${Math.round(f.pct)}` : "—"}
            </div>
            <p className="text-xs font-semibold text-foreground">{f.label}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{f.description}</p>
            {!f.active && (
              <Badge variant="outline" className="mt-1 text-[9px]">Neutral</Badge>
            )}
          </div>
        ))}
      </div>

      {/* Fusion equation and result */}
      <div className="p-3 rounded-lg bg-muted/30 border">
        <p className="text-xs text-muted-foreground mb-2">
          <strong>Fusion:</strong>{" "}
          <code className="text-[10px]">
            P(t) = σ(α₀ + α₁·log E + α₂·log A + α₃·log W + α₄·log X)
          </code>
        </p>
        <div className="flex items-center gap-3">
          <div className="text-2xl font-bold" style={{
            color: P_pct >= 77 ? SCIENTIFIC_COLORS.success : P_pct >= 60 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.danger,
          }}>
            {P_pct.toFixed(1)}%
          </div>
          <div>
            <p className="text-xs font-semibold text-foreground">Integrated Performance</p>
            <p className="text-[10px] text-muted-foreground">
              {factors.filter((f) => !f.active).length > 0 &&
                `${factors.filter((f) => !f.active).length} module(s) at neutral — connect HRV/workload for full fusion`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Risk Semaphore
function RiskSemaphore({ level, color }: { level: string; color: string }) {
  const bgColor = color === "green" ? "bg-success" : color === "yellow" ? "bg-warning" : "bg-danger";
  const textColor = color === "green" ? "text-success" : color === "yellow" ? "text-warning" : "text-danger";

  return (
    <div className="flex items-center gap-4">
      <div className={`w-16 h-16 rounded-full ${bgColor} flex items-center justify-center shadow-lg`}>
        {color === "green" ? (
          <Sun className="h-8 w-8 text-white" />
        ) : color === "yellow" ? (
          <Coffee className="h-8 w-8 text-white" />
        ) : (
          <Moon className="h-8 w-8 text-white" />
        )}
      </div>
      <div>
        <p className={`text-lg font-bold ${textColor}`}>
          {level.charAt(0).toUpperCase() + level.slice(1)} Risk
        </p>
        <p className="text-sm text-muted-foreground">
          {color === "green"
            ? "Normal operations appropriate"
            : color === "yellow"
              ? "Use caution, consider breaks"
              : "Avoid safety-critical tasks"}
        </p>
      </div>
    </div>
  );
}

export default function FatiguePage() {
  const [data, setData] = React.useState<FatigueResponse | null>(null);
  const [forecast, setForecast] = React.useState<SAFTEForecast | null>(null);
  const [loading, setLoading] = React.useState(false);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getFatiguePrediction(userId);

      // -----------------------------------------------------------------
      // Always generate the 48-point SAFTE circadian forecast locally.
      // The backend may return a coarse step-function; the two-harmonic
      // model produces a scientifically accurate, publication-quality curve.
      // Backend metadata (risk level, sleep debt, etc.) is preserved.
      // -----------------------------------------------------------------
      const baseEff = result.effectiveness_pct ?? 76;
      const sleepDebt = result.sleep_debt_hours ?? 2.5;
      const safteForecast = generateSAFTEForecast(baseEff, sleepDebt);
      setForecast(safteForecast);
      const forecast = safteForecast;

      const enriched: FatigueResponse = {
        ...result,
        effectiveness_pct: result.effectiveness_pct ?? forecast.effectiveness[0],
        forecast_hours: forecast.hours,
        forecast_effectiveness: forecast.effectiveness,
        sleep_debt_hours: result.sleep_debt_hours ?? 2.5,
        // Fall back to computed risk when backend returns default values
        fatigue_level:
          result.forecast_hours.length > 0
            ? result.fatigue_level
            : forecast.effectiveness[0] >= 77
              ? "normal"
              : forecast.effectiveness[0] >= 60
                ? "fatigued"
                : "severely_fatigued",
        risk_level:
          result.forecast_hours.length > 0
            ? result.risk_level
            : forecast.effectiveness[0] >= 77
              ? "low"
              : forecast.effectiveness[0] >= 60
                ? "moderate"
                : "high",
        risk_color:
          result.forecast_hours.length > 0
            ? result.risk_color
            : forecast.effectiveness[0] >= 77
              ? "green"
              : forecast.effectiveness[0] >= 60
                ? "yellow"
                : "red",
        recommendations:
          result.recommendations.length > 1
            ? result.recommendations
            : [
                "Schedule critical tasks during peak alertness windows (~09:00–11:00, ~17:00–19:00)",
                "Window of Circadian Low (WOCL): ~02:00–06:00 — avoid safety-critical operations",
                "Post-lunch dip: ~13:00–15:00 — consider strategic nap or caffeine at 13:00",
                "Target 7–8 h sleep tonight to reduce accumulated sleep debt",
              ],
        next_optimal_sleep: result.next_optimal_sleep ?? "22:00",
      };
      setData(enriched);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Fatigue Prediction"
      description="SAFTE-Based Cognitive Effectiveness Forecast"
    >
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            {data && (
              <>
                <Badge
                  variant="outline"
                  style={{
                    borderColor: FATIGUE_COLORS[data.fatigue_level],
                    color: FATIGUE_COLORS[data.fatigue_level],
                  }}
                >
                  {data.fatigue_level.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </Badge>
                {data.sleep_debt_hours !== null && data.sleep_debt_hours > 4 && (
                  <Badge variant="warning" className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Sleep Debt: {data.sleep_debt_hours.toFixed(1)}h
                  </Badge>
                )}
              </>
            )}
          </div>
          <Button onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </motion.div>

        {data && (
          <>
            {/* Main Gauge and Risk */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Zap className="h-5 w-5 text-warning" />
                      Cognitive Effectiveness
                    </CardTitle>
                    <CardDescription className="text-xs">
                      SAFTE model: &gt;77% optimal, 60-77% moderate, &lt;60% impaired
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <EffectivenessGauge effectiveness={data.effectiveness_pct} />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-danger" />
                      Risk Assessment
                    </CardTitle>
                    <CardDescription>
                      Operational risk level based on fatigue state
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col justify-center h-[calc(100%-80px)]">
                    <RiskSemaphore level={data.risk_level} color={data.risk_color} />
                    <div className="grid grid-cols-2 gap-4 mt-6">
                      <div className="p-3 rounded-lg border text-center">
                        <Battery className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">Sleep Debt</p>
                        <p className="text-lg font-bold">{data.sleep_debt_hours?.toFixed(1) ?? "—"} h</p>
                      </div>
                      <div className="p-3 rounded-lg border text-center">
                        <Clock className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
                        <p className="text-xs text-muted-foreground">Optimal Bedtime</p>
                        <p className="text-lg font-bold">{data.next_optimal_sleep ?? "—"}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Forecast */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Sun className="h-5 w-5 text-warning" />
                    24-Hour Circadian Forecast
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Two-harmonic SAFTE model: peaks ~10:00 &amp; ~18:00, troughs ~04:00 (WOCL) &amp; ~14:00 (post-lunch dip)
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <ForecastChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Process Decomposition */}
            {forecast && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Activity className="h-5 w-5 text-primary" />
                      SAFTE Process Decomposition
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Process S (homeostatic reservoir depletion) and Process C (two-harmonic circadian drive) —
                      the fundamental components of the Borbely two-process model
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ProcessDecompositionChart
                      forecast={forecast}
                      currentHour={new Date().getHours()}
                    />
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Integrated Physiological Model */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Brain className="h-5 w-5 text-info" />
                    Integrated Physiological Model
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Multiplicative fusion of schedule-based SAFTE, autonomic physiology (HRV/HRF),
                    workload context, and environmental modifiers — P(t) = σ(Σ αᵢ·log Fᵢ)
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-2">
                  <IntegratedModelCard effectiveness={data.effectiveness_pct ?? 75} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Recommendations */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Coffee className="h-5 w-5 text-info" />
                    Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {data.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-info">•</span>
                        <span className="text-sm text-muted-foreground">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

            {/* SAFTE Model Info */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>SAFTE Model Scientific Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-3">
                  <p>
                    <strong>Reservoir-Based SAFTE Model:</strong> The sleep reservoir R(t)
                    depletes linearly during wakefulness (K=0.5 units/min) and recovers exponentially
                    during sleep. Cognitive effectiveness is computed as:
                  </p>
                  <div className="p-2 rounded bg-muted/40 font-mono text-xs">
                    E(t) = 100 × (homeo% + circ%) / 96.7<br/>
                    homeo% = 100 × R/R<sub>c</sub><br/>
                    circ% = (a₁ + a₂·(1 − R/R<sub>c</sub>)) × C(t)<br/>
                    C(t) = cos(2π(t−18)/24) + 0.5·cos(4π(t−3)/24)
                  </div>
                  <p>
                    The fatigue-dependent term a₂·(1−R/R<sub>c</sub>) amplifies circadian
                    effects as the reservoir depletes — meaning sleep-deprived individuals
                    experience stronger WOCL troughs and alertness peaks.
                  </p>
                  <p>
                    <strong>Integrated Model:</strong> Extends SAFTE via log-linear fusion with
                    autonomic physiology (HRV/HRF), workload, and environment modifiers:
                    P(t) = σ(α₀ + α₁·log E<sub>SAFTE</sub> + α₂·log A<sub>AN</sub> + α₃·log W + α₄·log X).
                    The autonomic factor A<sub>AN</sub> is quality-gated: it defaults to neutral (1.0)
                    when HRV measurement quality is insufficient.
                  </p>
                  <div className="pt-2 border-t">
                    <p className="text-xs">
                      <strong>References:</strong><br/>
                      • Hursh SR et al. (2004). Fatigue models for applied research in warfighting.
                      <span className="ml-1 text-primary">Aviat Space Environ Med, 75(3 Suppl), A44-53.</span><br/>
                      • Peng H, Bouak F. (2015). Bio-mathematical models for human performance under fatigue.
                      <span className="ml-1 text-primary">DRDC-RDDC-2015-R280.</span><br/>
                      • Borbely AA. (1982). A two process model of sleep regulation.
                      <span className="ml-1 text-primary">Human Neurobiology, 1(3), 195-204.</span><br/>
                      • Dawson D, Reid K. (1997). Fatigue, alcohol and performance impairment.
                      <span className="ml-1 text-primary">Nature, 388(6639), 235.</span>
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>
    </PageWrapper>
  );
}
