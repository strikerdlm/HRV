// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Heart,
  Activity,
  Zap,
  CheckCircle,
  AlertCircle,
  XCircle,
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
import { getReadiness } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { ReadinessResponse, ReadinessComponent } from "@/types/research";
import { READINESS_COLORS } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

// Readiness Score Gauge - Clean minimal design following plot rules
function ReadinessGauge({ score }: { score: number | null }) {
  const value = score ?? 50;
  const hasData = score !== null;

  const getColor = (s: number) => {
    if (s >= 70) return SCIENTIFIC_COLORS.success;
    if (s >= 40) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const getLabel = (s: number) => {
    if (s >= 70) return "Ready";
    if (s >= 40) return "Moderate";
    return "Rest";
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
            width: 20,
            color: [
              [0.4, SCIENTIFIC_COLORS.danger],
              [0.7, SCIENTIFIC_COLORS.warning],
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
            // Only show key values: 0, 40, 70, 100
            if ([0, 40, 70, 100].includes(v)) return v.toString();
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
          formatter: () => (hasData ? Math.round(value).toString() : "—"),
          fontSize: 42,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? getColor(value) : "#94a3b8",
          offsetCenter: [0, "30%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 14,
          fontWeight: "500",
          color: SCIENTIFIC_COLORS.textSecondary,
        },
        data: [{ value, name: hasData ? getLabel(value) : "No Data" }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={280} showToolbox={false} />;
}

// Trend Chart - Clean design following plot rules (no title in chart, use CardHeader)
function TrendChart({ data }: { data: ReadinessResponse }) {
  // Calculate dynamic Y-axis bounds
  const validValues = data.trend_7day.filter((v): v is number => v !== null && !isNaN(v));
  const dataMin = validValues.length > 0 ? Math.min(...validValues) : 3;
  const dataMax = validValues.length > 0 ? Math.max(...validValues) : 4;
  const padding = (dataMax - dataMin) * 0.15 || 0.2;

  const option: Record<string, unknown> = {
    grid: {
      left: 45,
      right: 15,
      top: 20,
      bottom: 30,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: data.trend_dates,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 11,
        interval: 0, // Show all labels for 7-day data
      },
      axisLine: { lineStyle: { color: "#2c3e50" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "ln(RMSSD)",
      nameLocation: "middle",
      nameGap: 30,
      nameTextStyle: { color: "#1a1a1a", fontSize: 11, fontWeight: "bold" },
      min: Math.floor((dataMin - padding) * 10) / 10,
      max: Math.ceil((dataMax + padding) * 10) / 10,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        formatter: (v: number) => v.toFixed(1),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "rgba(44, 62, 80, 0.1)", type: "dashed" } },
    },
    series: [
      {
        type: "line",
        data: data.trend_7day,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2.5, color: SCIENTIFIC_COLORS.primary },
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(52, 152, 219, 0.25)" },
              { offset: 1, color: "rgba(52, 152, 219, 0)" },
            ],
          },
        },
        markLine: data.baseline
          ? {
              silent: true,
              symbol: "none",
              data: [{ yAxis: Math.log(data.baseline) }],
              lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dashed", width: 1.5 },
              label: { formatter: "Baseline", fontSize: 10, color: SCIENTIFIC_COLORS.success, position: "end" },
            }
          : undefined,
      },
    ],
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: "#1a1a1a", fontSize: 12 },
      formatter: (params: unknown[]) => {
        const p = params as Array<{ name: string; value: number }>;
        if (p[0] && p[0].value !== null) {
          return `<b>${p[0].name}</b><br/>ln(RMSSD): ${p[0].value.toFixed(2)}`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={200} showToolbox={false} />;
}

// Component Card
function ComponentCard({ component }: { component: ReadinessComponent }) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "good":
        return <CheckCircle className="h-4 w-4 text-success" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      case "poor":
        return <XCircle className="h-4 w-4 text-danger" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "good":
        return "border-success/30 bg-success/5";
      case "warning":
        return "border-warning/30 bg-warning/5";
      case "poor":
        return "border-danger/30 bg-danger/5";
      default:
        return "";
    }
  };

  return (
    <div className={`p-4 rounded-lg border ${getStatusColor(component.status)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">{component.name}</span>
        {getStatusIcon(component.status)}
      </div>
      <p className="text-2xl font-bold">{component.value.toFixed(1)}</p>
      <div className="flex items-center gap-2 mt-2">
        <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full rounded-full ${
              component.status === "good"
                ? "bg-success"
                : component.status === "warning"
                  ? "bg-warning"
                  : "bg-danger"
            }`}
            style={{ width: `${Math.min(component.contribution * 100, 100)}%` }}
          />
        </div>
        <span className="text-xs text-muted-foreground">
          {(component.weight * 100).toFixed(0)}% weight
        </span>
      </div>
    </div>
  );
}

export default function ReadinessPage() {
  const [data, setData] = React.useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getReadiness(userId);
      if (result.score === null) {
        // Generate demo data
        const demoData: ReadinessResponse = {
          score: 72,
          baseline: 45,
          deviation_from_baseline: 0.08,
          trend_direction: "improving",
          trend_7day: [3.6, 3.65, 3.7, 3.68, 3.75, 3.8, 3.82],
          trend_dates: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          components: [
            { name: "RMSSD", value: 45, weight: 0.4, contribution: 0.36, status: "good" },
            { name: "HF Power", value: 580, weight: 0.3, contribution: 0.25, status: "good" },
            { name: "Sleep Quality", value: 78, weight: 0.2, contribution: 0.16, status: "warning" },
            { name: "Recovery Index", value: 65, weight: 0.1, contribution: 0.08, status: "good" },
          ],
          readiness_status: "ready",
          recommendations: [
            "High readiness - appropriate for intense training",
            "lnRMSSD trend is improving over the past week",
            "Consider maintaining current recovery practices",
          ],
        };
        setData(demoData);
      } else {
        setData(result);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case "improving":
        return <TrendingUp className="h-4 w-4 text-success" />;
      case "declining":
        return <TrendingDown className="h-4 w-4 text-danger" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <PageWrapper
      title="Readiness Dashboard"
      description="Training Readiness Based on HRV Baseline"
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
                    borderColor: READINESS_COLORS[data.readiness_status],
                    color: READINESS_COLORS[data.readiness_status],
                  }}
                  className="flex items-center gap-1"
                >
                  <Target className="h-3 w-3" />
                  {data.readiness_status === "ready"
                    ? "Ready"
                    : data.readiness_status === "moderate"
                      ? "Moderate"
                      : "Rest Recommended"}
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  {getTrendIcon(data.trend_direction)}
                  {data.trend_direction.charAt(0).toUpperCase() + data.trend_direction.slice(1)}
                </Badge>
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
            {/* Main Gauge and Trend */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Target className="h-5 w-5 text-primary" />
                      Readiness Score
                    </CardTitle>
                    <CardDescription className="text-xs">
                      0-100 scale based on lnRMSSD vs. 7-day baseline. Green=ready, Yellow=moderate, Red=rest.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ReadinessGauge score={data.score} />
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="text-center p-3 rounded-lg border">
                        <p className="text-xs text-muted-foreground">Baseline RMSSD</p>
                        <p className="text-xl font-bold">{data.baseline?.toFixed(1) ?? "—"} ms</p>
                      </div>
                      <div className="text-center p-3 rounded-lg border">
                        <p className="text-xs text-muted-foreground">Deviation</p>
                        <p className="text-xl font-bold">
                          {data.deviation_from_baseline !== null
                            ? `${data.deviation_from_baseline > 0 ? "+" : ""}${(data.deviation_from_baseline * 100).toFixed(0)}%`
                            : "—"}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="h-full">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <TrendingUp className="h-5 w-5 text-info" />
                      7-Day Trend
                    </CardTitle>
                    <CardDescription className="text-xs">
                      ln(RMSSD) trend with baseline reference. Higher = better recovery.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <TrendChart data={data} />
                    <div className="p-3 rounded-lg bg-muted/50 mt-4">
                      <p className="text-sm">
                        <strong>Trend Analysis:</strong>{" "}
                        {data.trend_direction === "improving"
                          ? "Your HRV is improving, indicating good recovery and adaptation."
                          : data.trend_direction === "declining"
                            ? "Your HRV is declining, consider additional recovery time."
                            : "Your HRV is stable within normal variation."}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Components */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-success" />
                    Score Components
                  </CardTitle>
                  <CardDescription>
                    Individual metrics contributing to readiness score
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {data.components.map((comp) => (
                      <ComponentCard key={comp.name} component={comp} />
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Recommendations */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-warning" />
                    Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {data.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span
                          className={
                            data.readiness_status === "ready"
                              ? "text-success"
                              : data.readiness_status === "moderate"
                                ? "text-warning"
                                : "text-danger"
                          }
                        >
                          •
                        </span>
                        <span className="text-sm text-muted-foreground">{rec}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

            {/* References */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Scientific Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • <strong>Readiness scoring</strong> is based on the lnRMSSD approach, which uses
                    the natural logarithm of RMSSD to stabilize variance.
                  </p>
                  <p>
                    • <strong>Smallest Worthwhile Change (SWC)</strong>: Deviations ≥ 0.5 × CV × baseline
                    are considered meaningful (Plews et al. 2013).
                  </p>
                  <p>
                    • Plews DJ et al. (2013). Training Adaptation and Heart Rate Variability in Elite
                    Endurance Athletes.
                    <span className="ml-1 text-primary">Int J Sports Physiol Perform, 8(6), 688-691.</span>
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
