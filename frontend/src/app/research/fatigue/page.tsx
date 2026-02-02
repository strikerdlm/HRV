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

// Effectiveness Gauge
function EffectivenessGauge({ effectiveness }: { effectiveness: number | null }) {
  const value = effectiveness ?? 75;
  const hasData = effectiveness !== null;

  const getColor = (e: number) => {
    if (e >= 80) return SCIENTIFIC_COLORS.success;
    if (e >= 60) return SCIENTIFIC_COLORS.warning;
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
              [0.6, SCIENTIFIC_COLORS.danger],
              [0.8, SCIENTIFIC_COLORS.warning],
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
          itemStyle: { borderWidth: 4, borderColor: hasData ? getColor(value) : "#94a3b8", color: "#fff" },
        },
        axisTick: { show: true, splitNumber: 5, length: 10, distance: 8, lineStyle: { color: "#64748b", width: 1 } },
        splitLine: { show: true, length: 20, distance: 8, lineStyle: { color: "#475569", width: 2 } },
        axisLabel: { distance: 40, color: "#1e293b", fontSize: 14, fontWeight: "600" },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? `${Math.round(value)}%` : "—"),
          fontSize: 42,
          fontWeight: "bold",
          color: hasData ? getColor(value) : "#94a3b8",
          offsetCenter: [0, "25%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "55%"],
          fontSize: 14,
          color: SCIENTIFIC_COLORS.textSecondary,
        },
        data: [{ value, name: "Cognitive Effectiveness" }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={320} showToolbox={false} />;
}

// 24-Hour Forecast Chart
function ForecastChart({ data }: { data: FatigueResponse }) {
  const currentHour = new Date().getHours();

  const option: Record<string, unknown> = {
    title: {
      text: "24-Hour Effectiveness Forecast",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 50, right: 30, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: data.forecast_hours.map((h) => {
        const hour = (currentHour + h) % 24;
        return `${hour.toString().padStart(2, "0")}:00`;
      }),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, interval: 3, rotate: 45 },
    },
    yAxis: {
      type: "value",
      name: "Effectiveness %",
      min: 0,
      max: 100,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: data.forecast_effectiveness,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 3, color: SCIENTIFIC_COLORS.primary },
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
        markLine: {
          silent: true,
          data: [
            { yAxis: 60, name: "Threshold", lineStyle: { color: SCIENTIFIC_COLORS.warning, type: "dashed" } },
          ],
        },
        markArea: {
          silent: true,
          data: [
            [
              { xAxis: "02:00", itemStyle: { color: "rgba(231, 76, 60, 0.1)" } },
              { xAxis: "06:00" },
            ],
            [
              { xAxis: "14:00", itemStyle: { color: "rgba(241, 196, 15, 0.1)" } },
              { xAxis: "16:00" },
            ],
          ],
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ name: string; value: number }>;
        if (p[0]) {
          return `${p[0].name}<br/>Effectiveness: ${p[0].value.toFixed(0)}%`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={300} />;
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
  const [loading, setLoading] = React.useState(false);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getFatiguePrediction(userId);
      if (result.forecast_hours.length === 0) {
        // Generate demo data
        const currentHour = new Date().getHours();
        const baseEff = 82;
        const demoData: FatigueResponse = {
          effectiveness_pct: baseEff,
          fatigue_level: "normal",
          forecast_hours: Array.from({ length: 24 }, (_, i) => i),
          forecast_effectiveness: Array.from({ length: 24 }, (_, i) => {
            const hour = (currentHour + i) % 24;
            let circadian = 0;
            if (hour >= 2 && hour <= 6) circadian = -20; // WOCL
            else if (hour >= 14 && hour <= 16) circadian = -8; // Post-lunch
            else if ((hour >= 9 && hour <= 12) || (hour >= 16 && hour <= 20)) circadian = 5;
            return Math.max(0, Math.min(100, baseEff + circadian + (Math.random() - 0.5) * 5));
          }),
          sleep_debt_hours: 2.5,
          optimal_sleep_hours: 8,
          risk_level: "low",
          risk_color: "green",
          recommendations: [
            "Adequate rest levels - normal operations appropriate",
            "Window of Circadian Low (WOCL) predicted 02:00-06:00",
            "Consider strategic napping if needed during afternoon dip",
          ],
          next_optimal_sleep: "22:00",
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
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-warning" />
                      Current Effectiveness
                    </CardTitle>
                    <CardDescription>
                      Cognitive performance capacity based on sleep history
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
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
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sun className="h-5 w-5 text-warning" />
                    24-Hour Forecast
                  </CardTitle>
                  <CardDescription>
                    Predicted effectiveness accounting for circadian rhythm. Red zone = WOCL,
                    Yellow zone = post-lunch dip.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ForecastChart data={data} />
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
                  <CardTitle>SAFTE-FAST Model Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • <strong>SAFTE</strong> (Sleep, Activity, Fatigue, Task Effectiveness) models
                    cognitive effectiveness based on sleep history and circadian phase.
                  </p>
                  <p>
                    • <strong>WOCL</strong> (Window of Circadian Low): 0200-0600 local time represents
                    the period of lowest alertness due to circadian nadir.
                  </p>
                  <p>
                    • <strong>Effectiveness &lt; 70%</strong> is associated with significantly increased
                    error rates in safety-critical tasks.
                  </p>
                  <p>
                    • Hursh SR et al. (2004). Fatigue models for applied research in warfighting.
                    <span className="ml-1 text-primary">Aviat Space Environ Med, 75(3 Suppl), A44-53.</span>
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
