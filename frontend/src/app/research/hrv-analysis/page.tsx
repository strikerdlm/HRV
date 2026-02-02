// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Clock,
  Heart,
  Waves,
  Network,
  Zap,
  Upload,
  BarChart3,
  RefreshCw,
  Info,
  HelpCircle,
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { HRVGauge } from "@/components/charts";
import type { HRVAnalysisResult, HRFMetrics } from "@/types/research";
import { HRV_METRIC_INFO } from "@/types/research";

/**
 * Comprehensive metric explanations for publication-quality scientific documentation.
 * Each metric includes clinical significance, normal ranges, and interpretation guidance.
 */
const METRIC_EXPLANATIONS: Record<string, { title: string; explanation: string; normalRange: string; clinicalSignificance: string }> = {
  sdnn: {
    title: "SDNN (Standard Deviation of NN Intervals)",
    explanation: "The gold standard measure of overall HRV. SDNN reflects all cyclic components responsible for variability in the recording period, including circadian rhythms for 24h recordings.",
    normalRange: "Short-term (5 min): 50-100 ms | 24h: 100-180 ms",
    clinicalSignificance: "SDNN <50ms in 24h recordings indicates significantly increased cardiovascular risk. Values decline with age but can be improved through exercise, stress reduction, and sleep optimization.",
  },
  rmssd: {
    title: "RMSSD (Root Mean Square of Successive Differences)",
    explanation: "Primary measure of parasympathetic (vagal) activity. RMSSD reflects beat-to-beat variations and is largely independent of circadian influences, making it ideal for short recordings.",
    normalRange: "Short-term (5 min): 20-75 ms | Athletes may exceed 100 ms",
    clinicalSignificance: "Low RMSSD indicates reduced vagal tone, associated with stress, overtraining, or cardiovascular pathology. It's the preferred metric for monitoring recovery and training readiness.",
  },
  pnn50: {
    title: "pNN50 (Percentage of Successive Intervals >50ms)",
    explanation: "The percentage of successive RR intervals differing by more than 50 milliseconds. Highly correlated with RMSSD and similarly reflects parasympathetic activity.",
    normalRange: "Short-term: 10-30% | Values vary significantly with age",
    clinicalSignificance: "Easy to interpret percentage that tracks vagal tone. Like RMSSD, low values indicate reduced parasympathetic activity and potential cardiovascular stress.",
  },
  lf_hf_ratio: {
    title: "LF/HF Ratio",
    explanation: "Traditionally interpreted as sympathovagal balance, but this interpretation is now disputed. The LF band contains both sympathetic and parasympathetic influences, complicating interpretation.",
    normalRange: "Typically 0.5-2.0 in resting conditions",
    clinicalSignificance: "CAUTION: Per Billman (2013), this ratio does NOT accurately reflect sympathovagal balance. Use with care and prefer direct assessment of HF power for parasympathetic evaluation.",
  },
  dfa_alpha1: {
    title: "DFA α1 (Detrended Fluctuation Analysis)",
    explanation: "Short-term fractal scaling exponent (4-11 beats) measuring self-similarity in heart rate dynamics. Healthy hearts exhibit fractal-like correlation structures (α1 ≈ 1.0).",
    normalRange: "Healthy: 0.75-1.0 | Optimal: ~1.0",
    clinicalSignificance: "α1 < 0.65 suggests loss of correlation (pathological). α1 > 1.35 indicates rigid, overly regular rhythm. Both extremes are associated with increased mortality risk.",
  },
  pip: {
    title: "PIP (Percentage of Inflection Points)",
    explanation: "Primary HRF metric capturing direction changes in successive RR intervals. Unlike traditional HRV, HRF reflects non-autonomic irregularity in cardiac rhythm.",
    normalRange: "Normal: 40-55% | Elevated AF risk: >60%",
    clinicalSignificance: "Per Costa et al. (2017, 2021), elevated PIP (>60%) predicts atrial fibrillation independently of traditional HRV measures. Higher values indicate more fragmented, irregular rhythm.",
  },
};

// Mock HRV data for demonstration
const mockHRVResult: HRVAnalysisResult = {
  recording_time: new Date().toISOString(),
  duration_minutes: 5.2,
  total_beats: 312,
  artifact_percentage: 2.3,
  time_domain: {
    mean_hr: 62,
    sdnn: 58.4,
    rmssd: 42.3,
    pnn50: 28.5,
    pnn20: 48.2,
    cvnn: 8.2,
    mean_rr: 968,
    sdsd: 41.8,
    nn50: 89,
    nn20: 150,
  },
  frequency_domain: {
    vlf_power: 1240,
    lf_power: 980,
    hf_power: 720,
    total_power: 2940,
    lf_nu: 57.6,
    hf_nu: 42.4,
    lf_hf_ratio: 1.36,
    vlf_peak: 0.025,
    lf_peak: 0.08,
    hf_peak: 0.22,
  },
  nonlinear: {
    sd1: 29.9,
    sd2: 74.8,
    sd1_sd2_ratio: 0.4,
    dfa_alpha1: 1.05,
    dfa_alpha2: 0.92,
    sample_entropy: 1.42,
    approximate_entropy: 1.18,
  },
  hrf: {
    pip: 52.4,
    pip_h: 31.2,
    pip_s: 21.2,
    ials: 0.38,
    pss: 45.6,
    pas: 28.3,
    quality_ok: true,
  },
  quality_score: 0.92,
  analysis_method: "welch",
};

// Metric Card Component with comprehensive scientific tooltips
function MetricCard({
  title,
  value,
  unit,
  description,
  metricKey,
  icon: Icon,
  color = "text-primary",
}: {
  title: string;
  value: number | null;
  unit: string;
  description?: string;
  metricKey?: string;
  icon: React.ElementType;
  color?: string;
}) {
  const explanation = metricKey ? METRIC_EXPLANATIONS[metricKey] : null;

  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${color}`} />
          <span className="text-sm font-medium">{title}</span>
        </div>
        {explanation && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="text-muted-foreground hover:text-foreground transition-colors">
                  <HelpCircle className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-sm p-4">
                <div className="space-y-2">
                  <p className="font-semibold text-sm">{explanation.title}</p>
                  <p className="text-xs text-muted-foreground">{explanation.explanation}</p>
                  <div className="text-xs">
                    <span className="font-medium text-success">Normal Range: </span>
                    <span className="text-muted-foreground">{explanation.normalRange}</span>
                  </div>
                  <p className="text-xs text-muted-foreground italic">{explanation.clinicalSignificance}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(1) : "N/A"}
        <span className="text-sm font-normal text-muted-foreground ml-1">
          {unit}
        </span>
      </p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      )}
    </div>
  );
}

// PSD Spectrum Chart
function PSDChart({ data }: { data: HRVAnalysisResult }) {
  const fd = data.frequency_domain;

  const option: any = {
    title: {
      text: "Power Spectral Density",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 50 },
    xAxis: {
      type: "category" as const,
      data: ["VLF", "LF", "HF"],
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value" as const,
      name: "Power (ms²)",
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "bar",
        data: [
          {
            value: fd.vlf_power ?? 0,
            itemStyle: { color: SCIENTIFIC_COLORS.info },
          },
          {
            value: fd.lf_power ?? 0,
            itemStyle: { color: SCIENTIFIC_COLORS.warning },
          },
          {
            value: fd.hf_power ?? 0,
            itemStyle: { color: SCIENTIFIC_COLORS.success },
          },
        ],
        barWidth: "50%",
        label: {
          show: true,
          position: "top",
          color: SCIENTIFIC_COLORS.textPrimary,
          formatter: (params: any) => params.value.toFixed(0),
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: any) => {
        const p = params[0];
        return `${p.name}: ${p.value.toFixed(1)} ms²`;
      },
    },
  };

  return <EChartsWrapper option={option} height={280} />;
}

// Poincaré Plot
function PoincarePlot({ data }: { data: HRVAnalysisResult }) {
  const nl = data.nonlinear;

  // Generate mock Poincaré points
  const points = React.useMemo(() => {
    const result: [number, number][] = [];
    const meanRR = data.time_domain.mean_rr ?? 900;
    const sd1 = nl.sd1 ?? 30;
    const sd2 = nl.sd2 ?? 60;

    for (let i = 0; i < 200; i++) {
      const angle = Math.random() * 2 * Math.PI;
      const r1 = Math.random() * sd1;
      const r2 = Math.random() * sd2;
      const x = meanRR + r2 * Math.cos(angle) * 0.707 - r1 * Math.sin(angle) * 0.707;
      const y = meanRR + r2 * Math.cos(angle) * 0.707 + r1 * Math.sin(angle) * 0.707;
      result.push([x, y]);
    }
    return result;
  }, [nl.sd1, nl.sd2, data.time_domain.mean_rr]);

  const option: any = {
    title: {
      text: "Poincaré Plot",
      subtext: `SD1: ${nl.sd1?.toFixed(1)} ms | SD2: ${nl.sd2?.toFixed(1)} ms`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: { left: 60, right: 30, top: 60, bottom: 50 },
    xAxis: {
      type: "value" as const,
      name: "RR(n) ms",
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value" as const,
      name: "RR(n+1) ms",
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: 4,
        itemStyle: {
          color: SCIENTIFIC_COLORS.primary,
          opacity: 0.6,
        },
      },
    ],
    tooltip: {
      trigger: "item",
      formatter: (params: any) =>
        `RR(n): ${params.value[0].toFixed(0)} ms<br/>RR(n+1): ${params.value[1].toFixed(0)} ms`,
    },
  };

  return <EChartsWrapper option={option} height={300} />;
}

// HRF Radar Chart
function HRFRadar({ hrf }: { hrf: HRFMetrics }) {
  const option: any = {
    title: {
      text: "Heart Rate Fragmentation",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    radar: {
      indicator: [
        { name: "PIP", max: 100 },
        { name: "PIP-H", max: 100 },
        { name: "PIP-S", max: 100 },
        { name: "PSS", max: 100 },
        { name: "PAS", max: 100 },
      ],
      axisName: { color: SCIENTIFIC_COLORS.textPrimary },
      splitArea: { areaStyle: { color: ["rgba(39, 174, 96, 0.05)", "rgba(39, 174, 96, 0.1)"] } },
    },
    series: [
      {
        type: "radar" as const,
        data: [
          {
            value: [
              hrf.pip ?? 0,
              hrf.pip_h ?? 0,
              hrf.pip_s ?? 0,
              hrf.pss ?? 0,
              hrf.pas ?? 0,
            ],
            name: "HRF Metrics",
            areaStyle: { opacity: 0.3, color: SCIENTIFIC_COLORS.primary },
            lineStyle: { color: SCIENTIFIC_COLORS.primary },
            itemStyle: { color: SCIENTIFIC_COLORS.primary },
          },
        ],
      },
    ],
    tooltip: {
      trigger: "item" as const,
    },
  };

  return <EChartsWrapper option={option} height={280} />;
}

export default function HRVAnalysisPage() {
  const [data, setData] = React.useState<HRVAnalysisResult>(mockHRVResult);
  const [loading, setLoading] = React.useState(false);

  return (
    <PageWrapper
      title="HRV Analysis"
      description="Comprehensive Heart Rate Variability Analysis"
    >
      <div className="space-y-6">
        {/* Recording Info */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {data.duration_minutes?.toFixed(1)} min
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Heart className="h-3 w-3" />
              {data.total_beats} beats
            </Badge>
            <Badge
              variant={
                (data.artifact_percentage ?? 0) < 5 ? "success" : "warning"
              }
            >
              {data.artifact_percentage?.toFixed(1)}% artifacts
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">
              <Upload className="h-4 w-4 mr-2" />
              Upload RR Data
            </Button>
            <Button disabled={loading}>
              <RefreshCw
                className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`}
              />
              Analyze
            </Button>
          </div>
        </motion.div>

        {/* Time Domain */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-primary" />
                Time Domain
              </CardTitle>
              <CardDescription>
                Statistical measures of RR interval variability
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                  title="SDNN"
                  value={data.time_domain.sdnn}
                  unit="ms"
                  description="Overall HRV"
                  metricKey="sdnn"
                  icon={Activity}
                  color="text-primary"
                />
                <MetricCard
                  title="RMSSD"
                  value={data.time_domain.rmssd}
                  unit="ms"
                  description="Parasympathetic"
                  metricKey="rmssd"
                  icon={Heart}
                  color="text-success"
                />
                <MetricCard
                  title="pNN50"
                  value={data.time_domain.pnn50}
                  unit="%"
                  description="Vagal tone"
                  metricKey="pnn50"
                  icon={Zap}
                  color="text-warning"
                />
                <MetricCard
                  title="Mean HR"
                  value={data.time_domain.mean_hr}
                  unit="bpm"
                  description="Heart rate"
                  icon={Heart}
                  color="text-danger"
                />
              </div>
              
              {/* Clinical Interpretation Panel */}
              <div className="mt-4 p-4 rounded-lg bg-muted/50 border">
                <div className="flex items-start gap-3">
                  <Info className="h-5 w-5 text-info mt-0.5 flex-shrink-0" />
                  <div className="space-y-2 text-sm">
                    <p className="font-medium">Clinical Interpretation</p>
                    <p className="text-muted-foreground">
                      {data.time_domain.rmssd !== null && data.time_domain.rmssd > 40
                        ? "RMSSD indicates healthy parasympathetic (vagal) tone. Values above 40ms in short-term recordings suggest adequate recovery capacity."
                        : data.time_domain.rmssd !== null && data.time_domain.rmssd < 20
                          ? "Low RMSSD may indicate reduced vagal tone. Consider factors like recent stress, poor sleep, or overtraining."
                          : "RMSSD is within moderate range. Continue monitoring for personal baseline establishment."}
                    </p>
                    <p className="text-xs text-muted-foreground italic">
                      Reference: Task Force (1996). Heart rate variability: standards of measurement. Circulation, 93(5), 1043-1065.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Frequency Domain */}
        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="h-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Waves className="h-5 w-5 text-info" />
                  Frequency Domain
                </CardTitle>
                <CardDescription>
                  Spectral analysis of HRV (Welch method)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PSDChart data={data} />
                <Separator className="my-4" />
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">LF/HF</p>
                    <p className="text-lg font-bold">
                      {data.frequency_domain.lf_hf_ratio?.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">LF n.u.</p>
                    <p className="text-lg font-bold">
                      {data.frequency_domain.lf_nu?.toFixed(1)}%
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">HF n.u.</p>
                    <p className="text-lg font-bold">
                      {data.frequency_domain.hf_nu?.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card className="h-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Network className="h-5 w-5 text-purple-500" />
                  Nonlinear Analysis
                </CardTitle>
                <CardDescription>
                  Poincaré plot and fractal indices
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PoincarePlot data={data} />
                <Separator className="my-4" />
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">DFA α1</p>
                    <p className="text-lg font-bold">
                      {data.nonlinear.dfa_alpha1?.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">SampEn</p>
                    <p className="text-lg font-bold">
                      {data.nonlinear.sample_entropy?.toFixed(2)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">SD1/SD2</p>
                    <p className="text-lg font-bold">
                      {data.nonlinear.sd1_sd2_ratio?.toFixed(2)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* HRF Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-orange-500" />
                Heart Rate Fragmentation (HRF)
              </CardTitle>
              <CardDescription>
                Non-autonomic components of HRV — predictive of AF (PROOF-AF
                Study, 2025)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 lg:grid-cols-2">
                <HRFRadar hrf={data.hrf} />
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <MetricCard
                      title="PIP"
                      value={data.hrf.pip}
                      unit="%"
                      description="Inflection points"
                      icon={Zap}
                      color="text-orange-500"
                    />
                    <MetricCard
                      title="IALS"
                      value={data.hrf.ials}
                      unit=""
                      description="Segment inverse length"
                      icon={Activity}
                      color="text-orange-500"
                    />
                    <MetricCard
                      title="PSS"
                      value={data.hrf.pss}
                      unit="%"
                      description="Short segments"
                      icon={BarChart3}
                      color="text-orange-500"
                    />
                    <MetricCard
                      title="PAS"
                      value={data.hrf.pas}
                      unit="%"
                      description="Alternating segments"
                      icon={Network}
                      color="text-orange-500"
                    />
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-sm font-medium">Clinical Note</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Higher HRF values (especially PIP &gt; 60%) are associated
                      with increased risk of atrial fibrillation. HRF captures
                      cardiac rhythm irregularity not explained by autonomic
                      modulation.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Scientific References */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Scientific References</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                • Task Force (1996). Heart rate variability: standards of
                measurement, physiological interpretation, and clinical use.
                <span className="ml-1 text-primary">Circulation, 93(5), 1043-1065.</span>
              </p>
              <p>
                • Shaffer & Ginsberg (2017). An overview of heart rate
                variability metrics and norms.
                <span className="ml-1 text-primary">
                  Front Public Health, 5, 258.
                </span>
              </p>
              <p>
                • Costa et al. (2017). Heart Rate Fragmentation: A New Approach
                to Cardiac Interbeat Interval Dynamics.
                <span className="ml-1 text-primary">Front Physiol, 8, 255.</span>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
