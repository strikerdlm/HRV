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

// Readiness Score Gauge
function ReadinessGauge({ score }: { score: number | null }) {
  const value = score ?? 50;
  const hasData = score !== null;

  const getColor = (s: number) => {
    if (s >= 70) return SCIENTIFIC_COLORS.success;
    if (s >= 40) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "60%"],
        radius: "90%",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 30,
            color: [
              [0.4, SCIENTIFIC_COLORS.danger],
              [0.7, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.success],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "55%",
          width: 8,
          offsetCenter: [0, "-5%"],
          itemStyle: { color: hasData ? getColor(value) : "#94a3b8" },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 25,
          itemStyle: {
            borderWidth: 4,
            borderColor: hasData ? getColor(value) : "#94a3b8",
            color: "#fff",
          },
        },
        axisTick: { show: true, splitNumber: 5, length: 10, distance: 8, lineStyle: { color: "#64748b", width: 1 } },
        splitLine: { show: true, length: 20, distance: 8, lineStyle: { color: "#475569", width: 2 } },
        axisLabel: { distance: 40, color: "#1e293b", fontSize: 14, fontWeight: "600" },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? Math.round(value).toString() : "—"),
          fontSize: 48,
          fontWeight: "bold",
          color: hasData ? getColor(value) : "#94a3b8",
          offsetCenter: [0, "25%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 16,
          color: SCIENTIFIC_COLORS.textSecondary,
        },
        data: [{ value, name: "Readiness Score" }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={320} showToolbox={false} />;
}

// Trend Sparkline
function TrendChart({ data }: { data: ReadinessResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "7-Day Trend",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 50, right: 20, top: 50, bottom: 30 },
    xAxis: {
      type: "category",
      data: data.trend_dates,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        fontSize: 10,
        interval: Math.max(0, Math.ceil(data.trend_dates.length / 7) - 1),
        rotate: data.trend_dates.length > 10 ? 45 : 0,
        align: data.trend_dates.length > 10 ? "right" : "center",
        showMinLabel: true,
        showMaxLabel: true,
      },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: "value",
      name: "ln(RMSSD)",
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    series: [
      {
        type: "line",
        data: data.trend_7day,
        smooth: true,
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { width: 3, color: SCIENTIFIC_COLORS.primary },
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(52, 152, 219, 0.4)" },
              { offset: 1, color: "rgba(52, 152, 219, 0.05)" },
            ],
          },
        },
        markLine: data.baseline
          ? {
              silent: true,
              data: [{ yAxis: Math.log(data.baseline), name: "Baseline" }],
              lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dashed", width: 2 },
              label: { formatter: "Baseline", color: SCIENTIFIC_COLORS.success },
            }
          : undefined,
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ name: string; value: number }>;
        if (p[0]) {
          return `${p[0].name}<br/>ln(RMSSD): ${p[0].value.toFixed(2)}`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={220} />;
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
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Target className="h-5 w-5 text-primary" />
                      Readiness Score
                    </CardTitle>
                    <CardDescription>
                      Based on lnRMSSD vs. 7-day rolling baseline
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
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
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-info" />
                      Weekly Trend
                    </CardTitle>
                    <CardDescription>
                      ln(RMSSD) over the past 7 days with baseline reference
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
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
