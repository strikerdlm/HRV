// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Users,
  TrendingUp,
  RefreshCw,
  Book,
  Filter,
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
import { getPopulationNorms } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { PopulationNormsResponse, AgeNorm } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

// Age-Stratified Bar Chart
function NormsBarChart({ norms, metric }: { norms: AgeNorm[]; metric: string }) {
  const metricNames: Record<string, string> = {
    rmssd: "RMSSD (ms)",
    sdnn: "SDNN (ms)",
    pnn50: "pNN50 (%)",
    lf_hf_ratio: "LF/HF Ratio",
  };

  const option: Record<string, unknown> = {
    title: {
      text: `${metricNames[metric] ?? metric} by Age Group`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 70, bottom: 60 },
    legend: {
      top: 35,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    xAxis: {
      type: "category",
      data: norms.map((n) => n.age_range),
      name: "Age Group",
      nameLocation: "middle",
      nameGap: 35,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: metricNames[metric] ?? metric,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "bar",
        name: "Mean",
        data: norms.map((n) => n.mean),
        barWidth: "40%",
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        label: {
          show: true,
          position: "top",
          color: SCIENTIFIC_COLORS.textPrimary,
          formatter: (p: { value: number }) => p.value.toFixed(0),
        },
      },
      {
        type: "custom",
        name: "Range (P5-P95)",
        renderItem: (params: { coordSys: { x: number; width: number }; dataIndex: number }, api: { value: (idx: number) => number; coord: (val: [number, number]) => [number, number]; size: (val: [number, number]) => [number, number] }) => {
          const idx = params.dataIndex;
          const norm = norms[idx];
          const x = api.coord([idx, 0])[0];
          const y1 = api.coord([idx, norm.p5])[1];
          const y2 = api.coord([idx, norm.p95])[1];
          const width = api.size([0, 1])[0] * 0.1;

          return {
            type: "group",
            children: [
              {
                type: "line",
                shape: { x1: x, y1: y1, x2: x, y2: y2 },
                style: { stroke: SCIENTIFIC_COLORS.textSecondary, lineWidth: 2 },
              },
              {
                type: "line",
                shape: { x1: x - width, y1: y1, x2: x + width, y2: y1 },
                style: { stroke: SCIENTIFIC_COLORS.textSecondary, lineWidth: 2 },
              },
              {
                type: "line",
                shape: { x1: x - width, y1: y2, x2: x + width, y2: y2 },
                style: { stroke: SCIENTIFIC_COLORS.textSecondary, lineWidth: 2 },
              },
            ],
          };
        },
        data: norms.map((n) => [n.p5, n.p95]),
        z: 10,
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ name: string; seriesName: string; value: number; dataIndex: number }>;
        if (p[0]) {
          const norm = norms[p[0].dataIndex];
          return `<strong>${norm.age_range}</strong><br/>
                  Mean: ${norm.mean.toFixed(1)} ± ${norm.std.toFixed(1)}<br/>
                  P5-P95: ${norm.p5.toFixed(0)} - ${norm.p95.toFixed(0)}<br/>
                  P25-P75: ${norm.p25.toFixed(0)} - ${norm.p75.toFixed(0)}`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={350} />;
}

// Percentile Box Plot - Using bar chart with error bars for reliable rendering
function PercentileBoxPlot({ norms }: { norms: AgeNorm[] }) {
  const metricLabel = norms[0]?.metric === "rmssd" ? "RMSSD (ms)" : 
                      norms[0]?.metric === "sdnn" ? "SDNN (ms)" : 
                      norms[0]?.metric ?? "Value";
  
  // Calculate y-axis bounds
  const allValues = norms.flatMap(n => [n.p5, n.p95]);
  const minY = Math.floor(Math.min(...allValues) * 0.9);
  const maxY = Math.ceil(Math.max(...allValues) * 1.1);
  
  const option: Record<string, unknown> = {
    title: {
      text: "Percentile Distribution by Age Group",
      subtext: "Box: P25-P75 (IQR) | Whiskers: P5-P95 | Line: Median (P50)",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary, fontSize: 10 },
    },
    legend: {
      top: 40,
      data: ["IQR (P25-P75)", "Median (P50)"],
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    grid: { left: 70, right: 30, top: 80, bottom: 50 },
    xAxis: {
      type: "category",
      data: norms.map((n) => n.age_range),
      name: "Age Group",
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      axisTick: { alignWithLabel: true },
      boundaryGap: true,
    },
    yAxis: {
      type: "value",
      name: metricLabel,
      min: minY,
      max: maxY,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
    },
    series: [
      // IQR Box (P25 to P75) - using stacked bars
      {
        name: "P25 Base",
        type: "bar",
        stack: "box",
        data: norms.map(n => n.p25),
        barWidth: "50%",
        itemStyle: { color: "transparent" },
        emphasis: { itemStyle: { color: "transparent" } },
      },
      {
        name: "IQR (P25-P75)",
        type: "bar",
        stack: "box",
        data: norms.map(n => n.p75 - n.p25),
        barWidth: "50%",
        itemStyle: { 
          color: "rgba(52, 152, 219, 0.4)",
          borderColor: SCIENTIFIC_COLORS.primary,
          borderWidth: 2,
        },
      },
      // Median line
      {
        name: "Median (P50)",
        type: "scatter",
        symbol: "rect",
        symbolSize: [40, 4],
        data: norms.map(n => n.p50),
        itemStyle: { color: SCIENTIFIC_COLORS.danger },
        z: 10,
      },
      // P5 whisker
      {
        name: "P5",
        type: "scatter",
        symbol: "rect",
        symbolSize: [20, 2],
        data: norms.map(n => n.p5),
        itemStyle: { color: SCIENTIFIC_COLORS.textSecondary },
        z: 5,
      },
      // P95 whisker  
      {
        name: "P95",
        type: "scatter",
        symbol: "rect",
        symbolSize: [20, 2],
        data: norms.map(n => n.p95),
        itemStyle: { color: SCIENTIFIC_COLORS.textSecondary },
        z: 5,
      },
    ],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: Array<{ dataIndex: number }>) => {
        if (params[0]) {
          const norm = norms[params[0].dataIndex];
          if (norm) {
            return `<strong style="font-size: 13px">${norm.age_range}</strong><br/>
                    <span style="color: ${SCIENTIFIC_COLORS.danger}">●</span> <b>Median (P50):</b> ${norm.p50.toFixed(0)}<br/>
                    <span style="color: ${SCIENTIFIC_COLORS.primary}">■</span> <b>IQR (P25-P75):</b> ${norm.p25.toFixed(0)} - ${norm.p75.toFixed(0)}<br/>
                    <span style="color: ${SCIENTIFIC_COLORS.textSecondary}">┃</span> <b>Range (P5-P95):</b> ${norm.p5.toFixed(0)} - ${norm.p95.toFixed(0)}<br/>
                    <b>Mean ± SD:</b> ${norm.mean.toFixed(1)} ± ${norm.std.toFixed(1)}`;
          }
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={350} />;
}

// Norm Table
function NormTable({ norms }: { norms: AgeNorm[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2">Age Group</th>
            <th className="text-right p-2">Mean ± SD</th>
            <th className="text-right p-2">P5</th>
            <th className="text-right p-2">P25</th>
            <th className="text-right p-2">P50</th>
            <th className="text-right p-2">P75</th>
            <th className="text-right p-2">P95</th>
          </tr>
        </thead>
        <tbody>
          {norms.map((n) => (
            <tr key={n.age_range} className="border-b hover:bg-muted/50">
              <td className="p-2 font-medium">{n.age_range}</td>
              <td className="text-right p-2">{n.mean.toFixed(1)} ± {n.std.toFixed(1)}</td>
              <td className="text-right p-2">{n.p5.toFixed(0)}</td>
              <td className="text-right p-2">{n.p25.toFixed(0)}</td>
              <td className="text-right p-2 font-medium">{n.p50.toFixed(0)}</td>
              <td className="text-right p-2">{n.p75.toFixed(0)}</td>
              <td className="text-right p-2">{n.p95.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function NormsPage() {
  const [data, setData] = React.useState<PopulationNormsResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [metric, setMetric] = React.useState<string>("rmssd");

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getPopulationNorms(userId, metric);
      if (result.norms.length === 0) {
        // Demo data already provided by API
      }
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [userId, metric]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Population Norms"
      description="Age-Stratified Reference Values for HRV Metrics"
    >
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            {data?.user_age_group && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                Your Group: {data.user_age_group}
              </Badge>
            )}
            {data?.user_percentiles[metric] !== undefined && (
              <Badge variant="success">
                Your Percentile: P{data.user_percentiles[metric].toFixed(0)}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="px-3 py-2 rounded-md border bg-background text-sm"
            >
              <option value="rmssd">RMSSD</option>
              <option value="sdnn">SDNN</option>
            </select>
            <Button onClick={fetchData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {data && (
          <>
            {/* Bar Chart */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-primary" />
                    Age-Stratified Norms
                  </CardTitle>
                  <CardDescription>
                    Mean values with P5-P95 range whiskers
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <NormsBarChart norms={data.norms} metric={metric} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Box Plot */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-info" />
                    Percentile Distribution
                  </CardTitle>
                  <CardDescription>
                    Box plot showing P5, P25, P50, P75, P95 for each age group
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PercentileBoxPlot norms={data.norms} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Data Table */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Book className="h-5 w-5 text-success" />
                    Reference Values Table
                  </CardTitle>
                  <CardDescription>
                    Complete percentile data for clinical reference
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <NormTable norms={data.norms} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Sources */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Data Sources</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    <strong>Primary Source:</strong>
                  </p>
                  <p className="ml-4">{data.primary_source}</p>
                  {data.additional_sources.length > 0 && (
                    <>
                      <p className="mt-4">
                        <strong>Additional Sources:</strong>
                      </p>
                      {data.additional_sources.map((src, idx) => (
                        <p key={idx} className="ml-4">• {src}</p>
                      ))}
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}
      </div>
    </PageWrapper>
  );
}
