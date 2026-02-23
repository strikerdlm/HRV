// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Activity,
  RefreshCw,
  Settings,
  TrendingUp,
  AlertTriangle,
  Clock,
  GitCompare,
  Layers,
  BarChart3,
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EChartsWrapper, SCIENTIFIC_COLORS, autoAxisBounds } from "@/components/charts";
import { QualityPanel } from "@/components/research/quality-panel";
import { getHRVWindowed } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type {
  WindowedMetricsResponse,
  TrendStatistic,
  PhysiologicalCorrelation,
} from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

function metricLabel(metric: string): string {
  const labels: Record<string, string> = {
    rmssd: "RMSSD",
    sdnn: "SDNN",
    mean_hr: "Mean HR",
    lf_hf_ratio: "LF/HF Ratio",
    resting_hr_bpm: "Resting HR",
    sleep_duration_hours: "Sleep Duration",
    avg_spo2: "Avg SpO2",
    stress_score: "Stress Score",
    body_battery_avg: "Body Battery",
    avg_respiration_sleep: "Sleep Respiration",
    avg_respiration_awake: "Awake Respiration",
  };
  return labels[metric] ?? metric;
}

function formatXLabels(timestamps: string[]): string[] {
  return timestamps.map((ts) => {
    if (!ts) {
      return "";
    }
    const date = new Date(ts);
    if (Number.isNaN(date.getTime())) {
      return ts;
    }
    return `${date.toLocaleDateString(undefined, { month: "short", day: "2-digit" })} ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
  });
}

function finiteValues(values: (number | null)[]): number[] {
  return values.filter((value): value is number => value !== null && Number.isFinite(value));
}

function zScoreSeries(values: (number | null)[]): (number | null)[] {
  const valid = finiteValues(values);
  if (valid.length < 3) {
    return values;
  }
  const mean = valid.reduce((sum, value) => sum + value, 0) / valid.length;
  const variance = valid.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (valid.length - 1);
  const std = Math.sqrt(Math.max(variance, 1e-8));
  return values.map((value) => (value === null ? null : (value - mean) / std));
}

function trendBadgeColor(direction: string): string {
  if (direction === "increasing") return SCIENTIFIC_COLORS.success;
  if (direction === "decreasing") return SCIENTIFIC_COLORS.danger;
  if (direction === "stable") return SCIENTIFIC_COLORS.info;
  return SCIENTIFIC_COLORS.warning;
}

function LongitudinalOverviewChart({ data }: { data: WindowedMetricsResponse }) {
  const xLabels = formatXLabels(data.timestamps);
  const interval = Math.max(0, Math.ceil(xLabels.length / 9) - 1);
  const rmssdValues = finiteValues(data.rmssd);
  const sdnnValues = finiteValues(data.sdnn);
  const hrValues = finiteValues(data.mean_hr);
  const leftBounds = autoAxisBounds(...rmssdValues, ...sdnnValues);
  const rightBounds = autoAxisBounds(...hrValues);

  const option: Record<string, unknown> = {
    grid: { left: 70, right: 70, top: 40, bottom: 80, containLabel: true },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 5 },
    ],
    xAxis: {
      type: "category",
      data: xLabels,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval,
        showMinLabel: true,
        showMaxLabel: true,
        fontSize: 10,
      },
      name: "Measurement Windows Over Time",
      nameLocation: "middle",
      nameGap: 55,
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    yAxis: [
      {
        type: "value",
        name: "RMSSD / SDNN (ms)",
        min: leftBounds.min,
        max: leftBounds.max,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
      {
        type: "value",
        name: "Mean HR (bpm)",
        min: rightBounds.min,
        max: rightBounds.max,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
    ],
    legend: {
      top: 8,
      right: 10,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    series: [
      {
        name: "RMSSD",
        type: "line",
        data: data.rmssd,
        yAxisIndex: 0,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.success },
      },
      {
        name: "RMSSD EWMA",
        type: "line",
        data: data.rmssd_ewma,
        yAxisIndex: 0,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, type: "dashed", color: SCIENTIFIC_COLORS.trend },
      },
      {
        name: "SDNN",
        type: "line",
        data: data.sdnn,
        yAxisIndex: 0,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.primary },
      },
      {
        name: "Mean HR",
        type: "line",
        data: data.mean_hr,
        yAxisIndex: 1,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.danger },
      },
    ],
    tooltip: { trigger: "axis" },
  };

  return <EChartsWrapper option={option} height={380} />;
}

function SingleMetricChart({
  data,
  metric,
  trend,
}: {
  data: WindowedMetricsResponse;
  metric: "rmssd" | "sdnn";
  trend: (number | null)[];
}) {
  const values = metric === "rmssd" ? data.rmssd : data.sdnn;
  const label = metric === "rmssd" ? "RMSSD" : "SDNN";
  const unit = "ms";
  const color = metric === "rmssd" ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.primary;
  const xLabels = formatXLabels(data.timestamps);
  const interval = Math.max(0, Math.ceil(xLabels.length / 8) - 1);
  const bounds = autoAxisBounds(...finiteValues(values));

  const option: Record<string, unknown> = {
    grid: { left: 60, right: 25, top: 35, bottom: 75, containLabel: true },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5 },
    ],
    xAxis: {
      type: "category",
      data: xLabels,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval,
        showMinLabel: true,
        showMaxLabel: true,
        fontSize: 10,
      },
      name: "Time",
      nameLocation: "middle",
      nameGap: 45,
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      name: `${label} (${unit})`,
      min: bounds.min,
      max: bounds.max,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    legend: {
      top: 6,
      right: 8,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    series: [
      {
        name: label,
        type: "line",
        data: values,
        smooth: false,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 1.8, color },
        itemStyle: { color },
        ...(metric === "rmssd"
          ? {
              markPoint: {
                data: data.anomaly_indices
                  .filter((idx) => idx >= 0 && idx < values.length && values[idx] !== null)
                  .map((idx) => ({
                    coord: [idx, values[idx]],
                    symbol: "pin",
                    symbolSize: 28,
                    itemStyle: { color: SCIENTIFIC_COLORS.danger },
                  })),
              },
            }
          : {}),
      },
      {
        name: "EWMA Trend",
        type: "line",
        data: trend,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, type: "dashed", color: SCIENTIFIC_COLORS.trend },
      },
    ],
    tooltip: { trigger: "axis" },
  };

  return <EChartsWrapper option={option} height={320} />;
}

function CorrelationHeatmap({
  labels,
  matrix,
  pMatrix,
  qMatrix,
}: {
  labels: string[];
  matrix: (number | null)[][];
  pMatrix: (number | null)[][];
  qMatrix?: (number | null)[][];
}) {
  if (labels.length === 0 || matrix.length === 0) {
    return null;
  }

  const heatmapData: [number, number, number, number, number][] = [];
  for (let row = 0; row < labels.length; row += 1) {
    for (let col = 0; col < labels.length; col += 1) {
      const value = matrix[row]?.[col];
      if (value === null || value === undefined || Number.isNaN(value)) {
        continue;
      }
      const pVal = pMatrix[row]?.[col] ?? 1;
      const qVal = qMatrix?.[row]?.[col] ?? pVal;
      heatmapData.push([col, row, value, pVal, qVal]);
    }
  }

  const option: Record<string, unknown> = {
    grid: { left: 120, right: 85, top: 30, bottom: 75, containLabel: true },
    xAxis: {
      type: "category",
      data: labels.map(metricLabel),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, interval: 0, rotate: 20, fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: labels.map(metricLabel),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "vertical",
      right: 10,
      top: "center",
      itemHeight: 180,
      inRange: {
        color: ["#2563eb", "#60a5fa", "#f8fafc", "#fbbf24", "#dc2626"],
      },
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "heatmap",
        data: heatmapData,
        label: {
          show: true,
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 9,
          formatter: (params: { value: number[] }) => {
            const r = params.value[2];
            const q = params.value[4];
            let stars = "";
            if (q < 0.001) stars = "***";
            else if (q < 0.01) stars = "**";
            else if (q < 0.05) stars = "*";
            return `${r.toFixed(2)}${stars}`;
          },
        },
        itemStyle: {
          borderWidth: 1,
          borderColor: "#ffffff",
        },
      },
    ],
    tooltip: {
      formatter: (params: { value: number[] }) => {
        const [xIdx, yIdx, r, p, q] = params.value;
        return `<b>${metricLabel(labels[yIdx])} vs ${metricLabel(labels[xIdx])}</b><br/>r = ${r.toFixed(3)}<br/>p = ${p.toFixed(4)}<br/>q = ${q.toFixed(4)}`;
      },
    },
  };

  return <EChartsWrapper option={option} height={380} />;
}

function PhysiologyOverlayChart({ data }: { data: WindowedMetricsResponse }) {
  const seriesMap = data.physiological_series ?? {};
  const baseTimestamps = data.physiological_timestamps ?? [];
  const candidateKeys = Object.keys(seriesMap);
  if (baseTimestamps.length === 0 || candidateKeys.length === 0) {
    return null;
  }

  const topCorrelations = (data.physiological_correlations ?? [])
    .filter((corr) => typeof corr.other_metric === "string")
    .sort((a, b) => Math.abs(b.r ?? 0) - Math.abs(a.r ?? 0))
    .map((corr) => corr.other_metric);

  const selectedKeys = ["rmssd", ...topCorrelations]
    .filter((key, index, arr) => arr.indexOf(key) === index)
    .filter((key) => key in seriesMap)
    .slice(0, 6);

  if (selectedKeys.length < 2) {
    return null;
  }

  const xLabels = baseTimestamps.map((ts) =>
    new Date(ts).toLocaleDateString(undefined, { month: "short", day: "2-digit" }),
  );
  const interval = Math.max(0, Math.ceil(xLabels.length / 9) - 1);

  const option: Record<string, unknown> = {
    grid: { left: 65, right: 25, top: 35, bottom: 70, containLabel: true },
    xAxis: {
      type: "category",
      data: xLabels,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, interval, fontSize: 10 },
      name: "Date",
      nameLocation: "middle",
      nameGap: 40,
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: "Standardized Trend (z-score)",
      min: -3.5,
      max: 3.5,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
    },
    legend: {
      top: 6,
      right: 10,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    series: selectedKeys.map((key, idx) => ({
      name: metricLabel(key),
      type: "line",
      data: zScoreSeries(seriesMap[key] ?? []),
      smooth: true,
      symbol: "none",
      lineStyle: { width: key === "rmssd" ? 2.5 : 1.8, color: SCIENTIFIC_COLORS.series[idx % SCIENTIFIC_COLORS.series.length] },
    })),
    tooltip: { trigger: "axis" },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 18, bottom: 5 },
    ],
  };

  return <EChartsWrapper option={option} height={330} />;
}

function TrendStatisticsCards({ stats }: { stats: TrendStatistic[] }) {
  if (!stats.length) {
    return null;
  }
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((item) => {
        const directionColor = trendBadgeColor(item.direction);
        return (
          <div key={item.metric} className="rounded-lg border bg-card p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-sm font-semibold">{item.metric}</p>
              <Badge variant="outline" style={{ borderColor: directionColor, color: directionColor }}>
                {item.direction}
              </Badge>
            </div>
            <div className="space-y-1 text-xs text-muted-foreground">
              <p>
                OLS slope/day:{" "}
                <span className="font-medium text-foreground">
                  {item.slope_per_day !== null && item.slope_per_day !== undefined
                    ? item.slope_per_day.toFixed(3)
                    : "—"}
                </span>
              </p>
              <p>
                Robust slope/day:{" "}
                <span className="font-medium text-foreground">
                  {item.robust_slope_per_day !== null && item.robust_slope_per_day !== undefined
                    ? item.robust_slope_per_day.toFixed(3)
                    : "—"}
                </span>
              </p>
              <p>
                95% slope CI:{" "}
                <span className="font-medium text-foreground">
                  {item.slope_ci_low !== null &&
                  item.slope_ci_low !== undefined &&
                  item.slope_ci_high !== null &&
                  item.slope_ci_high !== undefined
                    ? `[${item.slope_ci_low.toFixed(3)}, ${item.slope_ci_high.toFixed(3)}]`
                    : "—"}
                </span>
              </p>
              <p>
                Delta vs baseline:{" "}
                <span className="font-medium text-foreground">
                  {item.delta_pct !== null && item.delta_pct !== undefined
                    ? `${item.delta_pct.toFixed(1)}%`
                    : "—"}
                </span>
              </p>
              <p>
                Kendall tau / p:{" "}
                <span className="font-medium text-foreground">
                  {item.kendall_tau !== null && item.kendall_tau !== undefined
                    ? item.kendall_tau.toFixed(3)
                    : "—"}
                  {" / "}
                  {item.p_value !== null && item.p_value !== undefined
                    ? item.p_value.toFixed(4)
                    : "—"}
                </span>
              </p>
              <p>
                q-value:{" "}
                <span className="font-medium text-foreground">
                  {item.q_value !== null && item.q_value !== undefined
                    ? item.q_value.toFixed(4)
                    : "—"}
                </span>
              </p>
              <p>
                FDR status:{" "}
                <span className="font-medium text-foreground">
                  {item.fdr_significance ?? "not_tested"}
                </span>
              </p>
              <p>
                n ={" "}
                <span className="font-medium text-foreground">
                  {item.n_samples}
                </span>
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CorrelationInsights({ correlations }: { correlations: PhysiologicalCorrelation[] }) {
  if (!correlations.length) {
    return null;
  }
  return (
    <div className="space-y-3">
      {correlations.slice(0, 6).map((corr, idx) => (
        <div key={`${corr.other_metric}-${idx}`} className="rounded-lg border bg-card p-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium">
              RMSSD vs {metricLabel(corr.other_metric)}
            </p>
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                r={corr.r !== null && corr.r !== undefined ? corr.r.toFixed(3) : "—"}
              </Badge>
              {corr.significance === "fdr_significant" && (
                <Badge variant="outline" className="border-success text-success">
                  FDR sig
                </Badge>
              )}
            </div>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {corr.interpretation ?? "Association over time"} | p=
            {corr.p_value !== null && corr.p_value !== undefined ? corr.p_value.toFixed(4) : "—"} | n=
            {corr.n_samples}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            q={corr.q_value !== null && corr.q_value !== undefined ? corr.q_value.toFixed(4) : "—"} | effect=
            {corr.effect_size ?? "—"}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function WindowedPage() {
  const [data, setData] = React.useState<WindowedMetricsResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [windowSize, setWindowSize] = React.useState(300);
  const [stepSize, setStepSize] = React.useState(60);
  const [scope, setScope] = React.useState<"all" | "selected">("all");

  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getHRVWindowed(userId, windowSize, stepSize, {
        scope,
        includeGarmin: true,
        maxRecordings: 120,
      });
      setData(result);
      if (result.n_windows <= 0) {
        setError(
          "No usable windowed segments were generated. Ingest more RR data or switch scope to the selected tracing.",
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch windowed HRV data");
    } finally {
      setLoading(false);
    }
  }, [userId, windowSize, stepSize, scope]);

  React.useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const trendStats = data?.trend_statistics ?? [];
  const physiologicalCorrelations = data?.physiological_correlations ?? [];
  const hasPhysioSeries =
    (data?.physiological_timestamps?.length ?? 0) > 0 &&
    Object.keys(data?.physiological_series ?? {}).length > 1;
  const hasCorrelationMatrix =
    (data?.correlation_metric_labels?.length ?? 0) >= 2 &&
    (data?.correlation_matrix?.length ?? 0) >= 2;

  return (
    <PageWrapper
      title="Windowed Analysis"
      description="Longitudinal Time-Varying HRV with Trend and Physiology Correlation"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3 flex-wrap">
            {data && (
              <>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {data.n_windows} windows
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Layers className="h-3 w-3" />
                  {data.n_sessions ?? 0} sessions
                </Badge>
                <Badge variant="outline">
                  Scope: {data.source_scope ?? scope}
                </Badge>
                {data.anomaly_indices.length > 0 && (
                  <Badge variant="warning" className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    {data.anomaly_indices.length} anomalies
                  </Badge>
                )}
              </>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Select value={scope} onValueChange={(value) => setScope(value as "all" | "selected")}>
              <SelectTrigger className="h-8 w-[180px]">
                <SelectValue placeholder="Scope" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All ingested tracings</SelectItem>
                <SelectItem value="selected">Selected tracing only</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center gap-1">
              <Settings className="h-4 w-4 text-muted-foreground" />
              <Input
                type="number"
                value={windowSize}
                onChange={(e) => setWindowSize(Math.max(60, Number(e.target.value) || 300))}
                className="w-20 h-8"
                min={60}
                max={600}
                placeholder="Window"
              />
              <span className="text-xs text-muted-foreground">s</span>
            </div>

            <div className="flex items-center gap-1">
              <Input
                type="number"
                value={stepSize}
                onChange={(e) => setStepSize(Math.max(30, Number(e.target.value) || 60))}
                className="w-20 h-8"
                min={30}
                max={300}
                placeholder="Step"
              />
              <span className="text-xs text-muted-foreground">s</span>
            </div>

            <Button onClick={() => void fetchData()} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Analyze
            </Button>
          </div>
        </motion.div>

        {error && (
          <Card className="border-warning">
            <CardContent className="pt-4">
              <p className="text-sm text-warning">{error}</p>
            </CardContent>
          </Card>
        )}

        {data && data.n_windows > 0 && (
          <>
            <QualityPanel context={data.context} />

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-primary" />
                    Longitudinal Multi-Metric Trend
                  </CardTitle>
                  <CardDescription>
                    Window-by-window RMSSD, SDNN, and mean HR trajectory across {data.source_scope === "all" ? "all ingested files" : "the selected tracing"}.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <LongitudinalOverviewChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-success" />
                      RMSSD Dynamics
                    </CardTitle>
                    <CardDescription>
                      Parasympathetic trend with EWMA smoothing and robust anomaly markers.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <SingleMetricChart data={data} metric="rmssd" trend={data.rmssd_ewma} />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      SDNN Dynamics
                    </CardTitle>
                    <CardDescription>
                      Global variability trend with EWMA smoothing and temporal zoom controls.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <SingleMetricChart data={data} metric="sdnn" trend={data.sdnn_ewma} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <GitCompare className="h-5 w-5 text-warning" />
                      Physiological Co-Trends
                    </CardTitle>
                    <CardDescription>
                      Standardized overlays to compare RMSSD against other physiological series over time.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                  {hasPhysioSeries ? (
                    <PhysiologyOverlayChart data={data} />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No synchronized wearable physiology timeline available yet. Sync Garmin metrics to enable co-trend overlays.
                    </p>
                  )}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-info" />
                      Correlation Structure
                    </CardTitle>
                    <CardDescription>
                      Spearman matrix across HRV and wearable physiology metrics (stars indicate statistical significance).
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                  {hasCorrelationMatrix ? (
                    <CorrelationHeatmap
                      labels={data.correlation_metric_labels ?? []}
                      matrix={data.correlation_matrix ?? []}
                      pMatrix={data.correlation_p_values ?? []}
                      qMatrix={data.correlation_q_values ?? []}
                    />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Correlation matrix requires at least two metrics with sufficient overlapping samples.
                    </p>
                  )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-5 w-5 text-primary" />
                    Trend Statistics
                  </CardTitle>
                  <CardDescription>
                    Robust slope, Kendall tau, and baseline-relative drift for key autonomic metrics.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TrendStatisticsCards stats={trendStats} />
                </CardContent>
              </Card>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GitCompare className="h-5 w-5 text-warning" />
                    Top Physiological Associations
                  </CardTitle>
                  <CardDescription>
                    Ranked RMSSD associations with concurrent physiological measures.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <CorrelationInsights correlations={physiologicalCorrelations} />
                </CardContent>
              </Card>
            </motion.div>

            {(data.anomaly_indices.length > 0 || (data.trend_break_indices?.length ?? 0) > 0) && (
              <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      Detected Events
                    </CardTitle>
                    <CardDescription>
                      Robust anomalies (RMSSD outliers) and potential change-points in EWMA trend slope.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {data.anomaly_indices.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {data.anomaly_indices.slice(0, 24).map((idx) => (
                          <Badge key={`a-${idx}`} variant="warning">
                            Anomaly #{idx + 1}: RMSSD {data.rmssd[idx]?.toFixed(1) ?? "—"} ms
                          </Badge>
                        ))}
                      </div>
                    )}
                    {(data.trend_break_indices?.length ?? 0) > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {(data.trend_break_indices ?? []).slice(0, 24).map((idx) => (
                          <Badge key={`b-${idx}`} variant="outline">
                            Trend break near window #{idx + 1}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}

            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 }}>
              <Card>
                <CardHeader>
                  <CardTitle>Methodology Notes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground">
                  <p>
                    • <strong>Windowed HRV:</strong> Sliding windows are computed per tracing, then chronologically merged to produce a longitudinal autonomic timeline across all ingested files.
                  </p>
                  <p>
                    • <strong>Trend model:</strong> EWMA smoothing plus Kendall tau, OLS slope, and robust Theil-Sen slope confidence intervals are used to characterize directionality.
                  </p>
                  <p>
                    • <strong>Physiology coupling:</strong> Correlations use Spearman statistics against wearable physiology (resting HR, sleep duration, SpO2, stress, body battery) with FDR control for multiple comparisons.
                  </p>
                  <p>
                    • <strong>References:</strong> Task Force of ESC/NASPE (1996), Shaffer &amp; Ginsberg (2017), Nunan et al. (2010).
                  </p>
                  {(data.statistical_notes ?? []).map((note, index) => (
                    <p key={`note-${index}`}>
                      • {note}
                    </p>
                  ))}
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>
    </PageWrapper>
  );
}
