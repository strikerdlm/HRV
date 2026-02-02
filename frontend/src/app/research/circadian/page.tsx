// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Clock,
  Sun,
  Moon,
  Sunrise,
  Sunset,
  RefreshCw,
  Lightbulb,
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
import { getCircadianAnalysis } from "@/lib/research-api";
import type { CircadianResponse } from "@/types/research";

const DEMO_USER_ID = "demo-user";

// Circadian Clock Visualization
function CircadianClock({ data }: { data: CircadianResponse }) {
  const currentHour = data.phase_angle_hours ?? new Date().getHours();

  const option: Record<string, unknown> = {
    polar: { radius: "75%" },
    angleAxis: {
      type: "value",
      min: 0,
      max: 24,
      startAngle: 90,
      clockwise: true,
      splitNumber: 24,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        formatter: (val: number) => (val === 24 ? "0" : val.toString().padStart(2, "0")),
        color: SCIENTIFIC_COLORS.textPrimary,
      },
      splitLine: {
        show: true,
        lineStyle: { color: "rgba(100,100,100,0.2)" },
      },
    },
    radiusAxis: {
      type: "value",
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false },
    },
    series: [
      // Alertness area
      {
        type: "bar",
        coordinateSystem: "polar",
        data: data.hours.map((h, i) => ({
          value: [data.alertness_level[i], h + 0.5],
          itemStyle: {
            color:
              data.alertness_level[i] >= 70
                ? SCIENTIFIC_COLORS.success
                : data.alertness_level[i] >= 50
                  ? SCIENTIFIC_COLORS.warning
                  : SCIENTIFIC_COLORS.danger,
            opacity: 0.7,
          },
        })),
        barWidth: "100%",
      },
      // Current time marker
      {
        type: "line",
        coordinateSystem: "polar",
        data: [
          [0, currentHour],
          [100, currentHour],
        ],
        lineStyle: { width: 3, color: SCIENTIFIC_COLORS.primary },
        symbol: "none",
      },
    ],
    tooltip: {
      trigger: "item",
      formatter: (params: { value: [number, number] }) =>
        `${Math.floor(params.value[1]).toString().padStart(2, "0")}:00<br/>Alertness: ${params.value[0].toFixed(0)}%`,
    },
  };

  return <EChartsWrapper option={option} height={400} showToolbox={false} />;
}

// Alertness Timeline
function AlertnessTimeline({ data }: { data: CircadianResponse }) {
  const currentHour = new Date().getHours();

  const option: Record<string, unknown> = {
    title: {
      text: "24-Hour Alertness Profile",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 50, right: 30, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: data.hours.map((h) => `${h.toString().padStart(2, "0")}:00`),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, interval: 3, rotate: 45 },
    },
    yAxis: {
      type: "value",
      name: "Alertness %",
      min: 0,
      max: 100,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: data.alertness_level,
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
            { xAxis: `${currentHour.toString().padStart(2, "0")}:00`, lineStyle: { color: SCIENTIFIC_COLORS.danger, width: 2, type: "solid" } },
          ],
          label: { formatter: "Now", color: SCIENTIFIC_COLORS.danger },
        },
        markArea: {
          silent: true,
          data: [
            [
              { xAxis: "02:00", itemStyle: { color: "rgba(231, 76, 60, 0.15)" } },
              { xAxis: "06:00" },
            ],
            [
              { xAxis: data.optimal_performance_start ?? "09:00", itemStyle: { color: "rgba(39, 174, 96, 0.15)" } },
              { xAxis: data.optimal_performance_end ?? "12:00" },
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
          return `${p[0].name}<br/>Alertness: ${p[0].value.toFixed(0)}%`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={280} />;
}

// Phase Icon
function PhaseIcon({ phase }: { phase: string }) {
  switch (phase) {
    case "morning":
      return <Sunrise className="h-8 w-8 text-warning" />;
    case "day":
      return <Sun className="h-8 w-8 text-warning" />;
    case "evening":
      return <Sunset className="h-8 w-8 text-orange-500" />;
    case "night":
      return <Moon className="h-8 w-8 text-info" />;
    default:
      return <Sun className="h-8 w-8" />;
  }
}

export default function CircadianPage() {
  const [data, setData] = React.useState<CircadianResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getCircadianAnalysis(DEMO_USER_ID);
      if (result.hours.length === 0) {
        // Generate demo data
        const hours = Array.from({ length: 24 }, (_, i) => i);
        const alertness = hours.map((h) => {
          const circadian = 50 + 30 * Math.cos((2 * Math.PI * (h - 16)) / 24);
          const homeostatic = Math.max(0, 100 - ((h - 7 + 24) % 24) * 5);
          return Math.max(0, Math.min(100, circadian * 0.6 + homeostatic * 0.4));
        });

        const demoData: CircadianResponse = {
          current_phase: new Date().getHours() < 6 ? "night" : new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "day" : "evening",
          phase_angle_hours: new Date().getHours(),
          optimal_performance_start: "09:00",
          optimal_performance_end: "12:00",
          optimal_sleep_start: "22:00",
          hours,
          alertness_level: alertness,
          light_exposure_lux: 450,
          light_recommendation: "Consider bright light exposure (>1000 lux) in the morning to reinforce circadian rhythm",
          chronotype: "intermediate",
          notes: [
            "Circadian rhythm follows ~24-hour cycle regulated by suprachiasmatic nucleus",
            "Light exposure in morning helps maintain rhythm alignment",
            "Avoid bright light 2 hours before intended sleep time",
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
  }, []);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Circadian Analysis"
      description="Sleep-Wake Cycle and Optimal Activity Windows"
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
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {data.current_phase.charAt(0).toUpperCase() + data.current_phase.slice(1)} Phase
                </Badge>
                <Badge variant="outline">
                  Chronotype: {data.chronotype}
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
            {/* Clock and Status */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5 text-primary" />
                      Circadian Clock
                    </CardTitle>
                    <CardDescription>
                      24-hour alertness profile with current time marker
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CircadianClock data={data} />
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
                      <Activity className="h-5 w-5 text-success" />
                      Current Status
                    </CardTitle>
                    <CardDescription>
                      Phase and optimal activity windows
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 mb-6 p-4 rounded-lg bg-muted/50">
                      <PhaseIcon phase={data.current_phase} />
                      <div>
                        <p className="text-lg font-bold">
                          {data.current_phase.charAt(0).toUpperCase() + data.current_phase.slice(1)} Phase
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {data.phase_angle_hours !== null
                            ? `${data.phase_angle_hours.toFixed(0)}:00 local time`
                            : "—"}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-lg border bg-success/10 border-success/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Sun className="h-4 w-4 text-success" />
                          <span className="text-sm font-medium">Peak Performance</span>
                        </div>
                        <p className="text-xl font-bold">
                          {data.optimal_performance_start} - {data.optimal_performance_end}
                        </p>
                      </div>
                      <div className="p-4 rounded-lg border bg-info/10 border-info/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Moon className="h-4 w-4 text-info" />
                          <span className="text-sm font-medium">Optimal Sleep</span>
                        </div>
                        <p className="text-xl font-bold">{data.optimal_sleep_start ?? "—"}</p>
                      </div>
                    </div>

                    {data.light_exposure_lux !== null && (
                      <div className="mt-4 p-3 rounded-lg border">
                        <div className="flex items-center gap-2 mb-1">
                          <Lightbulb className="h-4 w-4 text-warning" />
                          <span className="text-sm font-medium">Light Exposure</span>
                        </div>
                        <p className="text-lg font-bold">{data.light_exposure_lux} lux</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {data.light_recommendation}
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Alertness Timeline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Alertness Timeline
                  </CardTitle>
                  <CardDescription>
                    Green zone = peak performance window, Red zone = circadian low (WOCL)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <AlertnessTimeline data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Notes */}
            {data.notes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Lightbulb className="h-5 w-5 text-warning" />
                      Circadian Tips
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {data.notes.map((note, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-warning">•</span>
                          <span className="text-sm text-muted-foreground">{note}</span>
                        </li>
                      ))}
                    </ul>
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
                  <CardTitle>Scientific Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • <strong>Two-Process Model:</strong> Alertness is governed by Process C (circadian)
                    and Process S (homeostatic sleep pressure) - Borbély AA, 1982.
                  </p>
                  <p>
                    • <strong>Suprachiasmatic Nucleus (SCN):</strong> Master circadian pacemaker in
                    hypothalamus, synchronized primarily by light exposure.
                  </p>
                  <p>
                    • <strong>Light Therapy:</strong> Morning bright light (&gt;1000 lux) advances
                    circadian phase; evening light delays it.
                  </p>
                  <p>
                    • Czeisler CA et al. (1999). Stability, precision, and near-24-hour period of the
                    human circadian pacemaker.
                    <span className="ml-1 text-primary">Science, 284(5423), 2177-81.</span>
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
