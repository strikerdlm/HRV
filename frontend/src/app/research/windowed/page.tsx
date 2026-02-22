// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Layers,
  Activity,
  RefreshCw,
  Settings,
  TrendingUp,
  AlertTriangle,
  Clock,
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
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { QualityPanel } from "@/components/research/quality-panel";
import { getHRVWindowed } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { WindowedMetricsResponse } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

// Multi-line time series chart
function WindowedChart({ data, metric }: { data: WindowedMetricsResponse; metric: "rmssd" | "sdnn" | "lf_hf_ratio" }) {
  const values = data[metric] as (number | null)[];
  const ewma = metric === "rmssd" ? data.rmssd_ewma : metric === "sdnn" ? data.sdnn_ewma : [];
  
  const metricInfo = {
    rmssd: { name: "RMSSD", unit: "ms", color: SCIENTIFIC_COLORS.success },
    sdnn: { name: "SDNN", unit: "ms", color: SCIENTIFIC_COLORS.primary },
    lf_hf_ratio: { name: "LF/HF", unit: "", color: SCIENTIFIC_COLORS.warning },
  };

  const info = metricInfo[metric];
  
  // Calculate optimal label interval - show max 8 labels for clean display
  const numWindows = data.timestamps.length;
  const labelInterval = Math.max(0, Math.ceil(numWindows / 8) - 1);

  const option: Record<string, unknown> = {
    title: {
      text: `${info.name} Over Time`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 70 },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 5 },
    ],
    xAxis: {
      type: "category",
      data: data.timestamps.map((_, i) => i + 1),
      name: "Window",
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval: labelInterval,
        showMinLabel: true,
        showMaxLabel: true,
        fontSize: 11,
        hideOverlap: true,
      },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      axisTick: { alignWithLabel: true, interval: labelInterval },
    },
    yAxis: {
      type: "value",
      name: `${info.name} (${info.unit})`,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        name: info.name,
        data: values,
        smooth: false,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 1.5, color: info.color },
        itemStyle: { color: info.color },
        markPoint: {
          data: data.anomaly_indices.map((idx) => ({
            coord: [idx, values[idx]],
            symbol: "pin",
            symbolSize: 30,
            itemStyle: { color: SCIENTIFIC_COLORS.danger },
          })),
        },
      },
      ...(ewma.length > 0
        ? [
            {
              type: "line",
              name: "EWMA Trend",
              data: ewma,
              smooth: true,
              symbol: "none",
              lineStyle: { width: 2, color: SCIENTIFIC_COLORS.danger, type: "dashed" as const },
            },
          ]
        : []),
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ seriesName: string; value: number; dataIndex: number }>;
        let result = `Window ${p[0]?.dataIndex + 1}<br/>`;
        p.forEach((item) => {
          if (item.value !== null) {
            result += `${item.seriesName}: ${item.value.toFixed(2)} ${info.unit}<br/>`;
          }
        });
        return result;
      },
    },
    legend: {
      top: 25,
      right: 10,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
  };

  return <EChartsWrapper option={option} height={300} />;
}

// Combined metrics chart
function CombinedChart({ data }: { data: WindowedMetricsResponse }) {
  // Calculate optimal label interval - show max 10 labels for wider chart
  const numWindows = data.timestamps.length;
  const labelInterval = Math.max(0, Math.ceil(numWindows / 10) - 1);

  const option: Record<string, unknown> = {
    title: {
      text: "All Metrics Overview",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 60, top: 50, bottom: 70 },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 5 },
    ],
    xAxis: {
      type: "category",
      data: data.timestamps.map((_, i) => i + 1),
      name: "Window",
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval: labelInterval,
        showMinLabel: true,
        showMaxLabel: true,
        fontSize: 11,
        hideOverlap: true,
      },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      axisTick: { alignWithLabel: true, interval: labelInterval },
    },
    yAxis: [
      {
        type: "value",
        name: "ms",
        position: "left",
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
      {
        type: "value",
        name: "bpm / ratio",
        position: "right",
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
    ],
    series: [
      {
        type: "line",
        name: "RMSSD",
        data: data.rmssd,
        yAxisIndex: 0,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.success },
      },
      {
        type: "line",
        name: "SDNN",
        data: data.sdnn,
        yAxisIndex: 0,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.primary },
      },
      {
        type: "line",
        name: "Mean HR",
        data: data.mean_hr,
        yAxisIndex: 1,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.danger },
      },
    ],
    tooltip: { trigger: "axis" },
    legend: {
      top: 25,
      right: 10,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
  };

  return <EChartsWrapper option={option} height={350} />;
}

export default function WindowedPage() {
  const [data, setData] = React.useState<WindowedMetricsResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [windowSize, setWindowSize] = React.useState(300);
  const [stepSize, setStepSize] = React.useState(60);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getHRVWindowed(userId, windowSize, stepSize);
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [userId, windowSize, stepSize]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Windowed Analysis"
      description="Time-Varying HRV with Trend Detection"
    >
      <div className="space-y-6">
        {/* Header with Config */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            {data && (
              <>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {data.n_windows} windows
                </Badge>
                <Badge variant="outline">
                  Window: {data.window_size_seconds}s
                </Badge>
                <Badge variant="outline">
                  Step: {data.step_size_seconds}s
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
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <Settings className="h-4 w-4 text-muted-foreground" />
              <Input
                type="number"
                value={windowSize}
                onChange={(e) => setWindowSize(Number(e.target.value))}
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
                onChange={(e) => setStepSize(Number(e.target.value))}
                className="w-20 h-8"
                min={30}
                max={300}
                placeholder="Step"
              />
              <span className="text-xs text-muted-foreground">s</span>
            </div>
            <Button onClick={fetchData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Analyze
            </Button>
          </div>
        </motion.div>

        {data && (
          <>
            <QualityPanel context={data.context} />

            {/* Combined Overview */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-5 w-5 text-primary" />
                    Multi-Metric Overview
                  </CardTitle>
                  <CardDescription>
                    RMSSD, SDNN, and Heart Rate across all windows
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <CombinedChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Individual Metrics */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-success" />
                      RMSSD Trend
                    </CardTitle>
                    <CardDescription>
                      Parasympathetic activity with EWMA smoothing (red dashed)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <WindowedChart data={data} metric="rmssd" />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      SDNN Trend
                    </CardTitle>
                    <CardDescription>
                      Overall HRV with EWMA smoothing (red dashed)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <WindowedChart data={data} metric="sdnn" />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Anomaly List */}
            {data.anomaly_indices.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      Detected Anomalies
                    </CardTitle>
                    <CardDescription>
                      Windows with significant deviation from trend (z-score &gt; 2)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {data.anomaly_indices.map((idx) => (
                        <Badge key={idx} variant="warning">
                          Window {idx + 1}: RMSSD = {data.rmssd[idx]?.toFixed(1) ?? "—"} ms
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* References */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Methodology Notes</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • <strong>Windowed analysis</strong> computes HRV metrics over sliding windows
                    to reveal temporal dynamics and physiological state changes.
                  </p>
                  <p>
                    • <strong>EWMA (Exponential Weighted Moving Average)</strong> smooths the signal
                    to highlight underlying trends. α = 0.2 (7-window effective span).
                  </p>
                  <p>
                    • <strong>Anomaly detection</strong> flags windows where RMSSD deviates &gt;2 standard
                    deviations from the rolling mean, suggesting unusual autonomic states.
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>
    </PageWrapper>
  );
}
