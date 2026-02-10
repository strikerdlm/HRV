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

// SAFTE model imported from shared module (used by both Research and Operational tabs)
import {
  generateSAFTEForecast,
  SAFTE,
  type SAFTEForecast,
} from "@/lib/safte-model";

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
// FAST-Style Multi-Day Forecast Chart  (Publication Quality — Q1 Journal)
// Features: day/night shading, sleep bands, WOCL zones, color-coded line,
//           threshold annotations with BAC equivalence, confidence band,
//           nadir/peak markers, dynamic Y-axis, dataZoom, multi-day x-axis.
// Inspired by: SAFTE-FAST (Hursh / IBR) graphical display conventions.
// ---------------------------------------------------------------------------
function ForecastChart({
  forecast,
  predictionDays,
}: {
  forecast: SAFTEForecast;
  predictionDays: number;
}) {
  const currentHour = new Date().getHours();

  // --- X-axis labels: "Day N HH:MM" for multi-day, "HH:MM" for 1-day ---
  const xLabels = forecast.hours.map((h) => {
    const totalMin = Math.round(currentHour * 60 + h * 60) % (24 * 60);
    const hh = Math.floor(totalMin / 60);
    const mm = totalMin % 60;
    const dayNum = Math.floor(h / 24) + 1;
    const timeStr = `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
    return predictionDays > 1 ? `D${dayNum} ${timeStr}` : timeStr;
  });

  const effValues = forecast.effectiveness;
  const rawMin = Math.min(...effValues);
  const rawMax = Math.max(...effValues);
  const yMin = Math.max(0, Math.floor((rawMin - 8) / 5) * 5);
  const yMax = Math.min(100, Math.ceil((rawMax + 5) / 5) * 5);
  const minIdx = effValues.indexOf(rawMin);
  const maxIdx = effValues.indexOf(rawMax);

  // --- Night-time (sleep) bands as mark areas ---
  const markAreaData: Array<Array<Record<string, unknown>>> = [];

  // Find contiguous sleep blocks from the forecast
  let sleepStart = -1;
  for (let i = 0; i < forecast.isAsleep.length; i++) {
    if (forecast.isAsleep[i] && sleepStart < 0) {
      sleepStart = i;
    } else if (!forecast.isAsleep[i] && sleepStart >= 0) {
      markAreaData.push([
        {
          xAxis: xLabels[sleepStart],
          itemStyle: { color: "rgba(44, 62, 80, 0.06)" },
          label: sleepStart === (forecast.isAsleep.indexOf(true))
            ? { show: true, formatter: "Sleep", position: "insideTop", color: "#64748b", fontSize: 8 }
            : { show: false },
        },
        { xAxis: xLabels[i - 1] },
      ]);
      sleepStart = -1;
    }
  }
  if (sleepStart >= 0) {
    markAreaData.push([
      { xAxis: xLabels[sleepStart], itemStyle: { color: "rgba(44, 62, 80, 0.06)" } },
      { xAxis: xLabels[xLabels.length - 1] },
    ]);
  }

  // --- Threshold mark-lines ---
  const markLineData: Array<Record<string, unknown>> = [];
  if (yMin <= 90 && yMax >= 90) {
    markLineData.push({
      yAxis: 90, label: { formatter: "Normal Sleep Goal 90%", position: "insideEndTop", color: SCIENTIFIC_COLORS.success, fontSize: 8 },
      lineStyle: { color: SCIENTIFIC_COLORS.success, opacity: 0.35, type: "dotted", width: 1 },
    });
  }
  if (yMin <= 77 && yMax >= 77) {
    markLineData.push({
      yAxis: 77, label: { formatter: "Elevated Risk 77% (2.5× accident cost)", position: "insideEndTop", color: SCIENTIFIC_COLORS.warning, fontSize: 8 },
      lineStyle: { color: SCIENTIFIC_COLORS.warning, opacity: 0.5, type: "dashed", width: 1.2 },
    });
  }
  if (yMin <= 60 && yMax >= 60) {
    markLineData.push({
      yAxis: 60, label: { formatter: "Impairment 60% (≈ 0.08% BAC)", position: "insideEndTop", color: SCIENTIFIC_COLORS.danger, fontSize: 8 },
      lineStyle: { color: SCIENTIFIC_COLORS.danger, opacity: 0.5, type: "dashed", width: 1.2 },
    });
  }
  if (yMin <= 50 && yMax >= 50) {
    markLineData.push({
      yAxis: 50, label: { formatter: "Critical 50% (+65% accident risk)", position: "insideEndTop", color: "#7f1d1d", fontSize: 8 },
      lineStyle: { color: "#7f1d1d", opacity: 0.5, type: "dashed", width: 1 },
    });
  }
  // NOW marker
  markLineData.push({
    xAxis: xLabels[0],
    label: { formatter: "NOW", position: "insideEndTop", color: "#2c3e50", fontWeight: "bold", fontSize: 9 },
    lineStyle: { color: "#2c3e50", width: 1.5, type: "solid", opacity: 0.3 },
  });

  // Adaptive label interval based on data density
  const labelInterval = predictionDays <= 1
    ? Math.max(0, Math.floor(xLabels.length / 8) - 1)
    : predictionDays <= 3
      ? Math.max(0, Math.floor(xLabels.length / 12) - 1)
      : Math.max(0, Math.floor(xLabels.length / 14) - 1);

  const option: Record<string, unknown> = {
    title: {
      text: `SAFTE Cognitive Effectiveness — ${predictionDays}-Day Forecast`,
      left: "center",
      top: 6,
      textStyle: { color: "#1a1a1a", fontSize: 13, fontWeight: "bold" },
    },
    grid: { left: 55, right: 30, top: 48, bottom: 58, containLabel: true },
    xAxis: {
      type: "category",
      data: xLabels,
      boundaryGap: false,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: predictionDays > 3 ? 8 : 9,
        interval: labelInterval,
        rotate: predictionDays > 3 ? 30 : 0,
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
      axisLabel: { color: "#1a1a1a", fontSize: 10, formatter: "{value}%" },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "rgba(44, 62, 80, 0.06)", type: "dashed" } },
    },
    visualMap: {
      show: false,
      type: "piecewise",
      dimension: 1,
      pieces: [
        { gte: 90, color: SCIENTIFIC_COLORS.success },
        { gte: 77, lt: 90, color: "#2ecc71" },
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
        smooth: 0.3,
        symbol: "none",
        lineStyle: { width: 2.5 },
        areaStyle: { opacity: 0.08 },
        z: 10,
        markLine: { silent: true, symbol: "none", data: markLineData },
        markPoint: {
          animation: true,
          data: [
            {
              name: "Nadir",
              coord: [xLabels[minIdx], rawMin],
              value: `${rawMin.toFixed(0)}%`,
              symbol: "pin",
              symbolSize: 34,
              itemStyle: { color: rawMin < 60 ? SCIENTIFIC_COLORS.danger : SCIENTIFIC_COLORS.warning },
              label: { color: "#fff", fontSize: 8, fontWeight: "bold" },
            },
            {
              name: "Peak",
              coord: [xLabels[maxIdx], rawMax],
              value: `${rawMax.toFixed(0)}%`,
              symbol: "roundRect",
              symbolSize: [32, 18],
              itemStyle: { color: SCIENTIFIC_COLORS.success },
              label: { color: "#fff", fontSize: 8, fontWeight: "bold" },
            },
          ],
        },
        markArea: markAreaData.length > 0 ? { silent: true, data: markAreaData } : undefined,
      },
      // ±4% confidence band
      {
        name: "_ci_upper", type: "line",
        data: effValues.map((v) => Math.min(100, v + 4)),
        smooth: 0.3, symbol: "none", lineStyle: { width: 0 },
        areaStyle: { color: "rgba(52,152,219,0.04)" }, z: 1, silent: true,
      },
      {
        name: "_ci_lower", type: "line",
        data: effValues.map((v) => Math.max(0, v - 4)),
        smooth: 0.3, symbol: "none", lineStyle: { width: 0, opacity: 0 },
        areaStyle: { color: "transparent" }, z: 1, silent: true,
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
        const arr = params as Array<{ name: string; value: number; seriesName: string; dataIndex: number }>;
        const main = arr.find((s) => s.seriesName === "Effectiveness");
        if (!main || main.value == null) return "";
        const eff = main.value;
        const sleeping = forecast.isAsleep[main.dataIndex];
        const status = eff >= 90 ? "Optimal" : eff >= 77 ? "Good" : eff >= 60 ? "Moderate" : eff >= 50 ? "Impaired" : "Critical";
        const color = eff >= 77 ? SCIENTIFIC_COLORS.success : eff >= 60 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.danger;
        const bac = eff < 77 ? `<div style="margin-top:2px;font-size:10px;color:#94a3b8">≈ ${((100 - eff) * 0.08 / 40).toFixed(3)}% BAC equivalent</div>` : "";
        const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:6px"></span>`;
        return [
          `<div style="font-family:system-ui,sans-serif">`,
          `<div style="font-weight:600;margin-bottom:4px;color:#64748b;font-size:11px">${main.name}${sleeping ? " (Sleep)" : ""}</div>`,
          `<div style="display:flex;align-items:center">${dot}`,
          `<span style="font-size:18px;font-weight:700;color:${color}">${eff.toFixed(1)}%</span></div>`,
          `<div style="margin-top:2px;font-size:11px;color:#1a1a1a">${status}</div>`,
          bac,
          `</div>`,
        ].join("");
      },
    },
    legend: { show: false },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      {
        type: "slider", bottom: 5, height: 18,
        borderColor: "transparent",
        fillerColor: "rgba(52, 152, 219, 0.12)",
        handleStyle: { color: SCIENTIFIC_COLORS.primary },
      },
    ],
  };

  const chartHeight = predictionDays <= 1 ? 420 : predictionDays <= 3 ? 460 : 500;
  return <EChartsWrapper option={option} height={chartHeight} showToolbox={false} />;
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

const DAY_OPTIONS = [1, 2, 3, 5, 7] as const;

export default function FatiguePage() {
  const [data, setData] = React.useState<FatigueResponse | null>(null);
  const [forecast, setForecast] = React.useState<SAFTEForecast | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [predictionDays, setPredictionDays] = React.useState<number>(1);

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
      const safteForecast = generateSAFTEForecast(baseEff, sleepDebt, predictionDays);
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
  }, [userId, predictionDays]);

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

            {/* Forecast with day selector */}
            {forecast && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <Sun className="h-5 w-5 text-warning" />
                          SAFTE Circadian Forecast
                        </CardTitle>
                        <CardDescription className="text-xs mt-1">
                          Reservoir-based SAFTE model (Hursh et al. 2004) — sleep recovery, circadian modulation, BAC equivalence thresholds
                        </CardDescription>
                      </div>
                      {/* Day Selector */}
                      <div className="flex items-center gap-1 border rounded-lg p-0.5">
                        {DAY_OPTIONS.map((d) => (
                          <button
                            key={d}
                            onClick={() => setPredictionDays(d)}
                            className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                              predictionDays === d
                                ? "bg-primary text-primary-foreground shadow-sm"
                                : "text-muted-foreground hover:text-foreground hover:bg-muted"
                            }`}
                          >
                            {d}d
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ForecastChart forecast={forecast} predictionDays={predictionDays} />
                  </CardContent>
                </Card>
              </motion.div>
            )}

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
