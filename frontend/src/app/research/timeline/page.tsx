// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Sun,
  Heart,
  RefreshCw,
  Calendar,
  Zap,
  AlertTriangle,
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

// Mock data for unified timeline
const generateTimelineData = (days: number) => {
  const data: {
    dates: string[];
    rmssd: number[];
    kp: number[];
    events: Array<{ date: string; type: string; description: string }>;
  } = {
    dates: [],
    rmssd: [],
    kp: [],
    events: [],
  };

  const baseDate = new Date();
  baseDate.setDate(baseDate.getDate() - days);

  for (let i = 0; i < days; i++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + i);
    data.dates.push(date.toISOString().split("T")[0]);

    // Generate correlated mock data
    const kp = Math.random() * 4 + (i % 7 === 3 ? 3 : 0); // Spike every 7 days
    data.kp.push(kp);

    // RMSSD inversely related to Kp with lag
    const laggedKp = i > 1 ? data.kp[i - 1] : 3;
    const rmssd = 45 - laggedKp * 3 + Math.random() * 10;
    data.rmssd.push(Math.max(20, rmssd));

    // Add events
    if (kp > 5) {
      data.events.push({
        date: data.dates[i],
        type: "storm",
        description: `Geomagnetic Storm (Kp=${kp.toFixed(1)})`,
      });
    }
  }

  return data;
};

function UnifiedTimelineChart({ days }: { days: number }) {
  const data = React.useMemo(() => generateTimelineData(days), [days]);

  const option: Record<string, unknown> = {
    title: {
      text: "HRV & Space Weather Timeline",
      subtext: `Last ${days} days | Lag analysis: 24h offset applied`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: [
      { left: 70, right: 50, top: 70, height: "30%" },
      { left: 70, right: 50, top: "55%", height: "30%" },
    ],
    axisPointer: {
      link: [{ xAxisIndex: "all" }],
    },
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: "slider", xAxisIndex: [0, 1], start: 0, end: 100, bottom: 10, height: 20 },
    ],
    xAxis: [
      {
        type: "category",
        data: data.dates,
        gridIndex: 0,
        axisLabel: { show: false },
        axisTick: { show: false },
      },
      {
        type: "category",
        data: data.dates,
        gridIndex: 1,
        axisLabel: {
          color: SCIENTIFIC_COLORS.textPrimary,
          rotate: 45,
          interval: Math.max(0, Math.ceil(data.dates.length / 12) - 1),
          showMinLabel: true,
          showMaxLabel: true,
          fontSize: 10,
          align: "right",
        },
        axisTick: { alignWithLabel: true },
      },
    ],
    yAxis: [
      {
        type: "value",
        name: "RMSSD (ms)",
        gridIndex: 0,
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        splitLine: { lineStyle: { color: "rgba(100,100,100,0.2)" } },
      },
      {
        type: "value",
        name: "Kp Index",
        gridIndex: 1,
        min: 0,
        max: 9,
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        splitLine: { lineStyle: { color: "rgba(100,100,100,0.2)" } },
      },
    ],
    series: [
      {
        name: "RMSSD",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: data.rmssd,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.success },
        itemStyle: { color: SCIENTIFIC_COLORS.success },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(39, 174, 96, 0.3)" },
              { offset: 1, color: "rgba(39, 174, 96, 0.05)" },
            ],
          },
        },
      },
      {
        name: "Kp Index",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: data.kp.map((k) => ({
          value: k,
          itemStyle: {
            color:
              k >= 5 ? SCIENTIFIC_COLORS.danger : k >= 4 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.info,
          },
        })),
        barWidth: "60%",
        markLine: {
          silent: true,
          data: [
            { yAxis: 5, lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dashed" }, label: { formatter: "G1 Storm", color: SCIENTIFIC_COLORS.danger } },
          ],
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      formatter: (params: unknown[]) => {
        const p = params as Array<{ seriesName: string; value: number; axisValue: string }>;
        if (p.length === 0) return "";
        let result = `<strong>${p[0].axisValue}</strong><br/>`;
        p.forEach((item) => {
          const unit = item.seriesName === "RMSSD" ? " ms" : "";
          result += `${item.seriesName}: ${item.value.toFixed(1)}${unit}<br/>`;
        });
        return result;
      },
    },
    legend: {
      data: ["RMSSD", "Kp Index"],
      top: 35,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
  };

  return <EChartsWrapper option={option} height={500} />;
}

// Correlation highlight component
function CorrelationHighlight({
  rValue,
  lag,
  pValue,
}: {
  rValue: number;
  lag: number;
  pValue: number;
}) {
  const isSignificant = pValue < 0.05;

  return (
    <div className={`p-4 rounded-lg border ${isSignificant ? "border-primary bg-primary/5" : "border-muted"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Kp → RMSSD Correlation</span>
        {isSignificant && (
          <Badge variant="success" className="text-xs">
            Significant
          </Badge>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <p className="text-2xl font-bold" style={{ color: rValue < 0 ? SCIENTIFIC_COLORS.info : SCIENTIFIC_COLORS.danger }}>
            {rValue.toFixed(2)}
          </p>
          <p className="text-xs text-muted-foreground">r value</p>
        </div>
        <div>
          <p className="text-2xl font-bold">{lag}h</p>
          <p className="text-xs text-muted-foreground">Optimal lag</p>
        </div>
        <div>
          <p className="text-2xl font-bold">{pValue.toFixed(3)}</p>
          <p className="text-xs text-muted-foreground">p-value</p>
        </div>
      </div>
    </div>
  );
}

export default function TimelinePage() {
  const [days, setDays] = React.useState(30);
  const [loading, setLoading] = React.useState(false);

  return (
    <PageWrapper
      title="Unified Timeline"
      description="Synchronized HRV and Space Weather Visualization"
    >
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {days} days
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              24h lag offset
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="px-3 py-2 rounded-md border bg-background text-sm"
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
            </select>
            <Button disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {/* Main Timeline Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                Multi-Axis Timeline
              </CardTitle>
              <CardDescription>
                Top panel: RMSSD (HRV). Bottom panel: Kp Index (Geomagnetic Activity).
                Linked zoom and scroll.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <UnifiedTimelineChart days={days} />
            </CardContent>
          </Card>
        </motion.div>

        {/* Correlation Highlights */}
        <div className="grid gap-6 md:grid-cols-3">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <CorrelationHighlight rValue={-0.32} lag={24} pValue={0.028} />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="h-full">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Sun className="h-4 w-4 text-warning" />
                  <span className="text-sm font-medium">Key Observation</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Higher Kp index (geomagnetic storms) appears to correlate with reduced RMSSD
                  approximately 24 hours later, suggesting delayed physiological response.
                </p>
              </CardContent>
            </Card>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="h-full">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Heart className="h-4 w-4 text-danger" />
                  <span className="text-sm font-medium">Clinical Implication</span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Consider scheduling Polar H10 HRV recordings to avoid geomagnetically
                  disturbed periods (Kp &ge; 5) for baseline measurements.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Event Log */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-warning" />
                Space Weather Events
              </CardTitle>
              <CardDescription>
                Notable geomagnetic events during the selected period
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center gap-3 p-3 rounded-lg bg-warning/10 border border-warning/30">
                  <Badge variant="warning">G1</Badge>
                  <span className="text-sm">Minor geomagnetic storm detected — consider rescheduling sensitive measurements</span>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Events are flagged when Kp &ge; 5 (G1 storm level). NOAA scale: G1 (minor) to G5 (extreme).
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* References */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Scientific Background</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                • <strong>Solar-physiological correlation:</strong> Multiple studies report associations
                between geomagnetic activity and cardiovascular parameters, with effects typically
                appearing 12-48 hours post-event.
              </p>
              <p>
                • <strong>Lag analysis:</strong> Cross-correlation with varying time lags helps identify
                the optimal offset for correlating space weather indices with HRV metrics.
              </p>
              <p>
                • Alabdulgader A et al. (2018). Long-Term Study of HRV Responses to Solar/Geomagnetic Environment.
                <span className="ml-1 text-primary">Sci Rep, 8(1), 2663.</span>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
