// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  BookOpen,
  CheckCircle,
  ChevronDown,
  FileText,
  FlaskConical,
  Heart,
  Info,
  Layers,
  RefreshCw,
  Shield,
  Target,
  TrendingDown,
  Upload,
  Wind,
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
import { Label } from "@/components/ui/label";
import { AnimatePresence } from "framer-motion";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { getVTDemo, analyzeVT, parseRRFile } from "@/lib/research-api";
import type { VTAnalysisResponse } from "@/types/research";
import { VT_ZONE_COLORS, DFA_ZONE_COLORS } from "@/types/research";

// ---------------------------------------------------------------------------
// Helper: format seconds to mm:ss
// ---------------------------------------------------------------------------
function fmtTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Chart: DFA-α1 Time Series (Publication Quality)
// ---------------------------------------------------------------------------
function DFATimeSeriesChart({ data }: { data: VTAnalysisResponse }) {
  const option: Record<string, unknown> = React.useMemo(() => {
    const times = data.timeseries_time.map((t) => fmtTime(t));
    const dfaVals = data.timeseries_dfa;

    // Build mark areas for intensity zones
    const markAreaData: unknown[] = [];
    if (dfaVals.length > 0) {
      markAreaData.push(
        [
          { yAxis: 0.75, itemStyle: { color: DFA_ZONE_COLORS.vt1ToVT2 } },
          { yAxis: 0.50 },
        ],
        [
          { yAxis: 0.50, itemStyle: { color: DFA_ZONE_COLORS.aboveVT2 } },
          { yAxis: 0 },
        ],
        [
          { yAxis: 2.0, itemStyle: { color: DFA_ZONE_COLORS.belowVT1 } },
          { yAxis: 0.75 },
        ],
      );
    }

    // VT1 and VT2 vertical lines
    const markLines: unknown[] = [];
    if (data.vt1) {
      markLines.push({
        xAxis: fmtTime(data.vt1.time_seconds),
        label: {
          formatter: `VT1\n${data.vt1.heart_rate_bpm.toFixed(0)} bpm`,
          position: "insideStartTop",
          color: SCIENTIFIC_COLORS.success,
          fontWeight: "bold",
          fontSize: 11,
        },
        lineStyle: { color: SCIENTIFIC_COLORS.success, width: 2.5, type: "dashed" },
      });
    }
    if (data.vt2) {
      markLines.push({
        xAxis: fmtTime(data.vt2.time_seconds),
        label: {
          formatter: `VT2\n${data.vt2.heart_rate_bpm.toFixed(0)} bpm`,
          position: "insideStartTop",
          color: SCIENTIFIC_COLORS.danger,
          fontWeight: "bold",
          fontSize: 11,
        },
        lineStyle: { color: SCIENTIFIC_COLORS.danger, width: 2.5, type: "dashed" },
      });
    }

    return {
      title: {
        text: "DFA-α1 Time Series",
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      },
      grid: { left: 65, right: 40, top: 55, bottom: 80, containLabel: false },
      xAxis: {
        type: "category",
        data: times,
        name: "Time (min:sec)",
        nameLocation: "middle",
        nameGap: 35,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
      },
      yAxis: {
        type: "value",
        name: "DFA-α1",
        nameLocation: "middle",
        nameGap: 45,
        min: 0,
        max: 1.6,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
        splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: SCIENTIFIC_COLORS.axisLine,
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
        formatter: (params: Array<{ name: string; value: number; seriesName: string; marker: string }>) => {
          const p = params[0];
          const zone =
            p.value > 0.75 ? "Below VT1 (Aerobic)" :
            p.value > 0.5 ? "VT1–VT2 (Threshold)" :
            "Above VT2 (High Intensity)";
          return `<strong>${p.name}</strong><br/>${p.marker} DFA-α1: <strong>${p.value.toFixed(3)}</strong><br/>Zone: ${zone}`;
        },
      },
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { type: "slider", bottom: 10, height: 20, start: 0, end: 100 },
      ],
      series: [
        {
          name: "DFA-α1",
          type: "line",
          data: dfaVals,
          smooth: 0.3,
          symbol: "circle",
          symbolSize: 4,
          lineStyle: { width: 2.5, color: "#6366f1" },
          itemStyle: { color: "#6366f1" },
          areaStyle: { color: "rgba(99, 102, 241, 0.06)" },
          markLine: {
            silent: true,
            symbol: "none",
            data: [
              // VT1 threshold
              {
                yAxis: 0.75,
                label: { formatter: "VT1 (α1=0.75)", position: "insideEndTop", color: SCIENTIFIC_COLORS.success, fontSize: 10 },
                lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dotted", width: 1.5 },
              },
              // VT2 threshold
              {
                yAxis: 0.50,
                label: { formatter: "VT2 (α1=0.50)", position: "insideEndTop", color: SCIENTIFIC_COLORS.danger, fontSize: 10 },
                lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dotted", width: 1.5 },
              },
              ...markLines,
            ],
          },
          markArea: {
            silent: true,
            data: markAreaData,
          },
        },
      ],
    };
  }, [data]);

  return <EChartsWrapper option={option} height={420} />;
}

// ---------------------------------------------------------------------------
// Chart: Heart Rate Progression
// ---------------------------------------------------------------------------
function HRProgressionChart({ data }: { data: VTAnalysisResponse }) {
  const option: Record<string, unknown> = React.useMemo(() => {
    const times = data.timeseries_time.map((t) => fmtTime(t));

    const markLines: unknown[] = [];
    if (data.vt1) {
      markLines.push(
        {
          xAxis: fmtTime(data.vt1.time_seconds),
          label: { formatter: "VT1", position: "insideStartTop", color: SCIENTIFIC_COLORS.success, fontWeight: "bold" },
          lineStyle: { color: SCIENTIFIC_COLORS.success, width: 2, type: "dashed" },
        },
        {
          yAxis: data.vt1.heart_rate_bpm,
          label: { formatter: `${data.vt1.heart_rate_bpm.toFixed(0)} bpm`, position: "insideEndTop", color: SCIENTIFIC_COLORS.success },
          lineStyle: { color: SCIENTIFIC_COLORS.success, width: 1, type: "dotted" },
        },
      );
    }
    if (data.vt2) {
      markLines.push(
        {
          xAxis: fmtTime(data.vt2.time_seconds),
          label: { formatter: "VT2", position: "insideStartTop", color: SCIENTIFIC_COLORS.danger, fontWeight: "bold" },
          lineStyle: { color: SCIENTIFIC_COLORS.danger, width: 2, type: "dashed" },
        },
        {
          yAxis: data.vt2.heart_rate_bpm,
          label: { formatter: `${data.vt2.heart_rate_bpm.toFixed(0)} bpm`, position: "insideEndTop", color: SCIENTIFIC_COLORS.danger },
          lineStyle: { color: SCIENTIFIC_COLORS.danger, width: 1, type: "dotted" },
        },
      );
    }

    return {
      title: {
        text: "Heart Rate Progression",
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      },
      grid: { left: 65, right: 40, top: 55, bottom: 80, containLabel: false },
      xAxis: {
        type: "category",
        data: times,
        name: "Time (min:sec)",
        nameLocation: "middle",
        nameGap: 35,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
      },
      yAxis: {
        type: "value",
        name: "Heart Rate (bpm)",
        nameLocation: "middle",
        nameGap: 45,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
        splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: SCIENTIFIC_COLORS.axisLine,
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
      dataZoom: [
        { type: "inside", start: 0, end: 100 },
        { type: "slider", bottom: 10, height: 20, start: 0, end: 100 },
      ],
      series: [
        {
          name: "Heart Rate",
          type: "line",
          data: data.timeseries_hr,
          smooth: 0.3,
          symbol: "none",
          lineStyle: { width: 2.5, color: "#dc2626" },
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(220, 38, 38, 0.2)" },
                { offset: 1, color: "rgba(220, 38, 38, 0.02)" },
              ],
            },
          },
          markLine: { silent: true, symbol: "none", data: markLines },
        },
        {
          name: "Mean HR (window)",
          type: "line",
          data: data.timeseries_hr_mean,
          smooth: 0.3,
          symbol: "none",
          lineStyle: { width: 1.5, color: "#f97316", type: "dashed" },
        },
      ],
      legend: {
        data: ["Heart Rate", "Mean HR (window)"],
        bottom: 40,
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      },
    };
  }, [data]);

  return <EChartsWrapper option={option} height={380} />;
}

// ---------------------------------------------------------------------------
// Chart: Integrated Score
// ---------------------------------------------------------------------------
function IntegratedScoreChart({ data }: { data: VTAnalysisResponse }) {
  const option: Record<string, unknown> = React.useMemo(() => {
    const times = data.timeseries_time.map((t) => fmtTime(t));
    const scores = data.timeseries_integrated_score;

    const markLines: unknown[] = [
      {
        yAxis: 0.45,
        label: { formatter: "VT1 score (0.45)", position: "insideEndTop", color: SCIENTIFIC_COLORS.success, fontSize: 10 },
        lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dotted", width: 1.5 },
      },
      {
        yAxis: 0.75,
        label: { formatter: "VT2 score (0.75)", position: "insideEndTop", color: SCIENTIFIC_COLORS.danger, fontSize: 10 },
        lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dotted", width: 1.5 },
      },
    ];

    return {
      title: {
        text: "Multi-Parameter Integrated Score",
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      },
      grid: { left: 65, right: 40, top: 55, bottom: 60, containLabel: false },
      xAxis: {
        type: "category",
        data: times,
        name: "Time (min:sec)",
        nameLocation: "middle",
        nameGap: 35,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
      },
      yAxis: {
        type: "value",
        name: "Score",
        nameLocation: "middle",
        nameGap: 45,
        min: 0,
        max: 1,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
        splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: SCIENTIFIC_COLORS.axisLine,
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
        formatter: (params: Array<{ name: string; value: number; marker: string }>) => {
          const p = params[0];
          return `<strong>${p.name}</strong><br/>${p.marker} Score: <strong>${p.value.toFixed(3)}</strong><br/><em>VT1 @ 0.45 | VT2 @ 0.75</em>`;
        },
      },
      series: [
        {
          name: "Integrated Score",
          type: "line",
          data: scores,
          smooth: 0.3,
          symbol: "none",
          lineStyle: { width: 2.5, color: "#8b5cf6" },
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(139, 92, 246, 0.25)" },
                { offset: 1, color: "rgba(139, 92, 246, 0.02)" },
              ],
            },
          },
          markLine: { silent: true, symbol: "none", data: markLines },
        },
      ],
    };
  }, [data]);

  return <EChartsWrapper option={option} height={320} />;
}

// ---------------------------------------------------------------------------
// Chart: DFA-α1 vs Heart Rate scatter (Dual Y-axis overlay)
// ---------------------------------------------------------------------------
function DFAvsHRChart({ data }: { data: VTAnalysisResponse }) {
  const option: Record<string, unknown> = React.useMemo(() => {
    // Scatter: HR on X-axis, DFA on Y-axis
    const scatterData = data.timeseries_hr.map((hr, i) => [hr, data.timeseries_dfa[i]]);

    // Color each point by zone
    const pointColors = data.timeseries_dfa.map((d) => {
      if (d > 0.75) return SCIENTIFIC_COLORS.success;
      if (d > 0.50) return "#f59e0b";
      return SCIENTIFIC_COLORS.danger;
    });

    return {
      title: {
        text: "DFA-α1 vs Heart Rate",
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14, fontWeight: "bold" },
      },
      grid: { left: 65, right: 40, top: 55, bottom: 65, containLabel: false },
      xAxis: {
        type: "value",
        name: "Heart Rate (bpm)",
        nameLocation: "middle",
        nameGap: 35,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
      },
      yAxis: {
        type: "value",
        name: "DFA-α1",
        nameLocation: "middle",
        nameGap: 45,
        min: 0,
        max: 1.6,
        axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
        nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontWeight: "bold" },
        splitLine: { lineStyle: { color: SCIENTIFIC_COLORS.gridLine } },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: "#ffffff",
        borderColor: SCIENTIFIC_COLORS.axisLine,
        textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
        formatter: (params: { value: [number, number] }) =>
          `HR: <strong>${params.value[0].toFixed(0)} bpm</strong><br/>DFA-α1: <strong>${params.value[1].toFixed(3)}</strong>`,
      },
      series: [
        {
          type: "scatter",
          data: scatterData,
          symbolSize: 7,
          itemStyle: {
            color: (params: { dataIndex: number }) => pointColors[params.dataIndex],
            opacity: 0.8,
          },
          markLine: {
            silent: true,
            symbol: "none",
            data: [
              {
                yAxis: 0.75,
                label: { formatter: "VT1", color: SCIENTIFIC_COLORS.success, fontSize: 10 },
                lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dashed" },
              },
              {
                yAxis: 0.50,
                label: { formatter: "VT2", color: SCIENTIFIC_COLORS.danger, fontSize: 10 },
                lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dashed" },
              },
            ],
          },
        },
      ],
    };
  }, [data]);

  return <EChartsWrapper option={option} height={380} />;
}

// ---------------------------------------------------------------------------
// Metric summary card
// ---------------------------------------------------------------------------
function VTMetricCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
  description,
  confidence,
}: {
  title: string;
  value: string;
  unit?: string;
  icon: React.ElementType;
  color: string;
  description: string;
  confidence?: number;
}) {
  return (
    <div className="p-5 rounded-xl border bg-gradient-to-br from-card to-muted/20 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-foreground">{title}</span>
      </div>
      <p className="text-3xl font-bold text-foreground">
        {value}
        {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
      </p>
      <p className="text-xs text-muted-foreground mt-2">{description}</p>
      {confidence !== undefined && (
        <div className="mt-2 flex items-center gap-2">
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.round(confidence * 100)}%`,
                backgroundColor: confidence > 0.7 ? SCIENTIFIC_COLORS.success : confidence > 0.4 ? SCIENTIFIC_COLORS.warning : SCIENTIFIC_COLORS.danger,
              }}
            />
          </div>
          <span className="text-xs font-medium">{(confidence * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Intensity Zone Card
// ---------------------------------------------------------------------------
function ZoneCard({ zone }: { zone: VTAnalysisResponse["intensity_zones"][0] }) {
  const zoneColor = VT_ZONE_COLORS[zone.zone] ?? SCIENTIFIC_COLORS.primary;
  return (
    <div className="p-4 rounded-xl border-l-4 bg-card shadow-sm" style={{ borderLeftColor: zoneColor }}>
      <div className="flex items-center gap-2 mb-2">
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: zoneColor }} />
        <h4 className="font-semibold text-sm">{zone.zone_label}</h4>
      </div>
      <p className="text-xs text-muted-foreground mb-2">{zone.zone_description}</p>
      <div className="flex gap-4 text-xs">
        <span className="font-medium">
          HR: {zone.hr_min.toFixed(0)}–{zone.hr_max.toFixed(0)} bpm
        </span>
        <span className="text-muted-foreground">{zone.dfa_range}</span>
      </div>
      <p className="text-xs text-primary mt-2 font-medium">{zone.training_guidance}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Science Explanation Collapsible
// ---------------------------------------------------------------------------
function ScienceExplanation() {
  const [open, setOpen] = React.useState(false);
  return (
    <Card>
      <CardHeader>
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setOpen(!open)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setOpen(!open); }}
        >
          <CardTitle className="flex items-center gap-2 text-base">
            <BookOpen className="h-5 w-5 text-indigo-500" />
            Understanding DFA-α1 &amp; Ventilatory Thresholds
          </CardTitle>
          <ChevronDown className={`h-5 w-5 transition-transform ${open ? "rotate-180" : ""}`} />
        </div>
        <CardDescription>
          Scientific background on DFA-based threshold detection
        </CardDescription>
      </CardHeader>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">What is DFA-α1?</h4>
                <p>
                  Detrended Fluctuation Analysis (DFA) quantifies the fractal correlation
                  properties of RR interval time series. The short-term scaling exponent
                  (α1, computed over 4-16 beats) reflects autonomic nervous system regulation
                  of cardiac rhythm.
                </p>
                <ul className="space-y-1 ml-4 list-disc">
                  <li><strong>α1 ≈ 1.0:</strong> Correlated fractal pattern — healthy resting state</li>
                  <li><strong>α1 ≈ 0.75:</strong> First Ventilatory Threshold (VT1) — aerobic threshold</li>
                  <li><strong>α1 ≈ 0.50:</strong> Second Ventilatory Threshold (VT2) — anaerobic threshold</li>
                  <li><strong>α1 &lt; 0.50:</strong> Random/uncorrelated — maximal intensity</li>
                </ul>
              </div>
              <div className="space-y-3">
                <h4 className="font-semibold text-foreground">Multi-Parameter Algorithm</h4>
                <p>
                  This implementation uses a multi-parameter approach inspired by the
                  Kubios VT-algorithm (Eronen et al., 2024), combining:
                </p>
                <ul className="space-y-1 ml-4 list-disc">
                  <li><strong>DFA-α1 (60% weight):</strong> Primary fractal correlation metric</li>
                  <li><strong>HR Reserve (30%):</strong> Normalized heart rate position</li>
                  <li><strong>Respiratory frequency (10%):</strong> Ventilatory modulation</li>
                </ul>
                <p className="text-xs italic mt-2">
                  Validation: VT1 r=0.81 (VO₂), bias 1±11 bpm | VT2 r=0.93, SE&lt;7 bpm
                  (Eronen et al., 2024, n=64)
                </p>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium text-amber-800 dark:text-amber-200 text-xs">Experimental Feature</p>
                  <p className="text-xs text-amber-700 dark:text-amber-300 mt-1">
                    HRV-based VT estimation is for research purposes. Clinical decisions should be
                    validated against gold-standard CPET. Signal quality &gt;85% and artifact rate &lt;5% are
                    recommended for reliable results.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Upload Panel Component (functional with exercise-data warnings)
// ---------------------------------------------------------------------------
function VTUploadPanel({
  onResult,
  loading,
  setLoading,
}: {
  onResult: (result: VTAnalysisResponse) => void;
  loading: boolean;
  setLoading: (v: boolean) => void;
}) {
  const [dragActive, setDragActive] = React.useState(false);
  const [hrRest, setHrRest] = React.useState<number>(60);
  const [hrMax, setHrMax] = React.useState<number>(185);
  const [method, setMethod] = React.useState<string>("multiparameter");
  const [uploadStatus, setUploadStatus] = React.useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const [parsedCount, setParsedCount] = React.useState<number | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const processFile = React.useCallback(
    async (file: File) => {
      setUploadStatus(null);
      setParsedCount(null);
      setLoading(true);

      try {
        const text = await file.text();
        const rr = parseRRFile(text);

        if (rr.length < 100) {
          setUploadStatus({
            type: "error",
            message: `Found only ${rr.length} valid RR intervals. VT detection requires at least 100 beats (≥ 5 min graded exercise test recommended).`,
          });
          setLoading(false);
          return;
        }

        setParsedCount(rr.length);

        // Validate plausible exercise RR values (200–1500 ms)
        const outOfRange = rr.filter((v) => v < 200 || v > 1500).length;
        if (outOfRange > rr.length * 0.25) {
          setUploadStatus({
            type: "error",
            message: `${outOfRange} of ${rr.length} intervals are outside physiological range (200–1500 ms). Check that values are in milliseconds.`,
          });
          setLoading(false);
          return;
        }

        const result = await analyzeVT(rr, hrRest, hrMax, method);

        if (result.timeseries_time.length === 0) {
          setUploadStatus({
            type: "error",
            message: "Analysis returned empty results. Ensure the file contains RR data from a graded exercise test with progressively increasing intensity.",
          });
        } else {
          setUploadStatus({
            type: "success",
            message: `Successfully analyzed ${rr.length} RR intervals (${(rr.reduce((a, b) => a + b, 0) / 60000).toFixed(1)} min). VT detection complete.`,
          });
          onResult(result);
        }
      } catch (error) {
        setUploadStatus({
          type: "error",
          message:
            "Failed to analyze RR data: " +
            (error instanceof Error ? error.message : "Unknown error. Is the backend running?"),
        });
      } finally {
        setLoading(false);
      }
    },
    [hrRest, hrMax, method, onResult, setLoading],
  );

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div className="space-y-4">
      {/* ---- Exercise Data Requirement Warning ---- */}
      <div className="p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
          <div className="space-y-2">
            <p className="font-semibold text-amber-800 dark:text-amber-200 text-sm">
              Exercise RR Data Required
            </p>
            <p className="text-xs text-amber-700 dark:text-amber-300 leading-relaxed">
              VT estimation requires RR intervals recorded <strong>during a graded (incremental) exercise test</strong> with
              progressively increasing intensity — e.g., a ramp protocol on a treadmill or cycle ergometer.
              <strong> Resting HRV recordings will not produce valid results.</strong>
            </p>
            <div className="mt-2 text-xs text-amber-700 dark:text-amber-300 space-y-1">
              <p className="font-medium">For accurate results, your recording should have:</p>
              <ul className="list-disc ml-5 space-y-0.5">
                <li><strong>Duration:</strong> 8–25 min graded exercise test (ramp or step protocol)</li>
                <li><strong>HR range:</strong> From resting (~60 bpm) to near-maximal (~85–100% HRmax)</li>
                <li><strong>Signal quality:</strong> Chest-strap HRM (Polar H10, Garmin HRM-Pro) recommended — wrist-based optical HR is <strong>not</strong> suitable (poor beat-to-beat accuracy)</li>
                <li><strong>Artifact rate:</strong> &lt;5% for reliable DFA-α1 computation</li>
                <li><strong>Sampling:</strong> Beat-to-beat RR intervals in milliseconds (not averaged HR)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* ---- Physiological Parameters ---- */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Heart className="h-4 w-4 text-red-500" />
            Physiological Parameters
          </CardTitle>
          <CardDescription className="text-xs">
            Set your resting and maximum heart rate for accurate threshold placement.
            These are used to normalize HR reserve in the multi-parameter algorithm.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="hr-rest" className="text-xs font-medium">
                Resting HR (bpm)
              </Label>
              <Input
                id="hr-rest"
                type="number"
                min={30}
                max={120}
                value={hrRest}
                onChange={(e) => setHrRest(Number(e.target.value))}
                className="h-9"
              />
              <p className="text-[10px] text-muted-foreground">
                Measured lying down after 5 min rest
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="hr-max" className="text-xs font-medium">
                Max HR (bpm)
              </Label>
              <Input
                id="hr-max"
                type="number"
                min={120}
                max={230}
                value={hrMax}
                onChange={(e) => setHrMax(Number(e.target.value))}
                className="h-9"
              />
              <p className="text-[10px] text-muted-foreground">
                Known max or 220 − age estimate
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="vt-method" className="text-xs font-medium">
                Detection Method
              </Label>
              <select
                id="vt-method"
                aria-label="Detection Method"
                title="Detection Method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="multiparameter">Multi-Parameter (recommended)</option>
                <option value="dfa_only">DFA-α1 Only</option>
              </select>
              <p className="text-[10px] text-muted-foreground">
                Multi-parameter = DFA-α1 60% + HR reserve 30% + resp. 10%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ---- File Drop Zone ---- */}
      <Card>
        <CardContent className="pt-6">
          <div
            className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
              dragActive ? "border-primary bg-primary/5" : "border-muted hover:border-muted-foreground/40"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".txt,.csv"
              className="hidden"
              aria-label="Upload RR interval file"
              title="Upload RR interval file"
              onChange={handleChange}
            />
            <FileText className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
            <p className="text-sm font-medium">Drop exercise RR file here or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">
              Accepts .txt or .csv — one RR interval (ms) per line, comma-separated, or space-separated
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Or use the <strong>Run Demo</strong> button above for a synthetic 20-min graded exercise test
            </p>
          </div>

          {/* Loading indicator */}
          {loading && (
            <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Running VT analysis on uploaded RR data...
            </div>
          )}

          {/* Parsed count */}
          {parsedCount !== null && !loading && uploadStatus?.type !== "error" && (
            <p className="text-xs text-muted-foreground mt-3">
              Parsed <strong>{parsedCount}</strong> RR intervals from file.
            </p>
          )}

          {/* Status messages */}
          {uploadStatus?.type === "success" && (
            <div className="mt-4 p-3 bg-emerald-50 dark:bg-emerald-950/20 rounded-lg border border-emerald-200 dark:border-emerald-800">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-medium text-sm">
                <CheckCircle className="h-4 w-4" />
                {uploadStatus.message}
              </div>
            </div>
          )}

          {uploadStatus?.type === "error" && (
            <div className="mt-4 p-3 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-800">
              <div className="flex items-start gap-2 text-red-700 dark:text-red-300 text-sm">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{uploadStatus.message}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------
export default function VentilatoryThresholdPage() {
  const [data, setData] = React.useState<VTAnalysisResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [showUpload, setShowUpload] = React.useState(false);

  const fetchDemo = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getVTDemo();
      if (result.timeseries_time.length === 0) {
        // Generate client-side demo if API is unavailable
        setData(_generateClientDemo());
      } else {
        setData(result);
      }
    } catch {
      setData(_generateClientDemo());
    } finally {
      setLoading(false);
    }
  }, []);

  const handleVTResult = React.useCallback((result: VTAnalysisResponse) => {
    setData(result);
  }, []);

  React.useEffect(() => {
    fetchDemo();
  }, [fetchDemo]);

  return (
    <PageWrapper
      title="Ventilatory Threshold Estimation"
      description="DFA-α1 Based Exercise Threshold Detection"
    >
      <div className="space-y-6">
        {/* Header with experimental badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="border-amber-500 text-amber-600 gap-1">
              <FlaskConical className="h-3 w-3" />
              Experimental
            </Badge>
            {data?.method && (
              <Badge variant="secondary">
                Method: {data.method === "multiparameter" ? "Multi-Parameter" : "DFA-only"}
              </Badge>
            )}
            {data?.quality && (
              <Badge
                variant="outline"
                style={{
                  borderColor: data.quality.monotonic_decrease ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.warning,
                  color: data.quality.monotonic_decrease ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.warning,
                }}
              >
                {data.quality.monotonic_decrease ? "Valid Exercise Profile" : "Non-standard Profile"}
              </Badge>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowUpload(!showUpload)}>
              <Upload className="h-4 w-4 mr-2" />
              {showUpload ? "Hide Upload" : "Upload RR Data"}
            </Button>
            <Button onClick={fetchDemo} disabled={loading} size="sm">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Run Demo
            </Button>
          </div>
        </motion.div>

        {/* Upload Panel (collapsible, fully functional) */}
        <AnimatePresence>
          {showUpload && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <VTUploadPanel
                onResult={handleVTResult}
                loading={loading}
                setLoading={setLoading}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {data && (
          <>
            {/* Key Metrics Row */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
            >
              <VTMetricCard
                title="VT1 (Aerobic)"
                value={data.vt1 ? data.vt1.heart_rate_bpm.toFixed(0) : "—"}
                unit="bpm"
                icon={Target}
                color="bg-emerald-500"
                description={data.vt1 ? `At ${fmtTime(data.vt1.time_seconds)} | DFA-α1 = ${data.vt1.dfa_alpha1.toFixed(2)} | ${(data.vt1.hr_relative * 100).toFixed(0)}% HR reserve` : "Not detected"}
                confidence={data.vt1?.confidence}
              />
              <VTMetricCard
                title="VT2 (Anaerobic)"
                value={data.vt2 ? data.vt2.heart_rate_bpm.toFixed(0) : "—"}
                unit="bpm"
                icon={Zap}
                color="bg-red-500"
                description={data.vt2 ? `At ${fmtTime(data.vt2.time_seconds)} | DFA-α1 = ${data.vt2.dfa_alpha1.toFixed(2)} | ${(data.vt2.hr_relative * 100).toFixed(0)}% HR reserve` : "Not detected"}
                confidence={data.vt2?.confidence}
              />
              <VTMetricCard
                title="Signal Quality"
                value={data.quality ? `${data.quality.clean_beats}` : "—"}
                unit="beats"
                icon={Shield}
                color="bg-blue-500"
                description={data.quality ? `Artifacts: ${data.quality.artifact_percentage.toFixed(1)}% | Windows: ${data.quality.n_windows} | DFA range: ${data.quality.dfa_range.toFixed(2)}` : "N/A"}
              />
              <VTMetricCard
                title="Resp. Frequency"
                value={data.respiratory_frequency_hz ? (data.respiratory_frequency_hz * 60).toFixed(1) : "—"}
                unit="br/min"
                icon={Wind}
                color="bg-violet-500"
                description={data.respiratory_frequency_hz ? `${data.respiratory_frequency_hz.toFixed(3)} Hz — used in multi-parameter integration` : "N/A"}
              />
            </motion.div>

            {/* Main Chart: DFA-α1 Time Series */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingDown className="h-5 w-5 text-indigo-500" />
                    DFA-α1 During Exercise
                  </CardTitle>
                  <CardDescription>
                    Short-term fractal scaling exponent (4-16 beats) computed in 120s sliding windows.
                    Green zone = aerobic (α1 &gt; 0.75), Orange = threshold, Red = high intensity (α1 &lt; 0.50).
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <DFATimeSeriesChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Two-column: HR + DFA vs HR scatter */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Heart className="h-5 w-5 text-red-500" />
                      Heart Rate Progression
                    </CardTitle>
                    <CardDescription>
                      Instantaneous and windowed-mean HR with VT markers
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <HRProgressionChart data={data} />
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
                      <BarChart3 className="h-5 w-5 text-violet-500" />
                      DFA-α1 vs Heart Rate
                    </CardTitle>
                    <CardDescription>
                      Scatter plot showing the inverse relationship. Points color-coded by zone.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <DFAvsHRChart data={data} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Integrated Score */}
            {data.method === "multiparameter" && data.timeseries_integrated_score.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Layers className="h-5 w-5 text-violet-500" />
                      Multi-Parameter Integrated Score
                    </CardTitle>
                    <CardDescription>
                      Weighted combination: 60% DFA-α1 + 30% HR Reserve + 10% Respiratory frequency.
                      VT1 detected at score ≥ 0.45, VT2 at score ≥ 0.75.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <IntegratedScoreChart data={data} />
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Intensity Zones */}
            {data.intensity_zones.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-emerald-500" />
                      Exercise Intensity Zones
                    </CardTitle>
                    <CardDescription>
                      Personalized training zones derived from VT1 and VT2 detection.
                      Heart rate targets for optimal training prescription.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      {data.intensity_zones.map((zone) => (
                        <ZoneCard key={zone.zone} zone={zone} />
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Interpretation */}
            {(data.interpretation.length > 0 || data.warnings.length > 0) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Info className="h-5 w-5 text-blue-500" />
                      Analysis Results &amp; Interpretation
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {data.interpretation.map((note, idx) => (
                      <div key={`interp-${idx}`} className="flex items-start gap-3">
                        <BadgeCheck className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
                        <p className="text-sm text-foreground">{note}</p>
                      </div>
                    ))}
                    {data.warnings.map((warn, idx) => (
                      <div key={`warn-${idx}`} className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20">
                        <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                        <p className="text-sm text-amber-800 dark:text-amber-200">{warn}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Science Explanation */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <ScienceExplanation />
            </motion.div>

            {/* References */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-slate-500" />
                    Scientific References
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • Eronen T, et al. (2024). Heart Rate Variability Based Ventilatory Threshold
                    Estimation — Validation of a Commercially Available Algorithm.
                    <span className="ml-1 text-primary">medRxiv. doi: 10.1101/2024.08.14.24311967</span>
                  </p>
                  <p>
                    • Gronwald T, Rogers B, Hoos O. (2020). Correlation properties of HRV during
                    endurance exercise: A systematic review.
                    <span className="ml-1 text-primary">Ann Noninvasive Electrocardiol, 25(1):e12697.</span>
                  </p>
                  <p>
                    • Rogers B, et al. (2021). A New Detection Method Defining the Aerobic Threshold
                    for Endurance Exercise Based on Fractal Correlation Properties of HRV.
                    <span className="ml-1 text-primary">Front Physiol, 11:596567.</span>
                  </p>
                  <p>
                    • Peng CK, et al. (1995). Quantification of scaling exponents and crossover
                    phenomena in nonstationary heartbeat time series.
                    <span className="ml-1 text-primary">Chaos, 5(1):82-87.</span>
                  </p>
                  <p>
                    • Shaffer F, Ginsberg JP. (2017). An Overview of Heart Rate Variability Metrics
                    and Norms.
                    <span className="ml-1 text-primary">Front Public Health, 5:258.</span>
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

// ---------------------------------------------------------------------------
// Client-side demo data generator (fallback when API is unavailable)
// ---------------------------------------------------------------------------
function _generateClientDemo(): VTAnalysisResponse {
  const n = 100;
  const times: number[] = [];
  const dfaVals: number[] = [];
  const hrVals: number[] = [];
  const hrMean: number[] = [];
  const scores: number[] = [];

  for (let i = 0; i < n; i++) {
    const t = (i / n) * 1200; // 20 min = 1200s
    times.push(t);

    // DFA decreases from ~1.1 to ~0.35 in a sigmoid curve
    const frac = i / n;
    const dfa = 1.1 - 0.75 / (1 + Math.exp(-10 * (frac - 0.5))) + (Math.random() - 0.5) * 0.06;
    dfaVals.push(Math.max(0.2, Math.min(1.5, dfa)));

    // HR increases from 65 to 185
    const hr = 65 + 120 / (1 + Math.exp(-8 * (frac - 0.5))) + (Math.random() - 0.5) * 3;
    hrVals.push(hr);
    hrMean.push(hr + (Math.random() - 0.5) * 2);

    // Integrated score
    const dfaNorm = Math.max(0, Math.min(1, (1 - dfa) / 0.5));
    const hrNorm = Math.max(0, Math.min(1, (hr - 65) / 120));
    scores.push(0.6 * dfaNorm + 0.3 * hrNorm + 0.1 * frac * 0.3);
  }

  // Find VT1 and VT2 indices
  const vt1Idx = dfaVals.findIndex((d) => d <= 0.75);
  const vt2Idx = dfaVals.findIndex((d) => d <= 0.50);

  return {
    vt1: vt1Idx >= 0 ? {
      time_seconds: times[vt1Idx],
      heart_rate_bpm: hrVals[vt1Idx],
      dfa_alpha1: dfaVals[vt1Idx],
      hr_relative: (hrVals[vt1Idx] - 65) / 120,
      confidence: 0.78,
      index: vt1Idx,
    } : null,
    vt2: vt2Idx >= 0 ? {
      time_seconds: times[vt2Idx],
      heart_rate_bpm: hrVals[vt2Idx],
      dfa_alpha1: dfaVals[vt2Idx],
      hr_relative: (hrVals[vt2Idx] - 65) / 120,
      confidence: 0.85,
      index: vt2Idx,
    } : null,
    timeseries_time: times,
    timeseries_dfa: dfaVals,
    timeseries_hr: hrVals,
    timeseries_hr_mean: hrMean,
    timeseries_integrated_score: scores,
    respiratory_frequency_hz: 0.28,
    quality: {
      artifact_percentage: 2.3,
      total_beats: 2400,
      clean_beats: 2345,
      n_windows: n,
      min_dfa: Math.min(...dfaVals),
      max_dfa: Math.max(...dfaVals),
      dfa_range: Math.max(...dfaVals) - Math.min(...dfaVals),
      monotonic_decrease: true,
    },
    method: "multiparameter",
    intensity_zones: [
      {
        zone: "zone_1",
        zone_label: "Zone 1 — Aerobic (below VT1)",
        zone_description: "Low intensity, parasympathetic dominance. Sustainable for extended periods. DFA-α1 > 0.75 indicates preserved fractal correlation.",
        hr_min: 65,
        hr_max: vt1Idx >= 0 ? hrVals[vt1Idx] : 130,
        dfa_range: "α1 > 0.75",
        training_guidance: "Base endurance, recovery, long slow distance.",
      },
      {
        zone: "zone_2",
        zone_label: "Zone 2 — Threshold (VT1 to VT2)",
        zone_description: "Moderate-to-high intensity, mixed autonomic regulation. DFA-α1 between 0.50-0.75.",
        hr_min: vt1Idx >= 0 ? hrVals[vt1Idx] : 130,
        hr_max: vt2Idx >= 0 ? hrVals[vt2Idx] : 160,
        dfa_range: "0.50 < α1 < 0.75",
        training_guidance: "Tempo runs, threshold training, sweet-spot intervals.",
      },
      {
        zone: "zone_3",
        zone_label: "Zone 3 — High Intensity (above VT2)",
        zone_description: "Sympathetic dominance. Near-complete vagal withdrawal. DFA-α1 < 0.50.",
        hr_min: vt2Idx >= 0 ? hrVals[vt2Idx] : 160,
        hr_max: 185,
        dfa_range: "α1 < 0.50",
        training_guidance: "VO2max intervals, race-pace efforts. Limited sustainability.",
      },
    ],
    interpretation: [
      `VT1 (aerobic threshold) detected at HR ${vt1Idx >= 0 ? hrVals[vt1Idx].toFixed(0) : "—"} bpm — ${vt1Idx >= 0 ? ((hrVals[vt1Idx] - 65) / 120 * 100).toFixed(0) : "—"}% HR reserve.`,
      `VT2 (anaerobic threshold) detected at HR ${vt2Idx >= 0 ? hrVals[vt2Idx].toFixed(0) : "—"} bpm — ${vt2Idx >= 0 ? ((hrVals[vt2Idx] - 65) / 120 * 100).toFixed(0) : "—"}% HR reserve.`,
      "Multi-parameter algorithm shows clear DFA-α1 transition from correlated (aerobic) to uncorrelated (high intensity) patterns.",
      "Signal quality is excellent with low artifact rate.",
    ],
    warnings: [],
  };
}
