// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Network,
  Activity,
  RefreshCw,
  Info,
  TrendingUp,
  Sparkles,
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
import { QualityPanel } from "@/components/research/quality-panel";
import {
  getHRVNonlinear,
  getAnalysisSettings,
  type AnalysisSettings,
} from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { NonlinearResponse } from "@/types/research";
import { COMPLEXITY_COLORS } from "@/types/research";

// Default user ID when no user is selected
const DEFAULT_USER_ID = "demo-user";

// Poincare Plot with Ellipse
function PoincareChart({ data }: { data: NonlinearResponse }) {
  const ellipse = data.ellipse;
  
  // Generate ellipse points
  const ellipsePoints = React.useMemo(() => {
    if (!ellipse) return [];
    const points: [number, number][] = [];
    for (let i = 0; i <= 100; i++) {
      const angle = (i / 100) * 2 * Math.PI;
      const x = ellipse.center_x + (ellipse.width / 2) * Math.cos(angle) * Math.cos(Math.PI / 4)
                - (ellipse.height / 2) * Math.sin(angle) * Math.sin(Math.PI / 4);
      const y = ellipse.center_y + (ellipse.width / 2) * Math.cos(angle) * Math.sin(Math.PI / 4)
                + (ellipse.height / 2) * Math.sin(angle) * Math.cos(Math.PI / 4);
      points.push([x, y]);
    }
    return points;
  }, [ellipse]);

  const option: Record<string, unknown> = {
    title: {
      text: "Poincaré Plot",
      subtext: `SD1: ${data.sd1?.toFixed(1) ?? "—"} ms | SD2: ${data.sd2?.toFixed(1) ?? "—"} ms`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: { left: 70, right: 30, top: 70, bottom: 60 },
    xAxis: {
      type: "value",
      name: "RR(n) ms",
      nameLocation: "middle",
      nameGap: 35,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: "RR(n+1) ms",
      nameLocation: "middle",
      nameGap: 50,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      // Scatter points
      {
        type: "scatter",
        data: data.rr_n.map((rr, i) => [rr, data.rr_n1[i]]),
        symbolSize: 4,
        itemStyle: { color: SCIENTIFIC_COLORS.primary, opacity: 0.6 },
      },
      // SD1/SD2 Ellipse
      {
        type: "line",
        data: ellipsePoints,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.danger, type: "dashed" },
      },
      // Identity line
      {
        type: "line",
        data: data.rr_n.length > 0
          ? [[Math.min(...data.rr_n), Math.min(...data.rr_n)], [Math.max(...data.rr_n), Math.max(...data.rr_n)]]
          : [[700, 700], [1100, 1100]],
        symbol: "none",
        lineStyle: { width: 1, color: "#94a3b8", type: "dotted" },
      },
    ],
    tooltip: {
      trigger: "item",
      formatter: (params: { value: [number, number] }) =>
        `RR(n): ${params.value[0].toFixed(0)} ms<br/>RR(n+1): ${params.value[1].toFixed(0)} ms`,
    },
  };

  return <EChartsWrapper option={option} height={400} />;
}

// DFA Gauge
function DFAGauge({ alpha1, alpha2 }: { alpha1: number | null; alpha2: number | null }) {
  const value = alpha1 ?? 0;
  const hasData = alpha1 !== null;
  const max = 2;
  const clamped = Math.max(0, Math.min(value, max));
  const circumference = 2 * Math.PI * 40;
  const dash = (clamped / max) * circumference;

  const getColor = (a: number) => {
    if (a < 0.65) return SCIENTIFIC_COLORS.danger;
    if (a <= 1.0) return SCIENTIFIC_COLORS.success;
    if (a <= 1.35) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  return (
    <div className="flex flex-col items-center justify-center py-3">
      <div className="relative w-28 h-28">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 96 96">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-muted/30"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${dash} ${circumference}`}
            className={hasData ? "" : "text-muted/50"}
            style={{ color: hasData ? getColor(value) : "#94a3b8" }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-2xl font-bold"
            style={{ color: hasData ? getColor(value) : "#94a3b8" }}
          >
            {hasData ? value.toFixed(2) : "—"}
          </span>
          <span className="text-[10px] text-muted-foreground">α1</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        α2: {alpha2 !== null ? alpha2.toFixed(2) : "—"}
      </p>
    </div>
  );
}

// Entropy Display
function EntropyCard({ label, value, description }: { label: string; value: number | null; description: string }) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-4 w-4 text-purple-500" />
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(2) : "—"}
      </p>
      <p className="text-xs text-muted-foreground mt-1">{description}</p>
    </div>
  );
}

function MetricCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
  description,
}: {
  title: string;
  value: number | null;
  unit?: string;
  icon: React.ElementType;
  color: string;
  description?: string;
}) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-sm font-medium">{title}</span>
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(2) : "—"}
        {unit && <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>}
      </p>
      {description && <p className="text-xs text-muted-foreground mt-1">{description}</p>}
    </div>
  );
}

function AdvancedCurveChart({
  title,
  xLabel,
  yLabel,
  xValues,
  yValues,
  color,
}: {
  title: string;
  xLabel: string;
  yLabel: string;
  xValues: number[];
  yValues: number[];
  color: string;
}) {
  const option: Record<string, unknown> = {
    title: {
      text: title,
      left: "center",
      textStyle: { color: "#1a1a1a", fontSize: 13, fontWeight: "bold" },
    },
    grid: { left: 55, right: 20, top: 45, bottom: 50, containLabel: true },
    xAxis: {
      type: "value",
      name: xLabel,
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    yAxis: {
      type: "value",
      name: yLabel,
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "line",
        data: xValues.map((x, idx) => [x, yValues[idx] ?? 0]),
        smooth: true,
        symbolSize: 6,
        lineStyle: { color, width: 2 },
        itemStyle: { color },
      },
    ],
  };
  return <EChartsWrapper option={option} height={260} showToolbox={false} />;
}

// Informs users that nonlinear metrics use a bounded window, and which window
// suits their recording. Caps are server-configured (env-tunable); see API
// /api/research/analysis-settings.
function AnalysisSettingsPanel({ settings }: { settings: AnalysisSettings | null }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Info className="h-5 w-5 text-primary" />
          Analysis Window &amp; Performance
        </CardTitle>
        <CardDescription>
          Nonlinear metrics (SampEn, ApEn, RQA, MFDFA) are computed on a bounded
          window so analysis stays fast on long recordings. Time- and
          frequency-domain metrics always use the full recording.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">
            Nonlinear window:{" "}
            {settings ? `${settings.max_nonlinear_samples.toLocaleString()} beats` : "—"}
          </Badge>
          <Badge variant="outline">
            MFDFA scales: {settings ? settings.max_mfdfa_scales : "—"}
          </Badge>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th className="py-1 pr-4 font-medium">Recording</th>
                <th className="py-1 pr-4 font-medium">Recommended window</th>
                <th className="py-1 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-t border-border">
                <td className="py-1 pr-4">Short clinical (5–10 min)</td>
                <td className="py-1 pr-4">Default (4000)</td>
                <td className="py-1">Whole recording is used; no truncation.</td>
              </tr>
              <tr className="border-t border-border">
                <td className="py-1 pr-4">Ambulatory / multi-hour wearable</td>
                <td className="py-1 pr-4">4000 (default)</td>
                <td className="py-1">Fast and representative of short-term dynamics.</td>
              </tr>
              <tr className="border-t border-border">
                <td className="py-1 pr-4">24 h Holter</td>
                <td className="py-1 pr-4">4000–5000</td>
                <td className="py-1">
                  Raise toward 10000 only if you need longer-range complexity and
                  can accept slower runs.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-muted-foreground">
          Set on the server via{" "}
          <code className="rounded bg-muted px-1 py-0.5">
            {settings?.nonlinear_samples_env ?? "HRV_MAX_NONLINEAR_SAMPLES"}
          </code>{" "}
          (256–10000, default 4000) and{" "}
          <code className="rounded bg-muted px-1 py-0.5">
            {settings?.mfdfa_scales_env ?? "HRV_MFDFA_MAX_SCALES"}
          </code>{" "}
          (8–1000, default 100). Higher values capture more detail but take
          longer; out-of-range values are clamped.
        </p>
      </CardContent>
    </Card>
  );
}

export default function NonlinearPage() {
  const [data, setData] = React.useState<NonlinearResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [settings, setSettings] = React.useState<AnalysisSettings | null>(null);

  // Get user ID from global store
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getHRVNonlinear(userId);
      setData(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  React.useEffect(() => {
    getAnalysisSettings()
      .then(setSettings)
      .catch(() => setSettings(null));
  }, []);

  return (
    <PageWrapper
      title="Nonlinear Analysis"
      description="Poincaré Plot, DFA, and Entropy Measures"
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
              <Badge
                variant="outline"
                style={{
                  borderColor: COMPLEXITY_COLORS[data.complexity_state],
                  color: COMPLEXITY_COLORS[data.complexity_state],
                }}
              >
                Complexity: {data.complexity_state}
              </Badge>
            )}
          </div>
          <Button onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </motion.div>

        {/* Analysis window & performance settings guidance */}
        <AnalysisSettingsPanel settings={settings} />

        {data && (
          <>
            <QualityPanel context={data.context} />

            {/* Poincare Plot */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Network className="h-5 w-5 text-primary" />
                    Poincaré Plot
                  </CardTitle>
                  <CardDescription>
                    Return map showing RR(n) vs RR(n+1). Ellipse width = 2×SD2, height = 2×SD1.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PoincareChart data={data} />
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <MetricCard title="SD1" value={data.sd1} unit="ms" icon={Activity} color="text-primary" description="Short-term variability" />
                    <MetricCard title="SD2" value={data.sd2} unit="ms" icon={TrendingUp} color="text-info" description="Long-term variability" />
                    <MetricCard title="SD1/SD2" value={data.sd1_sd2_ratio} icon={Network} color="text-purple-500" description="Ratio (parasympath. index)" />
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* DFA and Entropy */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-success" />
                      Detrended Fluctuation Analysis
                    </CardTitle>
                    <CardDescription>
                      Fractal scaling exponents measuring self-similarity
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <DFAGauge alpha1={data.dfa_alpha1} alpha2={data.dfa_alpha2} />
                    <div className="text-center mt-2">
                      <p className="text-sm font-medium">DFA α1</p>
                      <p className="text-xs text-muted-foreground">{data.dfa_alpha1_interpretation ?? "—"}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3 mt-4">
                      <div className="text-center p-3 rounded-lg border">
                        <p className="text-xs text-muted-foreground">α1 (4-11 beats)</p>
                        <p className="text-xl font-bold">{data.dfa_alpha1?.toFixed(2) ?? "—"}</p>
                      </div>
                      <div className="text-center p-3 rounded-lg border">
                        <p className="text-xs text-muted-foreground">α2 (&gt;11 beats)</p>
                        <p className="text-xl font-bold">{data.dfa_alpha2?.toFixed(2) ?? "—"}</p>
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
                      <Sparkles className="h-5 w-5 text-purple-500" />
                      Entropy Measures
                    </CardTitle>
                    <CardDescription>
                      Complexity and irregularity of the time series
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <EntropyCard
                        label="Sample Entropy"
                        value={data.sample_entropy}
                        description="Lower values = more regular/predictable"
                      />
                      <EntropyCard
                        label="Approximate Entropy"
                        value={data.approximate_entropy}
                        description="Similar to SampEn, includes self-matches"
                      />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-warning" />
                    Advanced Cognitive Discriminators (RCMSE + MM-DFA)
                  </CardTitle>
                  <CardDescription>
                    Enabled only when data sufficiency and QC gates pass (minimum {data.min_samples_required ?? 400} RR samples).
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {data.advanced_metrics_enabled ? (
                    <div className="grid gap-6 lg:grid-cols-2">
                      <AdvancedCurveChart
                        title={`RCMSE (Ei: ${data.rcmse_ei?.toFixed(3) ?? "—"})`}
                        xLabel="Scale (tau)"
                        yLabel="Entropy"
                        xValues={data.rcmse_tau ?? []}
                        yValues={data.rcmse_curve ?? []}
                        color={SCIENTIFIC_COLORS.warning}
                      />
                      <AdvancedCurveChart
                        title={`MM-DFA (MFI: ${data.mfi?.toFixed(3) ?? "—"})`}
                        xLabel="Scale"
                        yLabel="Fluctuation"
                        xValues={data.mmdfa_scales ?? []}
                        yValues={data.mmdfa_curve ?? []}
                        color={SCIENTIFIC_COLORS.info}
                      />
                    </div>
                  ) : (
                    <div className="p-4 rounded-lg border bg-muted/40">
                      <p className="text-sm text-muted-foreground">
                        Advanced metrics are gated off due to insufficient clean data or failed stationarity/QC checks.
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Interpretation */}
            {data.interpretation.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Info className="h-5 w-5 text-info" />
                      Interpretation
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {data.interpretation.map((note, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-info">•</span>
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
                  <CardTitle>Scientific References</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • Brennan et al. (2001). Do existing measures of Poincaré plot geometry reflect nonlinear features?
                    <span className="ml-1 text-primary">IEEE Trans Biomed Eng, 48(11), 1342-7.</span>
                  </p>
                  <p>
                    • Peng et al. (1995). Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series.
                    <span className="ml-1 text-primary">Chaos, 5(1), 82-7.</span>
                  </p>
                  <p>
                    • Richman & Moorman (2000). Physiological time-series analysis using approximate entropy and sample entropy.
                    <span className="ml-1 text-primary">Am J Physiol Heart Circ Physiol, 278(6), H2039-49.</span>
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
