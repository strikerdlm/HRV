// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  GitCompare,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
  Info,
  CheckCircle,
  Clock,
  Sun,
  Heart,
  Upload,
  FileText,
  Database,
  BarChart3,
  ScatterChart,
  Activity,
  Download,
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
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import {
  getNOAADatasets,
  uploadRRData,
  parseRRFile,
  runCorrelationAnalysis,
} from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type {
  ComprehensiveCorrelationResponse,
  DetailedCorrelation,
  LagAnalysis,
  RRUploadResponse,
  NOAADataResponse,
} from "@/types/research";
import { SIGNIFICANCE_COLORS, STRENGTH_COLORS } from "@/types/research";

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

// Publication-quality correlation heatmap
function CorrelationHeatmap({
  matrix,
  pMatrix,
  solarLabels,
  hrvLabels,
}: {
  matrix: number[][];
  pMatrix: number[][];
  solarLabels: string[];
  hrvLabels: string[];
}) {
  // Build heatmap data
  const data: [number, number, number, number][] = [];
  for (let i = 0; i < solarLabels.length; i++) {
    for (let j = 0; j < hrvLabels.length; j++) {
      if (matrix[i] && matrix[i][j] !== undefined) {
        const pVal = pMatrix[i]?.[j] ?? 1;
        data.push([j, i, matrix[i][j], pVal]);
      }
    }
  }

  const option: Record<string, unknown> = {
    title: {
      text: "Solar Activity ↔ HRV Correlation Matrix",
      subtext: "Spearman correlations with significance indicators (* p<0.05, ** p<0.01, *** p<0.001)",
      left: "center",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary, fontSize: 11 },
    },
    grid: { left: 120, right: 80, top: 80, bottom: 80 },
    xAxis: {
      type: "category",
      data: hrvLabels,
      position: "bottom",
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        fontSize: 11,
        interval: 0,
      },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: "category",
      data: solarLabels,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        fontSize: 11,
      },
    },
    visualMap: {
      min: -0.5,
      max: 0.5,
      calculable: true,
      orient: "vertical",
      right: 10,
      top: "center",
      itemHeight: 200,
      inRange: {
        color: ["#2563eb", "#60a5fa", "#f8fafc", "#fbbf24", "#dc2626"],
      },
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      formatter: (value: number) => value.toFixed(2),
    },
    series: [
      {
        type: "heatmap",
        data: data,
        label: {
          show: true,
          formatter: (params: { value: number[] }) => {
            const r = params.value[2];
            const p = params.value[3];
            let stars = "";
            if (p < 0.001) stars = "***";
            else if (p < 0.01) stars = "**";
            else if (p < 0.05) stars = "*";
            return `${r.toFixed(2)}${stars}`;
          },
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 10,
          fontWeight: "bold",
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.3)" },
        },
        itemStyle: {
          borderWidth: 1,
          borderColor: "#fff",
        },
      },
    ],
    tooltip: {
      formatter: (params: { value: number[] }) => {
        const [x, y, r, p] = params.value;
        const hrvName = hrvLabels[x];
        const solarName = solarLabels[y];
        const sig = p < 0.05 ? " ★ Significant" : "";
        return `<b>${solarName} ↔ ${hrvName}</b><br/>
                r = ${r.toFixed(3)}<br/>
                p = ${p.toFixed(4)}${sig}<br/>
                R² = ${(r * r * 100).toFixed(1)}%`;
      },
    },
  };

  return <EChartsWrapper option={option} height={380} />;
}

// Lag analysis line chart
function LagAnalysisChart({ analyses }: { analyses: LagAnalysis[] }) {
  if (analyses.length === 0) return null;

  // Use the first analysis as primary
  const primary = analyses[0];
  const maxLabels = 8;
  const interval = Math.max(0, Math.ceil(primary.lags.length / maxLabels) - 1);

  const series = analyses.slice(0, 4).map((a, idx) => ({
    type: "line",
    name: `${a.solar_metric} → ${a.hrv_metric}`,
    data: a.correlations,
    smooth: true,
    symbol: "circle",
    symbolSize: 6,
    lineStyle: { width: 2 },
    markPoint: idx === 0 ? {
      data: [{ type: "max", name: "Optimal" }],
      label: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
    } : undefined,
  }));

  const option: Record<string, unknown> = {
    title: {
      text: "Correlation vs Lag Time",
      subtext: "Optimal lag maximizes |r| - effects typically appear 12-36h after solar events",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary, fontSize: 10 },
    },
    grid: { left: 60, right: 30, top: 80, bottom: 50 },
    legend: {
      top: 45,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
    },
    xAxis: {
      type: "category",
      data: primary.lags.map((l) => `${l}h`),
      name: "Lag (hours)",
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval,
        fontSize: 11,
      },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: "Correlation (r)",
      min: -0.5,
      max: 0.5,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
    },
    series,
    tooltip: {
      trigger: "axis",
      formatter: (params: Array<{ seriesName: string; value: number; axisValue: string }>) => {
        let result = `<b>Lag: ${params[0]?.axisValue}</b><br/>`;
        params.forEach((p) => {
          result += `${p.seriesName}: r = ${p.value.toFixed(3)}<br/>`;
        });
        return result;
      },
    },
    markLine: {
      data: [{ yAxis: 0, lineStyle: { type: "dashed", color: "#999" } }],
    },
  };

  return <EChartsWrapper option={option} height={320} />;
}

// Scatter plot for a specific correlation
function CorrelationScatter({ corr }: { corr: DetailedCorrelation }) {
  const data = corr.solar_values.map((s, i) => [s, corr.hrv_values[i]]);

  const option: Record<string, unknown> = {
    title: {
      text: `${corr.solar_metric_name} vs ${corr.physio_metric_name}`,
      subtext: `r = ${corr.r.toFixed(3)}, p = ${corr.p_value.toFixed(4)}, n = ${corr.n_samples}`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 13 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary, fontSize: 10 },
    },
    grid: { left: 50, right: 20, top: 60, bottom: 50 },
    xAxis: {
      type: "value",
      name: corr.solar_metric_name,
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    yAxis: {
      type: "value",
      name: corr.physio_metric_name,
      nameLocation: "middle",
      nameGap: 35,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    series: [
      {
        type: "scatter",
        data,
        symbolSize: 8,
        itemStyle: {
          color: corr.r > 0 ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.danger,
          opacity: 0.7,
        },
      },
      // Regression line (simplified)
      {
        type: "line",
        data: [
          [Math.min(...corr.solar_values), Math.min(...corr.hrv_values)],
          [Math.max(...corr.solar_values), Math.max(...corr.hrv_values)],
        ],
        lineStyle: { type: "dashed", color: SCIENTIFIC_COLORS.trend, width: 2 },
        symbol: "none",
      },
    ],
    tooltip: {
      formatter: (params: { value: number[] }) => {
        if (params.value) {
          return `${corr.solar_metric_name}: ${params.value[0]?.toFixed(1)}<br/>${corr.physio_metric_name}: ${params.value[1]?.toFixed(1)}`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={250} showToolbox={false} />;
}

// Timeline overlay chart (HRV + Space Weather)
function TimelineOverlay({ data }: { data: ComprehensiveCorrelationResponse }) {
  if (data.timeline_data.length === 0) return null;

  const dates = data.timeline_data.map((d) => d.date);
  const kp = data.timeline_data.map((d) => d.kp ?? null);
  const rmssd = data.timeline_data.map((d) => d.rmssd ?? null);

  const maxLabels = 10;
  const interval = Math.max(0, Math.ceil(dates.length / maxLabels) - 1);

  const option: Record<string, unknown> = {
    title: {
      text: "HRV & Space Weather Timeline",
      subtext: "RMSSD (parasympathetic) and Kp Index (geomagnetic activity)",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary, fontSize: 10 },
    },
    grid: { left: 60, right: 60, top: 70, bottom: 60 },
    legend: {
      top: 45,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        interval,
        rotate: 45,
        fontSize: 10,
        align: "right",
      },
      axisTick: { alignWithLabel: true },
    },
    yAxis: [
      {
        type: "value",
        name: "RMSSD (ms)",
        position: "left",
        axisLabel: { color: SCIENTIFIC_COLORS.success },
        nameTextStyle: { color: SCIENTIFIC_COLORS.success },
        splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
      },
      {
        type: "value",
        name: "Kp Index",
        position: "right",
        min: 0,
        max: 9,
        axisLabel: { color: SCIENTIFIC_COLORS.warning },
        nameTextStyle: { color: SCIENTIFIC_COLORS.warning },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "RMSSD",
        type: "line",
        yAxisIndex: 0,
        data: rmssd,
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.success },
        itemStyle: { color: SCIENTIFIC_COLORS.success },
      },
      {
        name: "Kp Index",
        type: "bar",
        yAxisIndex: 1,
        data: kp,
        barWidth: "60%",
        itemStyle: {
          color: (params: { value: number }) => {
            const v = params.value;
            if (v >= 5) return SCIENTIFIC_COLORS.danger;
            if (v >= 4) return SCIENTIFIC_COLORS.warning;
            return "rgba(243, 156, 18, 0.5)";
          },
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
    },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 5 },
    ],
  };

  return <EChartsWrapper option={option} height={350} />;
}

// Significant correlation card
function SignificantCorrelationCard({ corr }: { corr: DetailedCorrelation }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 rounded-lg border bg-card hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <Sun className="h-4 w-4 text-warning shrink-0" />
            <span className="font-medium text-sm">{corr.solar_metric_name}</span>
            <span className="text-muted-foreground">↔</span>
            <Heart className="h-4 w-4 text-danger shrink-0" />
            <span className="font-medium text-sm">{corr.physio_metric_name}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            Lag: {corr.lag_hours}h | n = {corr.n_samples}
          </div>
        </div>
        <div className="text-right shrink-0">
          <p
            className="text-xl font-bold"
            style={{ color: corr.r > 0 ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.danger }}
          >
            r = {corr.r.toFixed(3)}
          </p>
          <p className="text-xs text-muted-foreground">
            p = {corr.p_value.toFixed(4)}
          </p>
        </div>
      </div>
      <Separator className="my-3" />
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <Badge
          style={{
            backgroundColor: STRENGTH_COLORS[corr.strength] + "20",
            color: STRENGTH_COLORS[corr.strength],
            borderColor: STRENGTH_COLORS[corr.strength],
          }}
          variant="outline"
        >
          {corr.strength}
        </Badge>
        <Badge
          style={{
            backgroundColor: SIGNIFICANCE_COLORS[corr.significance] + "20",
            color: SIGNIFICANCE_COLORS[corr.significance],
            borderColor: SIGNIFICANCE_COLORS[corr.significance],
          }}
          variant="outline"
        >
          {corr.significance.replace(/_/g, " ")}
        </Badge>
        <Badge variant="outline">
          95% CI: [{corr.ci_lower.toFixed(2)}, {corr.ci_upper.toFixed(2)}]
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground mt-3">{corr.interpretation}</p>
    </motion.div>
  );
}

// Upload section component
function UploadSection({
  onUpload,
  uploadResult,
  loading,
}: {
  onUpload: (rr: number[]) => void;
  uploadResult: RRUploadResponse | null;
  loading: boolean;
}) {
  const [dragActive, setDragActive] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const text = await file.text();
    const rr = parseRRFile(text);
    if (rr.length >= 30) {
      onUpload(rr);
    } else {
      alert(`Found only ${rr.length} valid RR intervals. Need at least 30.`);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5 text-primary" />
          Upload RR Data
        </CardTitle>
        <CardDescription>
          Upload a text file with RR intervals (ms) for correlation analysis
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
            dragActive ? "border-primary bg-primary/5" : "border-muted"
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".txt,.csv"
            className="hidden"
            onChange={handleChange}
          />
          <FileText className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium">Drop RR file here or click to browse</p>
          <p className="text-xs text-muted-foreground mt-1">
            Accepts .txt or .csv with RR intervals in ms
          </p>
        </div>

        {loading && (
          <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Processing RR data...
          </div>
        )}

        {uploadResult && uploadResult.success && (
          <div className="mt-4 p-3 bg-success/10 rounded-lg border border-success/20">
            <div className="flex items-center gap-2 text-success font-medium">
              <CheckCircle className="h-4 w-4" />
              {uploadResult.message}
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
              <div>Duration: {uploadResult.duration_minutes.toFixed(1)} min</div>
              <div>Mean HR: {uploadResult.mean_hr_bpm.toFixed(0)} bpm</div>
              <div>RMSSD: {uploadResult.rmssd?.toFixed(1) ?? "—"} ms</div>
              <div>SDNN: {uploadResult.sdnn?.toFixed(1) ?? "—"} ms</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// NOAA status section
function NOAAStatusSection({
  noaaData,
  onRefresh,
  loading,
}: {
  noaaData: NOAADataResponse | null;
  onRefresh: () => void;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5 text-warning" />
          NOAA Space Weather Data
        </CardTitle>
        <CardDescription>
          Live solar activity data for correlation analysis
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button onClick={onRefresh} disabled={loading} className="w-full mb-4">
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Fetch NOAA Data
        </Button>

        {noaaData && Object.keys(noaaData.datasets).length > 0 && (
          <div className="space-y-2">
            {Object.entries(noaaData.datasets).map(([key, info]) => (
              <div key={key} className="p-2 bg-muted/50 rounded text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{info.title}</span>
                  <Badge variant="outline" className="text-xs">
                    {info.rows_available} pts
                  </Badge>
                </div>
                {info.time_range && (
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    {info.time_range}
                  </p>
                )}
              </div>
            ))}
            <p className="text-xs text-muted-foreground">
              Fetched: {new Date(noaaData.fetched_at).toLocaleString()}
            </p>
          </div>
        )}

        {noaaData && Object.keys(noaaData.errors).length > 0 && (
          <div className="mt-2 p-2 bg-warning/10 rounded text-xs text-warning">
            <AlertTriangle className="h-3 w-3 inline mr-1" />
            Some data sources unavailable
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function CorrelationsPage() {
  const [correlationData, setCorrelationData] = React.useState<ComprehensiveCorrelationResponse | null>(null);
  const [noaaData, setNoaaData] = React.useState<NOAADataResponse | null>(null);
  const [uploadResult, setUploadResult] = React.useState<RRUploadResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [uploadLoading, setUploadLoading] = React.useState(false);
  const [noaaLoading, setNoaaLoading] = React.useState(false);

  const activeUserId = useAppStore((state) => state.activeUserId);

  // Fetch NOAA data
  const fetchNOAA = React.useCallback(async () => {
    setNoaaLoading(true);
    try {
      const data = await getNOAADatasets(30);
      setNoaaData(data);
    } catch (error) {
      console.error("NOAA fetch error:", error);
    } finally {
      setNoaaLoading(false);
    }
  }, []);

  // Handle RR upload
  const handleRRUpload = React.useCallback(async (rr: number[]) => {
    setUploadLoading(true);
    try {
      const result = await uploadRRData({
        rr_intervals_ms: rr,
        recording_timestamp: new Date().toISOString(),
        source: "uploaded",
      });
      setUploadResult(result);
    } catch (error) {
      console.error("Upload error:", error);
      alert("Failed to process RR data: " + (error instanceof Error ? error.message : "Unknown error"));
    } finally {
      setUploadLoading(false);
    }
  }, []);

  // Run correlation analysis
  const runAnalysis = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await runCorrelationAnalysis({
        session_id: uploadResult?.session_id,
        user_id: activeUserId ?? undefined,
        max_lag_hours: 72,
      });
      setCorrelationData(result);
    } catch (error) {
      console.error("Analysis error:", error);
    } finally {
      setLoading(false);
    }
  }, [uploadResult?.session_id, activeUserId]);

  // Auto-fetch NOAA on mount
  React.useEffect(() => {
    fetchNOAA();
  }, [fetchNOAA]);

  return (
    <PageWrapper
      title="Solar-HRV Correlations"
      description="Publication-quality analysis of space weather effects on physiological parameters"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3 flex-wrap">
            {correlationData && (
              <>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Activity className="h-3 w-3" />
                  {correlationData.n_days} days
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Heart className="h-3 w-3" />
                  {correlationData.n_hrv_samples} HRV samples
                </Badge>
                <Badge variant="success" className="flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  {correlationData.significant_correlations.length} significant
                </Badge>
                {correlationData.optimal_lag_hours !== null && (
                  <Badge variant="info" className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Optimal lag: {correlationData.optimal_lag_hours}h
                  </Badge>
                )}
              </>
            )}
          </div>
          <Button onClick={runAnalysis} disabled={loading} size="lg">
            <Zap className={`h-4 w-4 mr-2 ${loading ? "animate-pulse" : ""}`} />
            Run Correlation Analysis
          </Button>
        </motion.div>

        {/* Data Input Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <UploadSection
              onUpload={handleRRUpload}
              uploadResult={uploadResult}
              loading={uploadLoading}
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <NOAAStatusSection
              noaaData={noaaData}
              onRefresh={fetchNOAA}
              loading={noaaLoading}
            />
          </motion.div>
        </div>

        {/* Results Section */}
        {correlationData && (
          <>
            {/* Correlation Heatmap */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-primary" />
                    Correlation Matrix
                  </CardTitle>
                  <CardDescription>
                    Heatmap showing Spearman correlations between solar activity and HRV metrics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {correlationData.correlation_matrix.length > 0 ? (
                    <CorrelationHeatmap
                      matrix={correlationData.correlation_matrix}
                      pMatrix={correlationData.p_value_matrix}
                      solarLabels={correlationData.solar_labels}
                      hrvLabels={correlationData.hrv_labels}
                    />
                  ) : (
                    <div className="h-[380px] flex items-center justify-center text-muted-foreground">
                      No correlation data available
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Lag Analysis & Timeline */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5 text-info" />
                      Lag Analysis
                    </CardTitle>
                    <CardDescription>
                      How correlations vary with time delay (0-72 hours)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {correlationData.lag_analyses.length > 0 ? (
                      <LagAnalysisChart analyses={correlationData.lag_analyses} />
                    ) : (
                      <div className="h-[320px] flex items-center justify-center text-muted-foreground">
                        No lag analysis available
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-success" />
                      Timeline Overlay
                    </CardTitle>
                    <CardDescription>
                      HRV and space weather data over time
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {correlationData.timeline_data.length > 0 ? (
                      <TimelineOverlay data={correlationData} />
                    ) : (
                      <div className="h-[350px] flex items-center justify-center text-muted-foreground">
                        No timeline data available
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Scatter Plots */}
            {correlationData.significant_correlations.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <ScatterChart className="h-5 w-5 text-primary" />
                      Significant Correlations - Scatter Plots
                    </CardTitle>
                    <CardDescription>
                      Visual representation of the strongest relationships
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                      {correlationData.significant_correlations.slice(0, 6).map((corr, idx) => (
                        <CorrelationScatter key={idx} corr={corr} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Significant Correlations Cards */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <GitCompare className="h-5 w-5 text-primary" />
                    Significant Correlations (p &lt; 0.05)
                  </CardTitle>
                  <CardDescription>
                    Statistically significant relationships with effect sizes and confidence intervals
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    {correlationData.significant_correlations.map((corr, idx) => (
                      <SignificantCorrelationCard key={idx} corr={corr} />
                    ))}
                    {correlationData.significant_correlations.length === 0 && (
                      <div className="col-span-full text-center py-8 text-muted-foreground">
                        <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p>No significant correlations found</p>
                        <p className="text-sm">Accumulate more data points for robust analysis</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Insights & Recommendations */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-info" />
                      Pattern Insights
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-3">
                      {correlationData.pattern_insights.map((insight, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <CheckCircle className="h-4 w-4 text-success mt-0.5 shrink-0" />
                          <span className="text-sm">{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.9 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      Recommendations
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-3">
                      {correlationData.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <Info className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                          <span className="text-sm">{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Methodology & References */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1.0 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Methodology & Scientific Background</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-3">
                  <div>
                    <strong>Statistical Methods:</strong>
                    <ul className="list-disc ml-5 mt-1 space-y-1">
                      {correlationData.methodology_notes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                  <Separator />
                  <div>
                    <strong>Scientific Background:</strong>
                    <p className="mt-1">
                      Multiple studies have documented associations between geomagnetic disturbances
                      and autonomic nervous system activity. Effects typically appear with 12-36 hour delays
                      (Alabdulgader et al., 2018; Vieira et al., 2022). Even modest correlations (r = 0.2-0.4)
                      may be biologically meaningful given the complexity of physiological regulation.
                    </p>
                  </div>
                  <div>
                    <strong>Key References:</strong>
                    <p className="text-xs mt-1">
                      Alabdulgader A, et al. (2018). Human Heart Rhythm Sensitivity to Earth Local Magnetic
                      Field Fluctuations. J Vibroeng. | Vieira CLZ, et al. (2022). Geomagnetic activity and
                      HRV: A Review. Adv Space Res. | Stoupel E, et al. (2008). Space proton flux and
                      cardiovascular deaths. Int J Biometeorol.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </>
        )}

        {/* Initial State - No Results Yet */}
        {!correlationData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardContent className="py-12 text-center">
                <GitCompare className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                <h3 className="text-lg font-medium mb-2">Ready for Analysis</h3>
                <p className="text-muted-foreground max-w-md mx-auto">
                  Upload RR interval data or use stored HRV recordings, then click
                  &ldquo;Run Correlation Analysis&rdquo; to discover relationships between space weather
                  and your physiological parameters.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </PageWrapper>
  );
}
