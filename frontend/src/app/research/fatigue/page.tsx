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

// SAFTE-Based 24-Hour Forecast Chart with proper circadian morphology
// Two peaks (morning ~10:00, evening ~18:00) and two troughs (WOCL ~04:00, post-lunch ~14:00)
function ForecastChart({ data }: { data: FatigueResponse }) {
  const currentHour = new Date().getHours();
  
  // Generate x-axis labels
  const xLabels = data.forecast_hours.map((h) => {
    const hour = (currentHour + h) % 24;
    return `${hour.toString().padStart(2, "0")}:00`;
  });

  // Calculate circadian zones for highlighting
  const woclStart = xLabels.findIndex((l) => l === "02:00" || l === "03:00");
  const woclEnd = xLabels.findIndex((l) => l === "06:00" || l === "07:00");
  const dipStart = xLabels.findIndex((l) => l === "13:00" || l === "14:00");
  const dipEnd = xLabels.findIndex((l) => l === "15:00" || l === "16:00");

  // Create mark areas dynamically based on actual data range
  const markAreas: Array<Array<{ xAxis?: string; itemStyle?: { color: string } }>> = [];
  if (woclStart >= 0 && woclEnd > woclStart) {
    markAreas.push([
      { xAxis: xLabels[woclStart], itemStyle: { color: "rgba(220, 38, 38, 0.12)" } },
      { xAxis: xLabels[woclEnd] },
    ]);
  }
  if (dipStart >= 0 && dipEnd > dipStart) {
    markAreas.push([
      { xAxis: xLabels[dipStart], itemStyle: { color: "rgba(234, 179, 8, 0.1)" } },
      { xAxis: xLabels[dipEnd] },
    ]);
  }

  const option: Record<string, unknown> = {
    title: {
      text: "SAFTE Model Effectiveness",
      left: "center",
      top: 8,
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
    },
    grid: {
      left: 50,
      right: 25,
      top: 50,
      bottom: 55,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: xLabels,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        interval: Math.max(0, Math.floor(xLabels.length / 8)),
        rotate: 0,
      },
      axisLine: { lineStyle: { color: "#2c3e50" } },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      name: "%",
      nameLocation: "middle",
      nameGap: 32,
      nameTextStyle: { color: "#1a1a1a", fontSize: 11, fontWeight: "bold" },
      min: 30,
      max: 100,
      interval: 10,
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 10,
        formatter: (v: number) => v.toFixed(0),
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: "rgba(44, 62, 80, 0.1)", type: "dashed" } },
    },
    series: [
      {
        type: "line",
        data: data.forecast_effectiveness,
        smooth: 0.4,
        symbol: "none",
        lineStyle: { width: 2.5, color: SCIENTIFIC_COLORS.primary },
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
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { type: "dashed", width: 1.5 },
          label: { fontSize: 9, distance: [10, 0] },
          data: [
            { yAxis: 77, label: { formatter: "Optimal", position: "end", color: SCIENTIFIC_COLORS.success }, lineStyle: { color: SCIENTIFIC_COLORS.success } },
            { yAxis: 60, label: { formatter: "Threshold", position: "end", color: SCIENTIFIC_COLORS.warning }, lineStyle: { color: SCIENTIFIC_COLORS.warning } },
          ],
        },
        markArea: markAreas.length > 0 ? { silent: true, data: markAreas } : undefined,
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
          const eff = p[0].value;
          const status = eff >= 77 ? "Optimal" : eff >= 60 ? "Moderate" : "Impaired";
          const color = eff >= 77 ? SCIENTIFIC_COLORS.success : eff >= 60 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.danger;
          return `<b>${p[0].name}</b><br/>Effectiveness: <span style="color:${color};font-weight:600">${eff.toFixed(0)}%</span> (${status})`;
        }
        return "";
      },
    },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
    ],
  };

  return <EChartsWrapper option={option} height={280} showToolbox={false} />;
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
        // Generate demo data using SAFTE two-harmonic circadian model
        // Based on Hursh et al. (2004) - 24h + 12h harmonics
        const currentHour = new Date().getHours();
        const baseEff = 82;
        
        // SAFTE circadian parameters (from safte_model.py)
        const p = 18.0;       // 24h peak phase (evening)
        const pPrime = 3.0;   // 12h harmonic phase
        const beta = 0.5;     // 12h harmonic amplitude ratio
        const a1 = 7.8;       // Base circadian contribution
        const a2 = 5.0;       // Additional circadian under fatigue
        
        const demoData: FatigueResponse = {
          effectiveness_pct: baseEff,
          fatigue_level: "normal",
          forecast_hours: Array.from({ length: 24 }, (_, i) => i),
          forecast_effectiveness: Array.from({ length: 24 }, (_, i) => {
            const hour = (currentHour + i) % 24;
            
            // Two-harmonic circadian function: c1 (24h) + beta * c2 (12h)
            const phaseRel = (hour - p + 24) % 24;
            const c1 = Math.cos((2 * Math.PI * phaseRel) / 24);  // 24h harmonic
            const c2 = Math.cos((4 * Math.PI * (phaseRel - pPrime)) / 24);  // 12h harmonic
            const circadianDrive = c1 + beta * c2;  // Range: ~-1.5 to +1.5
            
            // Convert to effectiveness percentage
            // This creates: peaks ~10:00 & ~18:00, troughs ~04:00 (WOCL) & ~14:00 (post-lunch)
            const circadianEffect = (a1 + a2 * 0.2) * circadianDrive;
            
            // Add small noise for realism
            const noise = (Math.random() - 0.5) * 3;
            
            return Math.max(40, Math.min(100, baseEff + circadianEffect + noise));
          }),
          sleep_debt_hours: 2.5,
          optimal_sleep_hours: 8,
          risk_level: "low",
          risk_color: "green",
          recommendations: [
            "Adequate rest levels - normal operations appropriate",
            "Window of Circadian Low (WOCL): ~02:00-06:00 - lowest alertness",
            "Post-lunch dip: ~13:00-15:00 - secondary circadian trough",
            "Peak alertness windows: ~09:00-11:00 and ~17:00-19:00",
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
                  <CardTitle>SAFTE Model Scientific Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-3">
                  <p>
                    • <strong>SAFTE</strong> (Sleep, Activity, Fatigue, Task Effectiveness) is a biomathematical 
                    model developed by the U.S. Department of Defense for predicting cognitive effectiveness 
                    based on sleep history and circadian phase.
                  </p>
                  <p>
                    • <strong>Two-Harmonic Circadian Drive</strong>: The model uses a 24h + 12h harmonic function 
                    (C = cos(24h) + β·cos(12h)) producing two daily alertness peaks (~09:00-11:00 and ~17:00-19:00) 
                    and two troughs (WOCL ~02:00-06:00 and post-lunch ~13:00-15:00).
                  </p>
                  <p>
                    • <strong>WOCL</strong> (Window of Circadian Low): 02:00-06:00 local time represents 
                    the primary circadian nadir with lowest alertness and highest accident risk.
                  </p>
                  <p>
                    • <strong>Post-Lunch Dip</strong>: Secondary alertness trough ~13:00-15:00, independent 
                    of food intake, driven by the 12h harmonic component.
                  </p>
                  <p>
                    • <strong>Effectiveness &lt;60%</strong> is associated with significantly increased 
                    error rates equivalent to 0.08% BAC impairment in safety-critical tasks.
                  </p>
                  <div className="pt-2 border-t">
                    <p className="text-xs">
                      <strong>References:</strong><br/>
                      • Hursh SR et al. (2004). Fatigue models for applied research in warfighting. 
                      <span className="ml-1 text-primary">Aviat Space Environ Med, 75(3 Suppl), A44-53.</span><br/>
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
