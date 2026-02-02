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
import { getHRVNonlinear } from "@/lib/research-api";
import type { NonlinearResponse } from "@/types/research";
import { COMPLEXITY_COLORS } from "@/types/research";

const DEMO_USER_ID = "demo-user";

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
  const value = alpha1 ?? 1;
  const hasData = alpha1 !== null;

  const getColor = (a: number) => {
    if (a < 0.65) return SCIENTIFIC_COLORS.danger;
    if (a <= 1.0) return SCIENTIFIC_COLORS.success;
    if (a <= 1.35) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
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
        max: 2,
        splitNumber: 4,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.325, SCIENTIFIC_COLORS.danger],
              [0.5, SCIENTIFIC_COLORS.success],
              [0.675, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: { color: hasData ? getColor(value) : "#94a3b8" },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: { borderWidth: 3, borderColor: hasData ? getColor(value) : "#94a3b8", color: "#fff" },
        },
        axisTick: { show: true, splitNumber: 2, length: 8, distance: 5, lineStyle: { color: "#64748b", width: 1 } },
        splitLine: { show: true, length: 15, distance: 5, lineStyle: { color: "#475569", width: 2 } },
        axisLabel: { distance: 30, color: "#1e293b", fontSize: 12, fontWeight: "600" },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? value.toFixed(2) : "—"),
          fontSize: 38,
          fontWeight: "bold",
          color: hasData ? getColor(value) : "#94a3b8",
          offsetCenter: [0, "30%"],
        },
        data: [{ value }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={260} showToolbox={false} />;
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

export default function NonlinearPage() {
  const [data, setData] = React.useState<NonlinearResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getHRVNonlinear(DEMO_USER_ID);
      if (result.rr_n.length === 0) {
        // Generate demo data
        const meanRR = 870;
        const sd1 = 32;
        const sd2 = 78;
        const n = 400;
        const rr_n: number[] = [];
        const rr_n1: number[] = [];
        
        for (let i = 0; i < n; i++) {
          const angle = Math.random() * 2 * Math.PI;
          const r1 = Math.random() * sd1;
          const r2 = Math.random() * sd2;
          const x = meanRR + r2 * Math.cos(angle) * 0.707 - r1 * Math.sin(angle) * 0.707;
          const y = meanRR + r2 * Math.cos(angle) * 0.707 + r1 * Math.sin(angle) * 0.707;
          rr_n.push(x);
          rr_n1.push(y);
        }

        const demoData: NonlinearResponse = {
          rr_n,
          rr_n1,
          sd1,
          sd2,
          sd1_sd2_ratio: sd1 / sd2,
          ellipse: { center_x: meanRR, center_y: meanRR, width: 2 * sd2, height: 2 * sd1, angle: 45 },
          dfa_alpha1: 1.05,
          dfa_alpha2: 0.92,
          dfa_alpha1_interpretation: "Normal fractal scaling (healthy heart)",
          sample_entropy: 1.42,
          approximate_entropy: 1.18,
          complexity_state: "normal",
          interpretation: ["Nonlinear dynamics within normal range", "DFA α1 indicates healthy fractal correlation"],
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

        {data && (
          <>
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
