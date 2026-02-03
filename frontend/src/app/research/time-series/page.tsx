// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Heart,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  RefreshCw,
  Clock,
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
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { getHRVTimeSeries } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { RRTimeSeriesResponse, DeviationZone } from "@/types/research";
import { DEVIATION_COLORS } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

function DeviationBadge({ zone }: { zone: DeviationZone }) {
  const color = DEVIATION_COLORS[zone.severity];
  const Icon = zone.direction === "high" ? TrendingUp : TrendingDown;
  
  return (
    <Badge
      variant="outline"
      style={{ borderColor: color, color }}
      className="flex items-center gap-1"
    >
      <Icon className="h-3 w-3" />
      {zone.severity} ({zone.mean_deviation_pct.toFixed(0)}%)
    </Badge>
  );
}

function RRIntervalChart({ data }: { data: RRTimeSeriesResponse }) {
  // Calculate smart interval for x-axis labels to prevent clutter
  const totalBeats = data.total_beats || data.timestamps.length;
  const labelInterval = Math.max(1, Math.ceil(totalBeats / 10) - 1);

  const option: Record<string, unknown> = {
    title: {
      text: "RR Intervals Over Time",
      subtext: `${data.total_beats} beats | ${((data.duration_seconds ?? 0) / 60).toFixed(1)} min`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: { left: 70, right: 30, top: 70, bottom: 70 },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 10 },
    ],
    xAxis: {
      type: "category",
      data: data.timestamps.map((_, i) => i + 1),
      name: "Beat Number",
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval: labelInterval,
        showMinLabel: true,
        showMaxLabel: true,
        fontSize: 11,
      },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: "value",
      name: "RR Interval (ms)",
      nameLocation: "middle",
      nameGap: 50,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: data.rr_ms,
        smooth: false,
        symbol: "none",
        lineStyle: { width: 1, color: SCIENTIFIC_COLORS.primary },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(52, 152, 219, 0.3)" },
              { offset: 1, color: "rgba(52, 152, 219, 0.05)" },
            ],
          },
        },
        markArea: {
          silent: true,
          data: data.deviation_zones.map((zone) => [
            {
              xAxis: zone.start_idx,
              itemStyle: {
                color:
                  zone.severity === "severe"
                    ? "rgba(231, 76, 60, 0.2)"
                    : zone.severity === "moderate"
                      ? "rgba(230, 126, 34, 0.15)"
                      : "rgba(241, 196, 15, 0.1)",
              },
            },
            { xAxis: zone.end_idx },
          ]),
        },
      },
      // Reference bands
      {
        type: "line",
        data: data.rr_ms.map(() => data.age_norm_high),
        lineStyle: { type: "dashed", color: SCIENTIFIC_COLORS.success, width: 1 },
        symbol: "none",
        name: "Upper Normal",
      },
      {
        type: "line",
        data: data.rr_ms.map(() => data.age_norm_low),
        lineStyle: { type: "dashed", color: SCIENTIFIC_COLORS.success, width: 1 },
        symbol: "none",
        name: "Lower Normal",
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ value: number; dataIndex: number }>;
        if (p[0]) {
          return `Beat ${p[0].dataIndex + 1}<br/>RR: ${p[0].value.toFixed(1)} ms<br/>HR: ${(60000 / p[0].value).toFixed(1)} bpm`;
        }
        return "";
      },
    },
    legend: {
      show: true,
      bottom: 35,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
  };

  return <EChartsWrapper option={option} height={400} />;
}

function HeartRateChart({ data }: { data: RRTimeSeriesResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "Derived Heart Rate",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 50 },
    xAxis: {
      type: "category",
      data: data.timestamps.map((_, i) => i + 1),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, show: false },
    },
    yAxis: {
      type: "value",
      name: "HR (bpm)",
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: data.hr_bpm,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.danger },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(231, 76, 60, 0.3)" },
              { offset: 1, color: "rgba(231, 76, 60, 0.05)" },
            ],
          },
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ value: number }>;
        if (p[0]) {
          return `HR: ${p[0].value.toFixed(1)} bpm`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={200} />;
}

function PercentileChart({ data }: { data: RRTimeSeriesResponse }) {
  const percentiles = data.percentiles;

  const option: Record<string, unknown> = {
    title: {
      text: "RR Interval Distribution",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: ["P5", "P25", "P50", "P75", "P95"],
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: "RR (ms)",
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "bar",
        data: [
          { value: percentiles.p5 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.warning } },
          { value: percentiles.p25 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.info } },
          { value: percentiles.p50 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.success } },
          { value: percentiles.p75 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.info } },
          { value: percentiles.p95 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.warning } },
        ],
        barWidth: "60%",
        label: {
          show: true,
          position: "top",
          color: SCIENTIFIC_COLORS.textPrimary,
          formatter: (p: { value: number }) => p.value.toFixed(0),
        },
      },
    ],
    tooltip: {
      trigger: "axis",
    },
  };

  return <EChartsWrapper option={option} height={250} />;
}

function StatCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
}: {
  title: string;
  value: number | null;
  unit: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(1) : "—"}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
    </div>
  );
}

export default function TimeSeriesPage() {
  const [data, setData] = React.useState<RRTimeSeriesResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getHRVTimeSeries(userId, 2000);
      if (result.total_beats === 0) {
        // Generate demo data
        const demoData: RRTimeSeriesResponse = {
          timestamps: Array.from({ length: 500 }, (_, i) =>
            new Date(Date.now() + i * 900).toISOString()
          ),
          rr_ms: Array.from({ length: 500 }, () => 850 + Math.random() * 200 - 100),
          hr_bpm: [],
          deviation_zones: [
            { start_idx: 120, end_idx: 145, start_time: null, end_time: null, severity: "mild", direction: "high", mean_deviation_pct: 15 },
            { start_idx: 280, end_idx: 310, start_time: null, end_time: null, severity: "moderate", direction: "low", mean_deviation_pct: 25 },
          ],
          mean_rr: 870,
          std_rr: 58,
          min_rr: 720,
          max_rr: 1050,
          total_beats: 500,
          duration_seconds: 450,
          percentiles: { p5: 780, p25: 830, p50: 870, p75: 910, p95: 980 },
          age_norm_mean: 850,
          age_norm_low: 700,
          age_norm_high: 1000,
        };
        demoData.hr_bpm = demoData.rr_ms.map((rr) => 60000 / rr);
        setData(demoData);
      } else {
        setData(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Time Series Analysis"
      description="RR Interval Visualization with Deviation Detection"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            {data && (
              <>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Heart className="h-3 w-3" />
                  {data.total_beats} beats
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {((data.duration_seconds ?? 0) / 60).toFixed(1)} min
                </Badge>
                {data.deviation_zones.length > 0 && (
                  <Badge variant="warning" className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    {data.deviation_zones.length} deviations
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

        {error && (
          <Card className="border-danger">
            <CardContent className="pt-4">
              <p className="text-danger">{error}</p>
            </CardContent>
          </Card>
        )}

        {data && (
          <>
            {/* Summary Stats */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <StatCard
                title="Mean RR"
                value={data.mean_rr}
                unit="ms"
                icon={Activity}
                color="text-primary"
              />
              <StatCard
                title="Std Dev"
                value={data.std_rr}
                unit="ms"
                icon={BarChart3}
                color="text-info"
              />
              <StatCard
                title="Min RR"
                value={data.min_rr}
                unit="ms"
                icon={TrendingDown}
                color="text-warning"
              />
              <StatCard
                title="Max RR"
                value={data.max_rr}
                unit="ms"
                icon={TrendingUp}
                color="text-success"
              />
            </motion.div>

            {/* Main RR Chart */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    RR Interval Time Series
                  </CardTitle>
                  <CardDescription>
                    Interbeat intervals with highlighted deviation zones. Green dashed
                    lines show age-stratified normal range.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <RRIntervalChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Secondary Charts */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Heart className="h-5 w-5 text-danger" />
                      Heart Rate
                    </CardTitle>
                    <CardDescription>
                      Instantaneous heart rate derived from RR intervals
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <HeartRateChart data={data} />
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-info" />
                      Percentile Distribution
                    </CardTitle>
                    <CardDescription>
                      RR interval distribution percentiles (P5-P95)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <PercentileChart data={data} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Deviation Zones */}
            {data.deviation_zones.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      Detected Deviation Zones
                    </CardTitle>
                    <CardDescription>
                      Periods with significant deviation from baseline (robust z-score &gt; 2)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {data.deviation_zones.map((zone, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg border bg-card flex items-center gap-3"
                        >
                          <DeviationBadge zone={zone} />
                          <span className="text-sm text-muted-foreground">
                            Beats {zone.start_idx}–{zone.end_idx}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Scientific Note */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Interpretation Guide</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • <strong>RR Intervals:</strong> Time between consecutive heartbeats.
                    Higher values indicate slower heart rate.
                  </p>
                  <p>
                    • <strong>Deviation Zones:</strong> Identified using robust z-scores
                    (MAD-based). Yellow = mild, Orange = moderate, Red = severe.
                  </p>
                  <p>
                    • <strong>Reference:</strong> Task Force (1996). Heart rate variability:
                    standards of measurement. <em>Circulation, 93(5), 1043-1065.</em>
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
