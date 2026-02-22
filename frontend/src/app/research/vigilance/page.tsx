// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Eye, RefreshCw } from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { QualityPanel } from "@/components/research/quality-panel";
import { getVigilanceTracking } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { VigilanceResponse } from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

function vigilanceOption(data: VigilanceResponse): Record<string, unknown> {
  const x = data.predictions.map((p) => p.end_seconds.toFixed(0));
  const stateToY = (state: string) => {
    if (state === "high") return 2;
    if (state === "medium") return 1;
    return 0;
  };
  const vigilanceSeries = data.predictions.map((p) => stateToY(p.state));
  const safteSeries = data.predictions.map((p) => p.safte_effectiveness ?? null);
  return {
    grid: { left: 55, right: 50, top: 35, bottom: 55, containLabel: true },
    legend: {
      top: 5,
      textStyle: { color: "#1a1a1a" },
      data: ["Vigilance state", "SAFTE effectiveness"],
    },
    xAxis: {
      type: "category",
      data: x,
      name: "Time (s)",
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    yAxis: [
      {
        type: "value",
        min: -0.2,
        max: 2.2,
        interval: 1,
        name: "Vigilance",
        axisLabel: {
          color: "#1a1a1a",
          formatter: (value: number) => (value >= 2 ? "High" : value >= 1 ? "Medium" : "Low"),
        },
        nameTextStyle: { color: "#1a1a1a" },
      },
      {
        type: "value",
        min: 0,
        max: 100,
        name: "Effectiveness %",
        axisLabel: { color: "#1a1a1a" },
        nameTextStyle: { color: "#1a1a1a" },
      },
    ],
    tooltip: { trigger: "axis" },
    dataZoom: [{ type: "inside" }, { type: "slider", bottom: 8, height: 18 }],
    series: [
      {
        name: "Vigilance state",
        type: "line",
        step: "middle",
        data: vigilanceSeries,
        lineStyle: { color: SCIENTIFIC_COLORS.primary, width: 2 },
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        markArea: {
          silent: true,
          data: data.predictions
            .filter((p) => p.state === "low")
            .map((p) => [
              { xAxis: p.start_seconds.toFixed(0), itemStyle: { color: "rgba(231, 76, 60, 0.15)" } },
              { xAxis: p.end_seconds.toFixed(0) },
            ]),
        },
      },
      {
        name: "SAFTE effectiveness",
        type: "line",
        yAxisIndex: 1,
        data: safteSeries,
        smooth: true,
        symbol: "none",
        lineStyle: { color: SCIENTIFIC_COLORS.warning, width: 1.8, type: "dashed" },
      },
    ],
  };
}

export default function VigilancePage() {
  const [windowSize, setWindowSize] = React.useState(30);
  const [stepSize, setStepSize] = React.useState(10);
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState<VigilanceResponse | null>(null);

  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getVigilanceTracking(userId, windowSize, stepSize);
      setData(result);
    } finally {
      setLoading(false);
    }
  }, [userId, windowSize, stepSize]);

  React.useEffect(() => {
    void fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Vigilance Tracker"
      description="Sliding-window vigilance classification (default 30s / 10s) with SAFTE overlay"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-3"
        >
          <div className="flex items-center gap-2">
            {data && (
              <>
                <Badge variant="outline">Model: {data.model_version}</Badge>
                <Badge variant="outline">
                  Low vigilance windows: {data.low_vigilance_windows}/{data.total_windows}
                </Badge>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Window</span>
              <Input
                type="number"
                className="w-20 h-8"
                min={20}
                max={180}
                value={windowSize}
                onChange={(e) => setWindowSize(Number(e.target.value))}
              />
            </div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">Step</span>
              <Input
                type="number"
                className="w-20 h-8"
                min={5}
                max={60}
                value={stepSize}
                onChange={(e) => setStepSize(Number(e.target.value))}
              />
            </div>
            <Button onClick={() => void fetchData()} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {data && <QualityPanel context={data.context} />}

        {data && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-primary" />
                Vigilance State Over Time
              </CardTitle>
              <CardDescription>
                Low-vigilance windows are highlighted; dashed line shows SAFTE effectiveness.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EChartsWrapper option={vigilanceOption(data)} height={360} />
            </CardContent>
          </Card>
        )}

        {data && data.low_vigilance_windows > 0 && (
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center gap-2 text-warning">
                <AlertTriangle className="h-4 w-4" />
                <p className="text-sm">
                  Low-vigilance periods detected. Review duty timing and mitigation actions before safety-critical tasks.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}

