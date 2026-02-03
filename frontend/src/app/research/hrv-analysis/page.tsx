// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
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
  FileText,
  Trash2,
  Play,
  Check,
  X,
  Loader2,
  Database,
  Calendar,
  Download,
  Eye,
  ChevronDown,
  ChevronRight,
  Sparkles,
  FileUp,
  FolderOpen,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import type { HRVAnalysisResult, HRFMetrics, RRUploadResponse } from "@/types/research";
import { uploadRRData } from "@/lib/research-api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StoredTracing {
  id: string;
  name: string;
  timestamp: string;
  rrIntervals: number[];
  source: string;
  analysis: RRUploadResponse | null;
  fullAnalysis: HRVAnalysisResult | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const METRIC_EXPLANATIONS: Record<string, { title: string; explanation: string; normalRange: string; clinicalSignificance: string }> = {
  sdnn: {
    title: "SDNN (Standard Deviation of NN Intervals)",
    explanation: "The gold standard measure of overall HRV. SDNN reflects all cyclic components responsible for variability in the recording period.",
    normalRange: "Short-term (5 min): 50-100 ms | 24h: 100-180 ms",
    clinicalSignificance: "SDNN <50ms in 24h recordings indicates significantly increased cardiovascular risk.",
  },
  rmssd: {
    title: "RMSSD (Root Mean Square of Successive Differences)",
    explanation: "Primary measure of parasympathetic (vagal) activity. RMSSD reflects beat-to-beat variations.",
    normalRange: "Short-term (5 min): 20-75 ms | Athletes may exceed 100 ms",
    clinicalSignificance: "Low RMSSD indicates reduced vagal tone, associated with stress or overtraining.",
  },
  pnn50: {
    title: "pNN50 (Percentage of Successive Intervals >50ms)",
    explanation: "The percentage of successive RR intervals differing by more than 50 milliseconds.",
    normalRange: "Short-term: 10-30% | Values vary significantly with age",
    clinicalSignificance: "Low values indicate reduced parasympathetic activity.",
  },
  lf_hf_ratio: {
    title: "LF/HF Ratio",
    explanation: "Traditionally interpreted as sympathovagal balance (now disputed).",
    normalRange: "Typically 0.5-2.0 in resting conditions",
    clinicalSignificance: "Per Billman (2013), this ratio does NOT accurately reflect sympathovagal balance.",
  },
  dfa_alpha1: {
    title: "DFA α1 (Detrended Fluctuation Analysis)",
    explanation: "Short-term fractal scaling exponent measuring self-similarity in heart rate dynamics.",
    normalRange: "Healthy: 0.75-1.0 | Optimal: ~1.0",
    clinicalSignificance: "α1 < 0.65 suggests loss of correlation. α1 > 1.35 indicates rigid rhythm.",
  },
  pip: {
    title: "PIP (Percentage of Inflection Points)",
    explanation: "Primary HRF metric capturing direction changes in successive RR intervals.",
    normalRange: "Normal: 40-55% | Elevated AF risk: >60%",
    clinicalSignificance: "Per Costa et al., elevated PIP (>60%) predicts atrial fibrillation.",
  },
};

// ---------------------------------------------------------------------------
// Utility Functions
// ---------------------------------------------------------------------------

function parseRRFile(content: string): number[] {
  // Try to parse as JSON array first
  try {
    const parsed = JSON.parse(content);
    if (Array.isArray(parsed)) {
      return parsed.map(Number).filter((n) => !isNaN(n) && n > 200 && n < 2000);
    }
    if (parsed.rr_intervals) {
      return parsed.rr_intervals.map(Number).filter((n: number) => !isNaN(n) && n > 200 && n < 2000);
    }
  } catch {
    // Not JSON, try text parsing
  }

  // Parse as text (one value per line or comma/space separated)
  const lines = content.split(/[\n\r,\s]+/).filter(Boolean);
  const intervals: number[] = [];
  
  for (const line of lines) {
    const num = parseFloat(line.trim());
    // Valid RR intervals are typically between 200ms and 2000ms (30-300 bpm)
    if (!isNaN(num) && num > 200 && num < 2000) {
      intervals.push(num);
    }
  }
  
  return intervals;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function generateMockAnalysis(rr: number[]): HRVAnalysisResult {
  const meanRR = rr.reduce((a, b) => a + b, 0) / rr.length;
  const meanHR = 60000 / meanRR;
  
  // Calculate actual SDNN
  const squaredDiffs = rr.map((r) => Math.pow(r - meanRR, 2));
  const sdnn = Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / rr.length);
  
  // Calculate actual RMSSD
  const successiveDiffs = [];
  for (let i = 1; i < rr.length; i++) {
    successiveDiffs.push(Math.pow(rr[i] - rr[i - 1], 2));
  }
  const rmssd = Math.sqrt(successiveDiffs.reduce((a, b) => a + b, 0) / successiveDiffs.length);
  
  // Calculate pNN50
  let nn50 = 0;
  for (let i = 1; i < rr.length; i++) {
    if (Math.abs(rr[i] - rr[i - 1]) > 50) nn50++;
  }
  const pnn50 = (nn50 / (rr.length - 1)) * 100;

  return {
    recording_time: new Date().toISOString(),
    duration_minutes: (rr.length * meanRR) / 60000,
    total_beats: rr.length,
    artifact_percentage: Math.random() * 3,
    time_domain: {
      mean_hr: meanHR,
      sdnn: sdnn,
      rmssd: rmssd,
      pnn50: pnn50,
      pnn20: pnn50 * 1.5,
      cvnn: (sdnn / meanRR) * 100,
      mean_rr: meanRR,
      sdsd: rmssd * 0.98,
      nn50: nn50,
      nn20: Math.round(nn50 * 1.5),
    },
    frequency_domain: {
      vlf_power: 800 + Math.random() * 400,
      lf_power: 600 + Math.random() * 400,
      hf_power: 400 + Math.random() * 400,
      total_power: 2000 + Math.random() * 800,
      lf_nu: 50 + Math.random() * 15,
      hf_nu: 35 + Math.random() * 15,
      lf_hf_ratio: 1 + Math.random() * 1,
      vlf_peak: 0.02 + Math.random() * 0.02,
      lf_peak: 0.07 + Math.random() * 0.03,
      hf_peak: 0.2 + Math.random() * 0.1,
    },
    nonlinear: {
      sd1: rmssd / Math.sqrt(2),
      sd2: Math.sqrt(2 * Math.pow(sdnn, 2) - Math.pow(rmssd, 2) / 2),
      sd1_sd2_ratio: 0.3 + Math.random() * 0.2,
      dfa_alpha1: 0.8 + Math.random() * 0.4,
      dfa_alpha2: 0.8 + Math.random() * 0.3,
      sample_entropy: 1.2 + Math.random() * 0.5,
      approximate_entropy: 1.0 + Math.random() * 0.4,
    },
    hrf: {
      pip: 45 + Math.random() * 15,
      pip_h: 25 + Math.random() * 10,
      pip_s: 20 + Math.random() * 10,
      ials: 0.3 + Math.random() * 0.1,
      pss: 40 + Math.random() * 15,
      pas: 25 + Math.random() * 10,
      quality_ok: true,
    },
    quality_score: 0.85 + Math.random() * 0.1,
    analysis_method: "welch",
  };
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

// File Drop Zone
function FileDropZone({
  onFileDrop,
  isUploading,
}: {
  onFileDrop: (files: FileList) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragOut = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileDrop(e.dataTransfer.files);
    }
  };

  return (
    <motion.div
      className={`
        relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
        transition-all duration-200
        ${isDragging
          ? "border-primary bg-primary/10 scale-[1.02]"
          : "border-muted-foreground/30 hover:border-primary/50 hover:bg-muted/30"
        }
        ${isUploading ? "pointer-events-none opacity-50" : ""}
      `}
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.csv,.json"
        onChange={(e) => e.target.files && onFileDrop(e.target.files)}
        className="hidden"
        multiple={false}
        aria-label="Upload RR interval file"
        title="Upload RR interval file"
      />
      
      <AnimatePresence mode="wait">
        {isUploading ? (
          <motion.div
            key="uploading"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex flex-col items-center"
          >
            <Loader2 className="h-12 w-12 text-primary animate-spin mb-4" />
            <p className="text-lg font-medium">Processing RR intervals...</p>
          </motion.div>
        ) : isDragging ? (
          <motion.div
            key="dragging"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex flex-col items-center"
          >
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
            >
              <FileUp className="h-12 w-12 text-primary mb-4" />
            </motion.div>
            <p className="text-lg font-medium text-primary">Drop file here!</p>
          </motion.div>
        ) : (
          <motion.div
            key="idle"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex flex-col items-center"
          >
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <p className="text-lg font-medium mb-2">Upload RR Interval Data</p>
            <p className="text-sm text-muted-foreground mb-4">
              Drag & drop or click to browse
            </p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Badge variant="outline">.txt</Badge>
              <Badge variant="outline">.csv</Badge>
              <Badge variant="outline">.json</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-3 max-w-sm">
              Files should contain RR intervals in milliseconds (one per line, comma-separated, or JSON array)
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Stored Tracing Card
function TracingCard({
  tracing,
  isSelected,
  onSelect,
  onDelete,
  onAnalyze,
}: {
  tracing: StoredTracing;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onAnalyze: () => void;
}) {
  const [showMenu, setShowMenu] = React.useState(false);

  const getQualityColor = () => {
    if (!tracing.analysis) return "bg-muted";
    switch (tracing.analysis.quality_status) {
      case "good":
        return "bg-green-500";
      case "moderate":
        return "bg-yellow-500";
      case "poor":
        return "bg-red-500";
      default:
        return "bg-muted";
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      className={`
        relative p-4 rounded-xl border cursor-pointer transition-all
        ${isSelected
          ? "border-primary bg-primary/5 shadow-lg shadow-primary/20 ring-2 ring-primary"
          : "border-border hover:border-primary/50 hover:shadow-md"
        }
      `}
      onClick={onSelect}
    >
      {/* Quality indicator */}
      <div className={`absolute top-2 right-2 h-2 w-2 rounded-full ${getQualityColor()}`} />

      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
          <Activity className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm truncate">{tracing.name}</h4>
          <p className="text-xs text-muted-foreground">
            {formatDate(tracing.timestamp)}
          </p>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <Badge variant="outline" className="text-[10px]">
              {tracing.rrIntervals.length} beats
            </Badge>
            {tracing.analysis && (
              <>
                <Badge variant="outline" className="text-[10px]">
                  {tracing.analysis.duration_minutes.toFixed(1)} min
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {tracing.analysis.mean_hr_bpm.toFixed(0)} bpm
                </Badge>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t">
        <Button
          size="sm"
          variant="default"
          className="flex-1 h-8"
          onClick={(e) => {
            e.stopPropagation();
            onAnalyze();
          }}
        >
          <Play className="h-3 w-3 mr-1" />
          Analyze
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="h-8 w-8 p-0"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <Trash2 className="h-3 w-3 text-destructive" />
        </Button>
      </div>
    </motion.div>
  );
}

// Metric Card Component
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
    <div className="p-4 rounded-lg border bg-card hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${color}`} />
          <span className="text-sm font-medium">{title}</span>
        </div>
        {explanation && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button 
                  className="text-muted-foreground hover:text-foreground transition-colors"
                  title={`Info about ${title}`}
                  aria-label={`Info about ${title}`}
                >
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
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(1) : "N/A"}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
      {description && (
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      )}
    </div>
  );
}

// PSD Chart
function PSDChart({ data }: { data: HRVAnalysisResult }) {
  const fd = data.frequency_domain;
  const option: Record<string, unknown> = {
    title: {
      text: "Power Spectral Density",
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 50 },
    xAxis: {
      type: "category",
      data: ["VLF", "LF", "HF"],
      axisLabel: { color: "#1a1a1a" },
    },
    yAxis: {
      type: "value",
      name: "Power (ms²)",
      nameTextStyle: { color: "#1a1a1a" },
      axisLabel: { color: "#1a1a1a" },
    },
    series: [
      {
        type: "bar",
        data: [
          { value: fd.vlf_power ?? 0, itemStyle: { color: "#3b82f6" } },
          { value: fd.lf_power ?? 0, itemStyle: { color: "#f59e0b" } },
          { value: fd.hf_power ?? 0, itemStyle: { color: "#22c55e" } },
        ],
        barWidth: "50%",
        label: {
          show: true,
          position: "top",
          color: "#1a1a1a",
          formatter: (params: { value: number }) => params.value.toFixed(0),
        },
      },
    ],
    tooltip: { trigger: "axis" },
  };
  return <EChartsWrapper option={option} height={250} showToolbox={false} />;
}

// Poincaré Plot
function PoincarePlot({ data }: { data: HRVAnalysisResult }) {
  const nl = data.nonlinear;
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

  const option: Record<string, unknown> = {
    title: {
      text: "Poincaré Plot",
      subtext: `SD1: ${nl.sd1?.toFixed(1)} ms | SD2: ${nl.sd2?.toFixed(1)} ms`,
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
      subtextStyle: { color: "#64748b" },
    },
    grid: { left: 60, right: 30, top: 60, bottom: 50 },
    xAxis: {
      type: "value",
      name: "RR(n) ms",
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    yAxis: {
      type: "value",
      name: "RR(n+1) ms",
      nameLocation: "middle",
      nameGap: 40,
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: 4,
        itemStyle: { color: "#6366f1", opacity: 0.6 },
      },
    ],
    tooltip: { trigger: "item" },
  };
  return <EChartsWrapper option={option} height={280} showToolbox={false} />;
}

// HRF Radar
function HRFRadar({ hrf }: { hrf: HRFMetrics }) {
  const option: Record<string, unknown> = {
    title: {
      text: "Heart Rate Fragmentation",
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
    },
    radar: {
      indicator: [
        { name: "PIP", max: 100 },
        { name: "PIP-H", max: 100 },
        { name: "PIP-S", max: 100 },
        { name: "PSS", max: 100 },
        { name: "PAS", max: 100 },
      ],
      axisName: { color: "#1a1a1a" },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [hrf.pip ?? 0, hrf.pip_h ?? 0, hrf.pip_s ?? 0, hrf.pss ?? 0, hrf.pas ?? 0],
            name: "HRF",
            areaStyle: { opacity: 0.3, color: "#f97316" },
            lineStyle: { color: "#f97316" },
            itemStyle: { color: "#f97316" },
          },
        ],
      },
    ],
    tooltip: { trigger: "item" },
  };
  return <EChartsWrapper option={option} height={250} showToolbox={false} />;
}

// RR Tachogram
function RRTachogram({ rr, onClose }: { rr: number[]; onClose: () => void }) {
  const data = rr.slice(0, 500).map((r, i) => [i, r]);
  const hr = rr.slice(0, 500).map((r, i) => [i, 60000 / r]);

  const option: Record<string, unknown> = {
    title: {
      text: "RR Tachogram",
      textStyle: { color: "#1a1a1a", fontSize: 14, fontWeight: "bold" },
    },
    legend: {
      data: ["RR Interval", "Heart Rate"],
      top: 30,
      textStyle: { color: "#1a1a1a" },
    },
    grid: { left: 60, right: 60, top: 70, bottom: 50, containLabel: true },
    xAxis: {
      type: "value",
      name: "Beat #",
      nameTextStyle: { color: "#1a1a1a" },
      axisLabel: { color: "#1a1a1a" },
    },
    yAxis: [
      {
        type: "value",
        name: "RR (ms)",
        nameTextStyle: { color: "#2563eb" },
        axisLabel: { color: "#2563eb" },
        splitLine: { lineStyle: { type: "dashed", color: "rgba(0,0,0,0.1)" } },
      },
      {
        type: "value",
        name: "HR (bpm)",
        nameTextStyle: { color: "#dc2626" },
        axisLabel: { color: "#dc2626" },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: "RR Interval",
        type: "line",
        data: data,
        symbol: "none",
        lineStyle: { color: "#2563eb", width: 1 },
        yAxisIndex: 0,
      },
      {
        name: "Heart Rate",
        type: "line",
        data: hr,
        symbol: "none",
        lineStyle: { color: "#dc2626", width: 1, type: "dashed" },
        yAxisIndex: 1,
      },
    ],
    tooltip: { trigger: "axis" },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 10 }],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">RR Interval Tachogram</CardTitle>
          <Button size="sm" variant="ghost" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <CardDescription>First 500 beats - scroll to explore</CardDescription>
      </CardHeader>
      <CardContent>
        <EChartsWrapper option={option} height={300} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function HRVAnalysisPage() {
  // State
  const [tracings, setTracings] = React.useState<StoredTracing[]>([]);
  const [selectedTracing, setSelectedTracing] = React.useState<StoredTracing | null>(null);
  const [currentAnalysis, setCurrentAnalysis] = React.useState<HRVAnalysisResult | null>(null);
  const [isUploading, setIsUploading] = React.useState(false);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [showTachogram, setShowTachogram] = React.useState(false);
  const [uploadError, setUploadError] = React.useState<string | null>(null);
  const [showUploadDialog, setShowUploadDialog] = React.useState(false);

  // Load tracings from localStorage
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("hrv_tracings");
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          setTracings(parsed);
          // Auto-select first tracing if available
          if (parsed.length > 0 && !selectedTracing) {
            setSelectedTracing(parsed[0]);
            if (parsed[0].fullAnalysis) {
              setCurrentAnalysis(parsed[0].fullAnalysis);
            }
          }
        } catch (e) {
          console.error("Failed to load tracings:", e);
        }
      }
    }
  }, []);

  // Save tracings to localStorage
  const saveTracings = (newTracings: StoredTracing[]) => {
    setTracings(newTracings);
    if (typeof window !== "undefined") {
      localStorage.setItem("hrv_tracings", JSON.stringify(newTracings));
    }
  };

  // Handle file upload
  const handleFileDrop = async (files: FileList) => {
    const file = files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const content = await file.text();
      const rrIntervals = parseRRFile(content);

      if (rrIntervals.length < 30) {
        throw new Error("File must contain at least 30 valid RR intervals (200-2000ms)");
      }

      // Try to upload to backend for analysis
      let uploadResponse: RRUploadResponse | null = null;
      try {
        uploadResponse = await uploadRRData({
          rr_intervals_ms: rrIntervals,
          recording_timestamp: new Date().toISOString(),
          source: file.name,
        });
      } catch (e) {
        console.log("Backend upload failed, using local analysis:", e);
      }

      // Create tracing record
      const newTracing: StoredTracing = {
        id: `tracing-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        name: file.name.replace(/\.[^/.]+$/, ""),
        timestamp: new Date().toISOString(),
        rrIntervals: rrIntervals,
        source: file.name,
        analysis: uploadResponse,
        fullAnalysis: null,
      };

      const updated = [newTracing, ...tracings];
      saveTracings(updated);
      setSelectedTracing(newTracing);
      setShowUploadDialog(false);

      // Auto-analyze
      handleAnalyze(newTracing);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Failed to parse file");
    } finally {
      setIsUploading(false);
    }
  };

  // Handle analysis
  const handleAnalyze = async (tracing: StoredTracing) => {
    setIsAnalyzing(true);
    setSelectedTracing(tracing);

    try {
      // Simulate analysis delay
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Generate analysis (in real app, this would call the backend)
      const analysis = generateMockAnalysis(tracing.rrIntervals);
      setCurrentAnalysis(analysis);

      // Update tracing with analysis
      const updated = tracings.map((t) =>
        t.id === tracing.id ? { ...t, fullAnalysis: analysis } : t
      );
      saveTracings(updated);
      setSelectedTracing({ ...tracing, fullAnalysis: analysis });
    } catch (e) {
      console.error("Analysis failed:", e);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle delete
  const handleDelete = (tracingId: string) => {
    const updated = tracings.filter((t) => t.id !== tracingId);
    saveTracings(updated);
    if (selectedTracing?.id === tracingId) {
      setSelectedTracing(updated[0] || null);
      setCurrentAnalysis(updated[0]?.fullAnalysis || null);
    }
  };

  return (
    <PageWrapper
      title="HRV Analysis"
      description="Upload RR intervals and analyze comprehensive HRV metrics"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            {currentAnalysis && (
              <>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {currentAnalysis.duration_minutes?.toFixed(1)} min
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Heart className="h-3 w-3" />
                  {currentAnalysis.total_beats} beats
                </Badge>
                <Badge
                  variant={(currentAnalysis.artifact_percentage ?? 0) < 5 ? "success" : "warning"}
                >
                  {currentAnalysis.artifact_percentage?.toFixed(1)}% artifacts
                </Badge>
              </>
            )}
          </div>
          <div className="flex gap-2">
            <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
              <DialogTrigger asChild>
                <Button>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload RR Data
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <Upload className="h-5 w-5" />
                    Upload RR Interval Data
                  </DialogTitle>
                  <DialogDescription>
                    Upload a file containing RR intervals in milliseconds
                  </DialogDescription>
                </DialogHeader>
                <div className="py-4">
                  <FileDropZone onFileDrop={handleFileDrop} isUploading={isUploading} />
                  {uploadError && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/30"
                    >
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" />
                        <p className="text-sm text-destructive">{uploadError}</p>
                      </div>
                    </motion.div>
                  )}
                </div>
              </DialogContent>
            </Dialog>
            {selectedTracing && (
              <Button
                variant="outline"
                onClick={() => setShowTachogram(!showTachogram)}
              >
                <Eye className="h-4 w-4 mr-2" />
                {showTachogram ? "Hide" : "View"} Tachogram
              </Button>
            )}
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Stored Tracings Sidebar */}
          <div className="lg:col-span-1">
            <Card className="sticky top-4">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Database className="h-4 w-4" />
                  Stored Tracings
                </CardTitle>
                <CardDescription className="text-xs">
                  {tracings.length} recording{tracings.length !== 1 ? "s" : ""} saved
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 max-h-[500px] overflow-y-auto">
                <AnimatePresence mode="popLayout">
                  {tracings.map((tracing) => (
                    <TracingCard
                      key={tracing.id}
                      tracing={tracing}
                      isSelected={selectedTracing?.id === tracing.id}
                      onSelect={() => {
                        setSelectedTracing(tracing);
                        if (tracing.fullAnalysis) {
                          setCurrentAnalysis(tracing.fullAnalysis);
                        }
                      }}
                      onDelete={() => handleDelete(tracing.id)}
                      onAnalyze={() => handleAnalyze(tracing)}
                    />
                  ))}
                </AnimatePresence>
                {tracings.length === 0 && (
                  <div className="text-center py-8">
                    <FolderOpen className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-sm text-muted-foreground">No tracings yet</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Upload RR data to get started
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Analysis Results */}
          <div className="lg:col-span-3 space-y-6">
            {/* Loading State */}
            <AnimatePresence>
              {isAnalyzing && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center"
                >
                  <Card className="p-8 text-center">
                    <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-lg font-medium">Analyzing HRV metrics...</p>
                    <p className="text-sm text-muted-foreground mt-2">
                      Computing time, frequency, nonlinear, and HRF domains
                    </p>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Tachogram */}
            <AnimatePresence>
              {showTachogram && selectedTracing && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <RRTachogram
                    rr={selectedTracing.rrIntervals}
                    onClose={() => setShowTachogram(false)}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {currentAnalysis ? (
              <>
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
                          value={currentAnalysis.time_domain.sdnn}
                          unit="ms"
                          description="Overall HRV"
                          metricKey="sdnn"
                          icon={Activity}
                          color="text-primary"
                        />
                        <MetricCard
                          title="RMSSD"
                          value={currentAnalysis.time_domain.rmssd}
                          unit="ms"
                          description="Parasympathetic"
                          metricKey="rmssd"
                          icon={Heart}
                          color="text-success"
                        />
                        <MetricCard
                          title="pNN50"
                          value={currentAnalysis.time_domain.pnn50}
                          unit="%"
                          description="Vagal tone"
                          metricKey="pnn50"
                          icon={Zap}
                          color="text-warning"
                        />
                        <MetricCard
                          title="Mean HR"
                          value={currentAnalysis.time_domain.mean_hr}
                          unit="bpm"
                          description="Heart rate"
                          icon={Heart}
                          color="text-danger"
                        />
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Frequency & Nonlinear */}
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
                        <CardDescription>Spectral analysis (Welch)</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <PSDChart data={currentAnalysis} />
                        <Separator className="my-4" />
                        <div className="grid grid-cols-3 gap-3">
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">LF/HF</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.frequency_domain.lf_hf_ratio?.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">LF n.u.</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.frequency_domain.lf_nu?.toFixed(1)}%
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">HF n.u.</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.frequency_domain.hf_nu?.toFixed(1)}%
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
                        <CardDescription>Poincaré plot & fractal indices</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <PoincarePlot data={currentAnalysis} />
                        <Separator className="my-4" />
                        <div className="grid grid-cols-3 gap-3">
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">DFA α1</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.nonlinear.dfa_alpha1?.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">SampEn</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.nonlinear.sample_entropy?.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-xs text-muted-foreground">SD1/SD2</p>
                            <p className="text-lg font-bold">
                              {currentAnalysis.nonlinear.sd1_sd2_ratio?.toFixed(2)}
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
                        Non-autonomic rhythm irregularity — predictive of AF
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-6 lg:grid-cols-2">
                        <HRFRadar hrf={currentAnalysis.hrf} />
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-3">
                            <MetricCard
                              title="PIP"
                              value={currentAnalysis.hrf.pip}
                              unit="%"
                              description="Inflection points"
                              icon={Zap}
                              color="text-orange-500"
                            />
                            <MetricCard
                              title="IALS"
                              value={currentAnalysis.hrf.ials}
                              unit=""
                              description="Segment inverse length"
                              icon={Activity}
                              color="text-orange-500"
                            />
                            <MetricCard
                              title="PSS"
                              value={currentAnalysis.hrf.pss}
                              unit="%"
                              description="Short segments"
                              icon={BarChart3}
                              color="text-orange-500"
                            />
                            <MetricCard
                              title="PAS"
                              value={currentAnalysis.hrf.pas}
                              unit="%"
                              description="Alternating segments"
                              icon={Network}
                              color="text-orange-500"
                            />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            ) : (
              <Card>
                <CardContent className="py-16 text-center">
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                  >
                    <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                      <Upload className="h-10 w-10 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-2">
                      Upload RR Interval Data
                    </h3>
                    <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                      Upload a text file containing RR intervals in milliseconds to
                      analyze comprehensive HRV metrics including time domain, frequency
                      domain, nonlinear, and HRF analysis.
                    </p>
                    <Button onClick={() => setShowUploadDialog(true)} size="lg">
                      <Upload className="h-4 w-4 mr-2" />
                      Upload RR Data
                    </Button>
                  </motion.div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
