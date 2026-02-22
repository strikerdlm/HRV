// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Sun,
  Zap,
  Wind,
  AlertTriangle,
  AlertCircle,
  Clock,
  RefreshCw,
  Activity,
  Radio,
  Compass,
  TrendingUp,
  Download,
  BarChart3,
  Waves,
  Radiation,
  Target,
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
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import {
  getCurrentSpaceWeather,
  refreshSpaceWeather,
  getNOAADatasets,
} from "@/lib/research-api";
import type {
  SpaceWeatherSnapshot,
  ImpactPrediction,
  ImpactSeverity,
  NOAADataResponse,
} from "@/types/research";
import { SEVERITY_COLORS, CATEGORY_ICONS } from "@/types/research";
import { formatDateTime } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Publication-Quality Color Palette (Nature Research Guidelines)
// ---------------------------------------------------------------------------

const PUBLICATION_COLORS = {
  // Primary data series - colorblind-friendly
  kp: "#2563eb", // Blue - Kp index
  dst: "#dc2626", // Red - Dst index (negative during storms)
  solarWind: "#059669", // Green - Solar wind
  f107: "#d97706", // Amber - F10.7 flux
  xray: "#7c3aed", // Purple - X-ray flux
  proton: "#db2777", // Pink - Proton flux
  bz: "#0891b2", // Cyan - IMF Bz

  // Status colors
  quiet: "#22c55e",
  unsettled: "#84cc16",
  active: "#eab308",
  minor: "#f97316",
  major: "#ef4444",
  severe: "#dc2626",
  extreme: "#991b1b",

  // Reference zones
  normalZone: "rgba(34, 197, 94, 0.1)",
  warningZone: "rgba(234, 179, 8, 0.1)",
  dangerZone: "rgba(239, 68, 68, 0.1)",

  // Text and grid
  text: "#1a1a1a",
  subtext: "#64748b",
  grid: "rgba(44, 62, 80, 0.1)",
  axis: "#2c3e50",
};

// Severity badge colors
const severityVariants: Record<
  ImpactSeverity,
  "success" | "info" | "warning" | "destructive" | "secondary"
> = {
  quiet: "success",
  minor: "info",
  moderate: "warning",
  strong: "warning",
  severe: "destructive",
  extreme: "destructive",
};

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

function getKpLevel(kp: number): { label: string; color: string } {
  if (kp < 4) return { label: "Quiet", color: PUBLICATION_COLORS.quiet };
  if (kp < 5) return { label: "Unsettled", color: PUBLICATION_COLORS.unsettled };
  if (kp < 6) return { label: "Active", color: PUBLICATION_COLORS.active };
  if (kp < 7) return { label: "Minor Storm", color: PUBLICATION_COLORS.minor };
  if (kp < 8) return { label: "Major Storm", color: PUBLICATION_COLORS.major };
  if (kp < 9) return { label: "Severe Storm", color: PUBLICATION_COLORS.severe };
  return { label: "Extreme Storm", color: PUBLICATION_COLORS.extreme };
}

function getDstLevel(dst: number): { label: string; color: string } {
  if (dst > -20) return { label: "Quiet", color: PUBLICATION_COLORS.quiet };
  if (dst > -50) return { label: "Weak Storm", color: PUBLICATION_COLORS.unsettled };
  if (dst > -100) return { label: "Moderate Storm", color: PUBLICATION_COLORS.active };
  if (dst > -200) return { label: "Strong Storm", color: PUBLICATION_COLORS.minor };
  if (dst > -350) return { label: "Severe Storm", color: PUBLICATION_COLORS.major };
  return { label: "Extreme Storm", color: PUBLICATION_COLORS.extreme };
}

// ---------------------------------------------------------------------------
// Modern Minimal Gauge Components - Clean & Professional
// ---------------------------------------------------------------------------

function KpGauge({ value }: { value: number | null }) {
  const displayValue = value ?? 0;
  const hasData = value !== null;
  const level = getKpLevel(displayValue);

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "70%"],
        radius: "100%",
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 9,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.33, PUBLICATION_COLORS.quiet],
              [0.44, PUBLICATION_COLORS.unsettled],
              [0.55, PUBLICATION_COLORS.active],
              [0.66, PUBLICATION_COLORS.minor],
              [0.77, PUBLICATION_COLORS.major],
              [0.88, PUBLICATION_COLORS.severe],
              [1, PUBLICATION_COLORS.extreme],
            ],
          },
        },
        pointer: {
          length: "70%",
          width: 6,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? level.color : "#94a3b8",
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
            borderColor: hasData ? level.color : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 6,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -35,
          color: PUBLICATION_COLORS.text,
          fontSize: 11,
          fontWeight: "600",
          formatter: (value: number) => {
            // Only show key values: 0, 3, 5, 7, 9
            if ([0, 3, 5, 7, 9].includes(value)) return value.toString();
            return "";
          },
        },
        progress: {
          show: true,
          overlap: false,
          roundCap: true,
          clip: false,
          itemStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: PUBLICATION_COLORS.quiet },
                { offset: 0.5, color: hasData ? level.color : "#94a3b8" },
                { offset: 1, color: hasData ? level.color : "#94a3b8" },
              ],
            },
          },
        },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? displayValue.toFixed(1) : "—"),
          fontSize: 28,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? level.color : "#94a3b8",
          offsetCenter: [0, "35%"],
        },
        data: [{ value: displayValue }],
      },
    ],
  };

  return (
    <Card className="h-full bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
      <CardHeader className="pb-0 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30">
            <Compass className="h-4 w-4 text-blue-600" />
          </div>
          Kp Index
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-2">
        <EChartsWrapper option={option} height={160} showToolbox={false} />
        <div className="text-center -mt-1">
          <Badge
            className="text-xs font-medium shadow-sm"
            style={{ backgroundColor: hasData ? level.color : "#94a3b8", color: "#fff" }}
          >
            {hasData ? level.label : "No Data"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function DstGauge({ value }: { value: number | null }) {
  const displayValue = value ?? 0;
  const hasData = value !== null;
  const level = getDstLevel(displayValue);

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "70%"],
        radius: "100%",
        startAngle: 180,
        endAngle: 0,
        min: -300,
        max: 50,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.14, PUBLICATION_COLORS.extreme],
              [0.43, PUBLICATION_COLORS.major],
              [0.71, PUBLICATION_COLORS.active],
              [0.86, PUBLICATION_COLORS.unsettled],
              [1, PUBLICATION_COLORS.quiet],
            ],
          },
        },
        pointer: {
          length: "75%",
          width: 10,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? level.color : "#94a3b8",
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
            borderColor: hasData ? level.color : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 6,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -35,
          color: PUBLICATION_COLORS.text,
          fontSize: 10,
          fontWeight: "600",
          formatter: (value: number) => {
            // Only show key values
            if ([-300, -100, 0, 50].includes(value)) return value.toString();
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
          formatter: () => (hasData ? `${displayValue.toFixed(0)}` : "—"),
          fontSize: 26,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? level.color : "#94a3b8",
          offsetCenter: [0, "35%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 11,
          fontWeight: "500",
          color: PUBLICATION_COLORS.subtext,
        },
        data: [{ value: displayValue, name: "nT" }],
      },
    ],
  };

  return (
    <Card className="h-full bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
      <CardHeader className="pb-0 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <div className="p-1.5 rounded-lg bg-red-100 dark:bg-red-900/30">
            <Waves className="h-4 w-4 text-red-600" />
          </div>
          Dst Index
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-2">
        <EChartsWrapper option={option} height={160} showToolbox={false} />
        <div className="text-center -mt-1">
          <Badge
            className="text-xs font-medium shadow-sm"
            style={{ backgroundColor: hasData ? level.color : "#94a3b8", color: "#fff" }}
          >
            {hasData ? level.label : "No Data"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function SolarWindGauge({
  speed,
  density,
}: {
  speed: number | null;
  density: number | null;
}) {
  const speedValue = speed ?? 350;
  const hasData = speed !== null;

  const getWindLevel = (v: number) => {
    if (v < 400) return { label: "Slow", color: PUBLICATION_COLORS.quiet };
    if (v < 500) return { label: "Nominal", color: PUBLICATION_COLORS.unsettled };
    if (v < 600) return { label: "Enhanced", color: PUBLICATION_COLORS.active };
    if (v < 700) return { label: "High", color: PUBLICATION_COLORS.minor };
    return { label: "Very High", color: PUBLICATION_COLORS.major };
  };

  const level = getWindLevel(speedValue);

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "70%"],
        radius: "100%",
        startAngle: 180,
        endAngle: 0,
        min: 200,
        max: 800,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.33, PUBLICATION_COLORS.quiet],
              [0.50, PUBLICATION_COLORS.unsettled],
              [0.67, PUBLICATION_COLORS.active],
              [0.83, PUBLICATION_COLORS.minor],
              [1, PUBLICATION_COLORS.major],
            ],
          },
        },
        pointer: {
          length: "75%",
          width: 10,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? level.color : "#94a3b8",
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
            borderColor: hasData ? level.color : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 6,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -35,
          color: PUBLICATION_COLORS.text,
          fontSize: 10,
          fontWeight: "600",
          formatter: (value: number) => {
            // Only show key values
            if ([200, 400, 600, 800].includes(value)) return value.toString();
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
          formatter: () => (hasData ? speedValue.toFixed(0) : "—"),
          fontSize: 26,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? level.color : "#94a3b8",
          offsetCenter: [0, "35%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 11,
          fontWeight: "500",
          color: PUBLICATION_COLORS.subtext,
        },
        data: [{ value: speedValue, name: "km/s" }],
      },
    ],
  };

  return (
    <Card className="h-full bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
      <CardHeader className="pb-0 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <div className="p-1.5 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
            <Wind className="h-4 w-4 text-emerald-600" />
          </div>
          Solar Wind
        </CardTitle>
        <CardDescription className="text-xs mt-0.5">
          Density: {density?.toFixed(1) ?? "—"} p/cm³
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0 pb-2">
        <EChartsWrapper option={option} height={160} showToolbox={false} />
        <div className="text-center -mt-1">
          <Badge
            className="text-xs font-medium shadow-sm"
            style={{ backgroundColor: hasData ? level.color : "#94a3b8", color: "#fff" }}
          >
            {hasData ? level.label : "No Data"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

function F107Gauge({ value }: { value: number | null }) {
  const displayValue = value ?? 100;
  const hasData = value !== null;

  const getFluxLevel = (v: number) => {
    if (v < 80) return { label: "Very Low", color: PUBLICATION_COLORS.quiet };
    if (v < 120) return { label: "Low", color: PUBLICATION_COLORS.unsettled };
    if (v < 150) return { label: "Moderate", color: PUBLICATION_COLORS.active };
    if (v < 200) return { label: "High", color: PUBLICATION_COLORS.minor };
    return { label: "Very High", color: PUBLICATION_COLORS.major };
  };

  const level = getFluxLevel(displayValue);

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "70%"],
        radius: "100%",
        startAngle: 180,
        endAngle: 0,
        min: 60,
        max: 260,
        axisLine: {
          lineStyle: {
            width: 18,
            color: [
              [0.10, PUBLICATION_COLORS.quiet],
              [0.30, PUBLICATION_COLORS.unsettled],
              [0.45, PUBLICATION_COLORS.active],
              [0.70, PUBLICATION_COLORS.minor],
              [1, PUBLICATION_COLORS.major],
            ],
          },
        },
        pointer: {
          length: "75%",
          width: 10,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? level.color : "#94a3b8",
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
            borderColor: hasData ? level.color : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 6,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -35,
          color: PUBLICATION_COLORS.text,
          fontSize: 10,
          fontWeight: "600",
          formatter: (value: number) => {
            // Only show key values
            if ([60, 100, 150, 200, 260].includes(value)) return value.toString();
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
          formatter: () => (hasData ? displayValue.toFixed(0) : "—"),
          fontSize: 26,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? level.color : "#94a3b8",
          offsetCenter: [0, "35%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 11,
          fontWeight: "500",
          color: PUBLICATION_COLORS.subtext,
        },
        data: [{ value: displayValue, name: "SFU" }],
      },
    ],
  };

  return (
    <Card className="h-full bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
      <CardHeader className="pb-0 pt-3">
        <CardTitle className="flex items-center gap-2 text-sm font-semibold">
          <div className="p-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30">
            <Radio className="h-4 w-4 text-amber-600" />
          </div>
          F10.7 Flux
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-2">
        <EChartsWrapper option={option} height={160} showToolbox={false} />
        <div className="text-center -mt-1">
          <Badge
            className="text-xs font-medium shadow-sm"
            style={{ backgroundColor: hasData ? level.color : "#94a3b8", color: "#fff" }}
          >
            {hasData ? level.label : "No Data"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Publication-Quality Time Series Charts
// ---------------------------------------------------------------------------

interface TimeSeriesData {
  timestamp: string;
  kp?: number;
  dst?: number;
  speed?: number;
  density?: number;
  bz?: number;
  f107?: number;
}

function buildKpTimeSeriesChart(data: TimeSeriesData[]): Record<string, unknown> {
  // Format timestamps for display
  const timestamps = data.map((d) => {
    const date = new Date(d.timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, "0")}:00`;
  });
  
  // Extract only numeric Kp values
  const kpValues = data.map((d) => {
    const val = d.kp;
    return typeof val === "number" && !isNaN(val) ? val : null;
  });

  // Calculate bounds with safety
  const validKp = kpValues.filter((v): v is number => v !== null);
  const dataMin = validKp.length > 0 ? Math.min(...validKp) : 0;
  const dataMax = validKp.length > 0 ? Math.max(...validKp) : 5;

  return {
    title: {
      text: "Kp Index",
      left: "center",
      top: 10,
      textStyle: {
        fontSize: 15,
        fontWeight: "bold",
        color: PUBLICATION_COLORS.text,
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: PUBLICATION_COLORS.text, fontSize: 12 },
      formatter: (params: Array<{ axisValue: string; value: number | null }>) => {
        const p = params[0];
        if (!p || p.value === null || p.value === undefined) return "";
        const level = getKpLevel(p.value);
        return `<b>${p.axisValue}</b><br/>Kp: <span style="color:${level.color};font-weight:600">${p.value.toFixed(1)}</span> (${level.label})`;
      },
    },
    grid: {
      left: 50,
      right: 25,
      top: 45,
      bottom: 65,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 10,
        rotate: 0,
        interval: Math.max(0, Math.floor(data.length / 8)),
      },
      axisLine: { lineStyle: { color: PUBLICATION_COLORS.axis } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "Kp",
      nameLocation: "middle",
      nameGap: 30,
      nameTextStyle: { color: PUBLICATION_COLORS.text, fontSize: 12, fontWeight: "bold" },
      min: Math.max(0, Math.floor(dataMin) - 1),
      max: Math.min(9, Math.ceil(dataMax) + 1),
      interval: 1,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 11,
        formatter: (v: number) => v.toFixed(0),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: PUBLICATION_COLORS.grid, type: "dashed" } },
    },
    visualMap: {
      show: false,
      pieces: [
        { lte: 3.99, color: PUBLICATION_COLORS.quiet },
        { gt: 3.99, lte: 4.99, color: PUBLICATION_COLORS.unsettled },
        { gt: 4.99, lte: 5.99, color: PUBLICATION_COLORS.active },
        { gt: 5.99, lte: 6.99, color: PUBLICATION_COLORS.minor },
        { gt: 6.99, lte: 7.99, color: PUBLICATION_COLORS.major },
        { gt: 7.99, color: PUBLICATION_COLORS.severe },
      ],
    },
    series: [
      {
        name: "Kp",
        type: "bar",
        data: kpValues,
        barWidth: "70%",
        itemStyle: { borderRadius: [3, 3, 0, 0] },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1.5 },
          label: { fontSize: 10, distance: [10, 0] },
          data: [
            { yAxis: 4, label: { formatter: "G1", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.active } },
            { yAxis: 5, label: { formatter: "G2", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.minor } },
          ],
        },
      },
    ],
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5, borderColor: "transparent" },
    ],
    toolbox: {
      right: 10,
      top: 5,
      itemSize: 14,
      feature: {
        saveAsImage: { title: "PNG", pixelRatio: 3 },
      },
    },
  };
}

function buildDstTimeSeriesChart(data: TimeSeriesData[]): Record<string, unknown> {
  // Format timestamps for display
  const timestamps = data.map((d) => {
    const date = new Date(d.timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, "0")}:00`;
  });
  
  // Extract only numeric Dst values
  const dstValues = data.map((d) => {
    const val = d.dst;
    return typeof val === "number" && !isNaN(val) ? val : null;
  });

  // Calculate bounds with safety
  const validDst = dstValues.filter((v): v is number => v !== null);
  const dataMin = validDst.length > 0 ? Math.min(...validDst) : -100;
  const dataMax = validDst.length > 0 ? Math.max(...validDst) : 50;

  return {
    title: {
      text: "Dst Index",
      left: "center",
      top: 10,
      textStyle: {
        fontSize: 15,
        fontWeight: "bold",
        color: PUBLICATION_COLORS.text,
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: PUBLICATION_COLORS.text, fontSize: 12 },
      formatter: (params: Array<{ axisValue: string; value: number | null }>) => {
        const p = params[0];
        if (!p || p.value === null || p.value === undefined) return "";
        const level = getDstLevel(p.value);
        return `<b>${p.axisValue}</b><br/>Dst: <span style="color:${level.color};font-weight:600">${p.value.toFixed(0)} nT</span> (${level.label})`;
      },
    },
    grid: {
      left: 55,
      right: 25,
      top: 45,
      bottom: 65,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 10,
        rotate: 0,
        interval: Math.max(0, Math.floor(data.length / 8)),
      },
      axisLine: { lineStyle: { color: PUBLICATION_COLORS.axis } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "nT",
      nameLocation: "middle",
      nameGap: 35,
      nameTextStyle: { color: PUBLICATION_COLORS.text, fontSize: 12, fontWeight: "bold" },
      min: Math.floor((dataMin - 20) / 50) * 50,
      max: Math.ceil((dataMax + 20) / 50) * 50,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 11,
        formatter: (v: number) => v.toFixed(0),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: PUBLICATION_COLORS.grid, type: "dashed" } },
    },
    series: [
      {
        name: "Dst",
        type: "line",
        data: dstValues,
        smooth: true,
        lineStyle: { color: PUBLICATION_COLORS.dst, width: 2 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(220, 38, 38, 0.25)" },
              { offset: 1, color: "rgba(220, 38, 38, 0.02)" },
            ],
          },
        },
        symbol: "none",
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1.5 },
          label: { fontSize: 10, distance: [10, 0] },
          data: [
            { yAxis: 0, label: { formatter: "Quiet", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.quiet } },
            { yAxis: -50, label: { formatter: "Moderate", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.active } },
          ],
        },
      },
    ],
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5, borderColor: "transparent" },
    ],
    toolbox: {
      right: 10,
      top: 5,
      itemSize: 14,
      feature: {
        saveAsImage: { title: "PNG", pixelRatio: 3 },
      },
    },
  };
}

function buildSolarWindChart(data: TimeSeriesData[]): Record<string, unknown> {
  // Format timestamps
  const timestamps = data.map((d) => {
    const date = new Date(d.timestamp);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, "0")}:00`;
  });
  
  // Extract numeric values only
  const speedValues = data.map((d) => (typeof d.speed === "number" && !isNaN(d.speed) ? d.speed : null));
  const densityValues = data.map((d) => (typeof d.density === "number" && !isNaN(d.density) ? d.density : null));
  const bzValues = data.map((d) => (typeof d.bz === "number" && !isNaN(d.bz) ? d.bz : null));

  return {
    title: {
      text: "Solar Wind",
      left: "center",
      top: 10,
      textStyle: {
        fontSize: 15,
        fontWeight: "bold",
        color: PUBLICATION_COLORS.text,
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: PUBLICATION_COLORS.text, fontSize: 11 },
    },
    legend: {
      data: ["Speed", "Density", "Bz"],
      top: 35,
      textStyle: { color: PUBLICATION_COLORS.text, fontSize: 11 },
      itemGap: 20,
    },
    grid: {
      left: 55,
      right: 55,
      top: 70,
      bottom: 65,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 10,
        rotate: 0,
        interval: Math.max(0, Math.floor(data.length / 8)),
      },
      axisLine: { lineStyle: { color: PUBLICATION_COLORS.axis } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: "value",
        name: "km/s",
        position: "left",
        nameTextStyle: { color: PUBLICATION_COLORS.solarWind, fontSize: 11, fontWeight: "bold" },
        axisLabel: { color: PUBLICATION_COLORS.solarWind, fontSize: 10, formatter: (v: number) => v.toFixed(0) },
        axisLine: { show: false },
        splitLine: { lineStyle: { color: PUBLICATION_COLORS.grid, type: "dashed" } },
      },
      {
        type: "value",
        name: "nT / p/cm³",
        position: "right",
        nameTextStyle: { color: PUBLICATION_COLORS.bz, fontSize: 10 },
        axisLabel: { color: PUBLICATION_COLORS.bz, fontSize: 10, formatter: (v: number) => v.toFixed(0) },
        axisLine: { show: false },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "Speed",
        type: "line",
        data: speedValues,
        smooth: true,
        yAxisIndex: 0,
        lineStyle: { color: PUBLICATION_COLORS.solarWind, width: 2 },
        symbol: "none",
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(5, 150, 105, 0.15)" },
              { offset: 1, color: "rgba(5, 150, 105, 0)" },
            ],
          },
        },
      },
      {
        name: "Density",
        type: "line",
        data: densityValues,
        smooth: true,
        yAxisIndex: 1,
        lineStyle: { color: PUBLICATION_COLORS.f107, width: 1.5, type: "dashed" },
        symbol: "none",
      },
      {
        name: "Bz",
        type: "line",
        data: bzValues,
        smooth: true,
        yAxisIndex: 1,
        lineStyle: { color: PUBLICATION_COLORS.bz, width: 2 },
        symbol: "none",
      },
    ],
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5, borderColor: "transparent" },
    ],
    toolbox: {
      right: 10,
      top: 5,
      itemSize: 14,
      feature: {
        saveAsImage: { title: "PNG", pixelRatio: 3 },
      },
    },
  };
}

function buildF107Chart(f107Data: Array<{ timestamp: string; f107: number }>): Record<string, unknown> {
  // Format timestamps
  const timestamps = f107Data.map((d) => {
    const date = new Date(d.timestamp);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });
  
  // Extract numeric values
  const values = f107Data.map((d) => (typeof d.f107 === "number" && !isNaN(d.f107) ? d.f107 : null));

  return {
    title: {
      text: "F10.7 Flux",
      left: "center",
      top: 10,
      textStyle: {
        fontSize: 15,
        fontWeight: "bold",
        color: PUBLICATION_COLORS.text,
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: PUBLICATION_COLORS.text, fontSize: 12 },
    },
    grid: {
      left: 50,
      right: 25,
      top: 45,
      bottom: 65,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: timestamps,
      axisLabel: {
        color: PUBLICATION_COLORS.text,
        fontSize: 10,
        rotate: 0,
        interval: Math.max(0, Math.floor(f107Data.length / 8)),
      },
      axisLine: { lineStyle: { color: PUBLICATION_COLORS.axis } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "SFU",
      nameLocation: "middle",
      nameGap: 35,
      nameTextStyle: { color: PUBLICATION_COLORS.text, fontSize: 12, fontWeight: "bold" },
      axisLabel: { color: PUBLICATION_COLORS.text, fontSize: 11, formatter: (v: number) => v.toFixed(0) },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: PUBLICATION_COLORS.grid, type: "dashed" } },
    },
    series: [
      {
        name: "F10.7",
        type: "line",
        data: values,
        smooth: true,
        lineStyle: { color: PUBLICATION_COLORS.f107, width: 2 },
        symbol: "none",
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(217, 119, 6, 0.2)" },
              { offset: 1, color: "rgba(217, 119, 6, 0)" },
            ],
          },
        },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1.5 },
          label: { fontSize: 10, distance: [10, 0] },
          data: [
            { yAxis: 70, label: { formatter: "Min", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.quiet } },
            { yAxis: 150, label: { formatter: "High", position: "end" }, lineStyle: { color: PUBLICATION_COLORS.minor } },
          ],
        },
      },
    ],
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5, borderColor: "transparent" },
    ],
    toolbox: {
      right: 10,
      top: 5,
      itemSize: 14,
      feature: {
        saveAsImage: { title: "PNG", pixelRatio: 3 },
      },
    },
  };
}

// ---------------------------------------------------------------------------
// Impact Prediction Card
// ---------------------------------------------------------------------------

function ImpactCard({ prediction }: { prediction: ImpactPrediction }) {
  const icon = CATEGORY_ICONS[prediction.category] || "⚡";

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 rounded-lg border bg-card"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h4 className="font-medium capitalize">
              {prediction.category.replace("_", " ")}
            </h4>
            <p className="text-xs text-muted-foreground">
              {prediction.arrival_time
                ? formatDateTime(prediction.arrival_time)
                : "Unknown arrival"}
            </p>
          </div>
        </div>
        <Badge variant={severityVariants[prediction.severity]}>
          {prediction.severity}
        </Badge>
      </div>
      {prediction.biological_effect && (
        <p className="text-sm text-muted-foreground mt-3">
          {prediction.biological_effect}
        </p>
      )}
      {prediction.polar_h10_recommendation && (
        <div className="mt-3 p-2 rounded bg-muted/50">
          <p className="text-xs font-medium">📍 Polar H10 Recommendation:</p>
          <p className="text-xs text-muted-foreground">
            {prediction.polar_h10_recommendation}
          </p>
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Quick Metrics Card
// ---------------------------------------------------------------------------

function QuickMetricsCard({ data }: { data: SpaceWeatherSnapshot | null }) {
  const metrics = [
    {
      label: "X-ray Flux",
      value: data?.data.xray_class || "N/A",
      icon: <Radiation className="h-4 w-4" />,
      color: "text-purple-600",
    },
    {
      label: "Proton >10 MeV",
      value: data?.data.proton_flux_10mev?.toExponential(1) || "N/A",
      icon: <Zap className="h-4 w-4" />,
      color: "text-pink-600",
    },
    {
      label: "IMF Bz",
      value: data?.data.solar_wind_bz
        ? `${data.data.solar_wind_bz.toFixed(1)} nT`
        : "N/A",
      icon: <Target className="h-4 w-4" />,
      color: "text-cyan-600",
    },
    {
      label: "Wind Density",
      value: data?.data.solar_wind_density
        ? `${data.data.solar_wind_density.toFixed(1)} p/cm³`
        : "N/A",
      icon: <Wind className="h-4 w-4" />,
      color: "text-green-600",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <BarChart3 className="h-5 w-5" />
          Additional Metrics
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {metrics.map((metric, idx) => (
            <div key={idx} className="p-3 rounded-lg bg-muted/50">
              <div className="flex items-center gap-2 mb-1">
                <span className={metric.color}>{metric.icon}</span>
                <span className="text-xs text-muted-foreground">{metric.label}</span>
              </div>
              <p className="text-lg font-semibold">{metric.value}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function SpaceWeatherPage() {
  const [currentData, setCurrentData] = React.useState<SpaceWeatherSnapshot | null>(null);
  const [noaaData, setNoaaData] = React.useState<NOAADataResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [lastFetch, setLastFetch] = React.useState<Date | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [timeRange, setTimeRange] = React.useState<string>("7");

  const informationalPatterns = React.useMemo(
    () => [
      "No ENLIL record",
      "No solar wind plasma",
      "No CME",
      "not found",
      "No data available",
      "no recent",
    ],
    [],
  );

  const isInformationalMessage = React.useCallback((msg: string): boolean => {
    const lowerMsg = msg.toLowerCase();
    return informationalPatterns.some((pattern) =>
      lowerMsg.includes(pattern.toLowerCase())
    );
  }, [informationalPatterns]);

  const fetchAllData = React.useCallback(async (forceRefresh: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch current snapshot and historical NOAA data in parallel
      const [snapshot, datasets] = await Promise.all([
        forceRefresh ? refreshSpaceWeather(true) : getCurrentSpaceWeather(),
        getNOAADatasets(
          parseInt(timeRange),
          "planetary_k_index_3h,geospace_dst,solar_wind_wind,solar_wind_mag,f107_flux"
        ),
      ]);

      setCurrentData(snapshot);
      setNoaaData(datasets);
      setLastFetch(new Date());

      // Check for actual errors
      if (snapshot.errors && Object.keys(snapshot.errors).length > 0) {
        const actualErrors = Object.values(snapshot.errors).filter(
          (msg) => !isInformationalMessage(msg)
        );
        if (actualErrors.length > 0) {
          setError(actualErrors.join(", "));
        }
      }
    } catch (err) {
      console.error("Failed to fetch space weather:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, [timeRange, isInformationalMessage]);

  React.useEffect(() => {
    fetchAllData(false);
  }, [fetchAllData]);

  // Generate sample data for demonstration when API data is unavailable
  const generateSampleData = React.useCallback((days: number): TimeSeriesData[] => {
    const data: TimeSeriesData[] = [];
    const now = new Date();
    const hoursBack = days * 24;
    
    for (let h = hoursBack; h >= 0; h -= 3) {
      const timestamp = new Date(now.getTime() - h * 60 * 60 * 1000);
      // Simulate realistic space weather patterns
      const baseKp = 2 + Math.sin(h / 12) * 1.5 + Math.random() * 1;
      const baseDst = -10 - Math.sin(h / 24) * 30 - Math.random() * 20;
      const baseSpeed = 380 + Math.sin(h / 18) * 80 + Math.random() * 50;
      const baseDensity = 5 + Math.sin(h / 12) * 3 + Math.random() * 2;
      const baseBz = Math.sin(h / 6) * 5 + (Math.random() - 0.5) * 4;
      
      data.push({
        timestamp: timestamp.toISOString(),
        kp: Math.max(0, Math.min(9, baseKp)),
        dst: Math.max(-300, Math.min(50, baseDst)),
        speed: Math.max(200, Math.min(800, baseSpeed)),
        density: Math.max(1, Math.min(30, baseDensity)),
        bz: Math.max(-20, Math.min(20, baseBz)),
      });
    }
    return data;
  }, []);

  // Prepare time series data from NOAA response
  const timeSeriesData = React.useMemo((): TimeSeriesData[] => {
    // If NOAA data exists and has content, use it
    if (noaaData) {
      const kpData = noaaData.kp_data || [];
      const dstData = noaaData.dst_data || [];
      const solarWindData = noaaData.solar_wind_data || [];

      // Check if we have any actual data
      if (kpData.length > 0 || dstData.length > 0 || solarWindData.length > 0) {
        // Merge all data by timestamp
        const merged: Map<string, TimeSeriesData> = new Map();

        kpData.forEach((d: { timestamp: string; kp: number | null }) => {
          if (d.timestamp && d.kp !== null) {
            const ts = d.timestamp;
            merged.set(ts, { ...merged.get(ts), timestamp: ts, kp: d.kp });
          }
        });

        dstData.forEach((d: { timestamp: string; dst: number | null }) => {
          if (d.timestamp && d.dst !== null) {
            const ts = d.timestamp;
            merged.set(ts, { ...merged.get(ts), timestamp: ts, dst: d.dst });
          }
        });

        solarWindData.forEach((d: { timestamp: string; speed?: number | null; density?: number | null; bz?: number | null }) => {
          if (d.timestamp) {
            const ts = d.timestamp;
            const existing = merged.get(ts) || { timestamp: ts };
            merged.set(ts, {
              ...existing,
              timestamp: ts,
              speed: d.speed ?? existing.speed,
              density: d.density ?? existing.density,
              bz: d.bz ?? existing.bz,
            });
          }
        });

        // Sort by timestamp and return
        const sortedData = Array.from(merged.values()).sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );
        
        if (sortedData.length > 0) {
          return sortedData;
        }
      }
    }
    
    // Fall back to sample data for demonstration
    console.log("Using sample space weather data for demonstration");
    return generateSampleData(parseInt(timeRange));
  }, [noaaData, timeRange, generateSampleData]);

  // Filter data for each chart type
  const kpChartData = React.useMemo(() => 
    timeSeriesData.filter((d) => d.kp !== undefined && d.kp !== null),
    [timeSeriesData]
  );
  
  const dstChartData = React.useMemo(() =>
    timeSeriesData.filter((d) => d.dst !== undefined && d.dst !== null),
    [timeSeriesData]
  );
  
  const solarWindChartData = React.useMemo(() =>
    timeSeriesData.filter(
      (d) => (d.speed !== undefined && d.speed !== null) || 
             (d.density !== undefined && d.density !== null) || 
             (d.bz !== undefined && d.bz !== null)
    ),
    [timeSeriesData]
  );

  return (
    <PageWrapper
      title="Space Weather Dashboard"
      description="Publication-quality NOAA/NASA space weather monitoring for research correlation"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            {lastFetch && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated: {formatDateTime(lastFetch.toISOString())}
              </Badge>
            )}
            {currentData?.most_severe && (
              <Badge
                variant={severityVariants[currentData.most_severe.severity]}
                className="flex items-center gap-1"
              >
                <AlertTriangle className="h-3 w-3" />
                {currentData.most_severe.severity.toUpperCase()} conditions
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3">3 Days</SelectItem>
                <SelectItem value="7">7 Days</SelectItem>
                <SelectItem value="14">14 Days</SelectItem>
                <SelectItem value="30">30 Days</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={() => fetchAllData(true)} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {/* Error Display */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
                <div>
                  <p className="font-medium text-destructive">Data Fetch Error</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="overview" className="gap-2">
              <Sun className="h-4 w-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="kp-dst" className="gap-2">
              <Compass className="h-4 w-4" />
              <span className="hidden sm:inline">Kp & Dst</span>
            </TabsTrigger>
            <TabsTrigger value="solar-wind" className="gap-2">
              <Wind className="h-4 w-4" />
              <span className="hidden sm:inline">Solar Wind</span>
            </TabsTrigger>
            <TabsTrigger value="science" className="gap-2">
              <TrendingUp className="h-4 w-4" />
              <span className="hidden sm:inline">Scientific Context</span>
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Gauges Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <KpGauge value={currentData?.data.kp_index ?? null} />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <DstGauge value={currentData?.data.dst_index ?? null} />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <SolarWindGauge
                  speed={currentData?.data.solar_wind_speed ?? null}
                  density={currentData?.data.solar_wind_density ?? null}
                />
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <F107Gauge value={currentData?.data.f10_7_flux ?? null} />
              </motion.div>
            </div>

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Impact Predictions */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-warning" />
                      Impact Predictions
                    </CardTitle>
                    <CardDescription>
                      Expected arrival times and biological effects
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {currentData?.predictions && currentData.predictions.length > 0 ? (
                      currentData.predictions.map((pred, idx) => (
                        <ImpactCard key={idx} prediction={pred} />
                      ))
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        <Sun className="h-12 w-12 mx-auto mb-3 opacity-50" />
                        <p>No significant impacts predicted</p>
                        <p className="text-sm">Conditions are nominal</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              {/* Quick Metrics + Recommendation */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="space-y-4"
              >
                <QuickMetricsCard data={currentData} />

                {/* Measurement Recommendation */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Activity className="h-5 w-5 text-success" />
                      HRV Recording Recommendation
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div
                      className={`p-4 rounded-lg ${
                        (currentData?.data.kp_index ?? 0) < 4
                          ? "bg-success/10 border border-success/30"
                          : (currentData?.data.kp_index ?? 0) < 5
                          ? "bg-warning/10 border border-warning/30"
                          : "bg-danger/10 border border-danger/30"
                      }`}
                    >
                      <p className="font-medium">
                        {(currentData?.data.kp_index ?? 0) < 4
                          ? "✓ Good Conditions for HRV Recording"
                          : (currentData?.data.kp_index ?? 0) < 5
                          ? "⚠ Moderate Conditions - Proceed with Awareness"
                          : "⚠ Disturbed Conditions - Document for Correlation"}
                      </p>
                      <p className="text-sm text-muted-foreground mt-2">
                        {(currentData?.data.kp_index ?? 0) < 4
                          ? "Geomagnetic conditions are quiet. Optimal window for baseline measurements."
                          : (currentData?.data.kp_index ?? 0) < 5
                          ? "Minor activity detected. Record with space weather annotation."
                          : "Storm in progress. HRV may show atypical patterns - document conditions."}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </TabsContent>

          {/* Kp & Dst Tab */}
          <TabsContent value="kp-dst" className="space-y-6">
            {/* Kp Index Time Series */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">
                  Planetary K-index: Global geomagnetic activity (0-9 scale). G1-G5 = NOAA storm levels.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {kpChartData.length > 0 ? (
                  <EChartsWrapper
                    option={buildKpTimeSeriesChart(kpChartData)}
                    height={350}
                    showToolbox={false}
                  />
                ) : (
                  <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                    <div className="text-center">
                      <Compass className="h-10 w-10 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Loading Kp data...</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Dst Index Time Series */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">
                  Disturbance Storm Time index: Ring current strength in nanoTesla. Negative values indicate storms.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {dstChartData.length > 0 ? (
                  <EChartsWrapper
                    option={buildDstTimeSeriesChart(dstChartData)}
                    height={350}
                    showToolbox={false}
                  />
                ) : (
                  <div className="flex items-center justify-center h-[350px] text-muted-foreground">
                    <div className="text-center">
                      <Waves className="h-10 w-10 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Loading Dst data...</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Scientific Reference */}
            <Card>
              <CardHeader>
                <CardTitle>Geomagnetic Indices Reference</CardTitle>
              </CardHeader>
              <CardContent className="prose prose-sm max-w-none">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-semibold text-base mb-2">Kp Index Scale</h4>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-1">Kp</th>
                          <th className="text-left py-1">Level</th>
                          <th className="text-left py-1">NOAA Scale</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr><td>0-3</td><td style={{color: PUBLICATION_COLORS.quiet}}>Quiet</td><td>G0</td></tr>
                        <tr><td>4</td><td style={{color: PUBLICATION_COLORS.unsettled}}>Unsettled</td><td>G0</td></tr>
                        <tr><td>5</td><td style={{color: PUBLICATION_COLORS.active}}>Minor Storm</td><td>G1</td></tr>
                        <tr><td>6</td><td style={{color: PUBLICATION_COLORS.minor}}>Moderate Storm</td><td>G2</td></tr>
                        <tr><td>7</td><td style={{color: PUBLICATION_COLORS.major}}>Strong Storm</td><td>G3</td></tr>
                        <tr><td>8</td><td style={{color: PUBLICATION_COLORS.severe}}>Severe Storm</td><td>G4</td></tr>
                        <tr><td>9</td><td style={{color: PUBLICATION_COLORS.extreme}}>Extreme Storm</td><td>G5</td></tr>
                      </tbody>
                    </table>
                  </div>
                  <div>
                    <h4 className="font-semibold text-base mb-2">Dst Index Interpretation</h4>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-1">Dst (nT)</th>
                          <th className="text-left py-1">Classification</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr><td>&gt; -20</td><td style={{color: PUBLICATION_COLORS.quiet}}>Quiet</td></tr>
                        <tr><td>-20 to -50</td><td style={{color: PUBLICATION_COLORS.unsettled}}>Weak Storm</td></tr>
                        <tr><td>-50 to -100</td><td style={{color: PUBLICATION_COLORS.active}}>Moderate Storm</td></tr>
                        <tr><td>-100 to -200</td><td style={{color: PUBLICATION_COLORS.minor}}>Strong Storm</td></tr>
                        <tr><td>-200 to -350</td><td style={{color: PUBLICATION_COLORS.major}}>Severe Storm</td></tr>
                        <tr><td>&lt; -350</td><td style={{color: PUBLICATION_COLORS.extreme}}>Extreme Storm</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-4 italic">
                  Reference: Gonzalez, W.D., et al. (1994). What is a geomagnetic storm? 
                  Journal of Geophysical Research, 99(A4), 5771-5792.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Solar Wind Tab */}
          <TabsContent value="solar-wind" className="space-y-6">
            {/* Solar Wind Time Series */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="text-xs">
                  ACE/DSCOVR real-time data: Speed (km/s), proton density (p/cm³), IMF Bz (nT). Southward Bz enables geomagnetic coupling.
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {solarWindChartData.length > 0 ? (
                  <EChartsWrapper
                    option={buildSolarWindChart(solarWindChartData)}
                    height={380}
                    showToolbox={false}
                  />
                ) : (
                  <div className="flex items-center justify-center h-[380px] text-muted-foreground">
                    <div className="text-center">
                      <Wind className="h-10 w-10 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Loading solar wind data...</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Solar Wind Reference */}
            <Card>
              <CardHeader>
                <CardTitle>Solar Wind Parameters Reference</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <h4 className="font-semibold mb-2" style={{color: PUBLICATION_COLORS.solarWind}}>
                      Speed (km/s)
                    </h4>
                    <ul className="text-sm space-y-1">
                      <li>&lt;400: Slow wind</li>
                      <li>400-500: Nominal</li>
                      <li>500-600: Enhanced</li>
                      <li>600-700: High speed</li>
                      <li>&gt;700: Very high (CME)</li>
                    </ul>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <h4 className="font-semibold mb-2" style={{color: PUBLICATION_COLORS.f107}}>
                      Density (p/cm³)
                    </h4>
                    <ul className="text-sm space-y-1">
                      <li>&lt;5: Low density</li>
                      <li>5-10: Nominal</li>
                      <li>10-20: Enhanced</li>
                      <li>&gt;20: High (shock)</li>
                    </ul>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/50">
                    <h4 className="font-semibold mb-2" style={{color: PUBLICATION_COLORS.bz}}>
                      IMF Bz (nT)
                    </h4>
                    <ul className="text-sm space-y-1">
                      <li>&gt;0: Northward (quiet)</li>
                      <li>&lt;0: Southward (coupling)</li>
                      <li>&lt;-10: Strong coupling</li>
                      <li>&lt;-20: Severe (storm)</li>
                    </ul>
                    <p className="text-xs text-muted-foreground mt-2">
                      Southward Bz enables geomagnetic coupling
                    </p>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground italic">
                  Data source: ACE/DSCOVR spacecraft at L1 Lagrange point, ~1.5 million km from Earth.
                  Provides ~30-60 minute advance warning of solar wind conditions.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Scientific Context Tab */}
          <TabsContent value="science" className="space-y-6">
            <div className="grid md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Cardiovascular Effects of Geomagnetic Activity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <p>
                    Multiple epidemiological studies have demonstrated associations between 
                    geomagnetic activity and cardiovascular health outcomes:
                  </p>
                  <ul className="list-disc pl-4 space-y-2">
                    <li>
                      <strong>HRV Depression:</strong> Reduced RMSSD and HF power during 
                      geomagnetic storms (Kp ≥ 5), indicating parasympathetic withdrawal.
                    </li>
                    <li>
                      <strong>Blood Pressure:</strong> Increased variability during disturbed 
                      geomagnetic conditions, particularly in sensitive individuals.
                    </li>
                    <li>
                      <strong>Myocardial Events:</strong> Statistical increase in acute MI 
                      incidence 1-3 days following major geomagnetic storms.
                    </li>
                    <li>
                      <strong>Lag Effects:</strong> Physiological responses typically appear 
                      12-48 hours after geomagnetic disturbance onset.
                    </li>
                  </ul>
                  <Separator />
                  <div className="text-xs text-muted-foreground">
                    <p className="font-semibold mb-1">Key References:</p>
                    <p>
                      Alabdulgader, A., et al. (2018). Long-term study of heart rate variability 
                      responses to changes in the solar and geomagnetic environment. 
                      Scientific Reports, 8, 2663.
                    </p>
                    <p className="mt-1">
                      Cornélissen, G., et al. (2002). Non-photic solar associations of heart rate 
                      variability and myocardial infarction. Journal of Atmospheric and 
                      Solar-Terrestrial Physics, 64(5-6), 707-720.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Proposed Mechanisms</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div>
                    <h4 className="font-semibold">1. Schumann Resonance Modulation</h4>
                    <p className="text-muted-foreground">
                      Geomagnetic activity alters the Earth-ionosphere cavity, modifying 
                      Schumann resonances (7.83 Hz fundamental) which overlap with human 
                      EEG alpha rhythms and cardiac frequencies.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-semibold">2. Magnetoreception</h4>
                    <p className="text-muted-foreground">
                      Cryptochrome proteins in the retina and pineal gland may detect 
                      geomagnetic field variations, affecting circadian rhythms and 
                      melatonin production.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-semibold">3. Autonomic Nervous System</h4>
                    <p className="text-muted-foreground">
                      Geomagnetic disturbances appear to shift autonomic balance toward 
                      sympathetic dominance, measurable through HRV metrics (LF/HF ratio, 
                      reduced HF power).
                    </p>
                  </div>
                  <div>
                    <h4 className="font-semibold">4. Oxidative Stress</h4>
                    <p className="text-muted-foreground">
                      Some research suggests geomagnetic storms may increase reactive 
                      oxygen species production, contributing to cardiovascular stress.
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>HRV Recording Guidelines for Space Weather Correlation</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-lg bg-success/10 border border-success/30">
                      <h4 className="font-semibold text-success mb-2">✓ Baseline Recordings</h4>
                      <p className="text-sm">
                        Prefer Kp &lt; 4 (quiet conditions) for establishing personal baselines. 
                        Document date, time, and current space weather conditions.
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-warning/10 border border-warning/30">
                      <h4 className="font-semibold text-warning mb-2">⚠ Storm Recordings</h4>
                      <p className="text-sm">
                        Recordings during Kp ≥ 5 are valuable for correlation analysis. 
                        Note: Results may show atypical patterns - this is expected.
                      </p>
                    </div>
                    <div className="p-4 rounded-lg bg-info/10 border border-info/30">
                      <h4 className="font-semibold text-info mb-2">📊 Analysis Tips</h4>
                      <p className="text-sm">
                        Consider 12-48 hour lag when correlating HRV with space weather. 
                        Use 7-day EWMA smoothing for trend visualization.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </PageWrapper>
  );
}
