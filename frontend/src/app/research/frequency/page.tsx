// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Waves,
  Activity,
  Zap,
  RefreshCw,
  Info,
  PieChart,
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
import { Separator } from "@/components/ui/separator";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { getHRVFrequency } from "@/lib/research-api";
import type { FrequencyDomainResponse } from "@/types/research";

const DEMO_USER_ID = "demo-user";

// LF/HF Ratio Gauge
function LFHFGauge({ ratio }: { ratio: number | null }) {
  const value = ratio ?? 1;
  const hasData = ratio !== null;

  const getColor = (r: number) => {
    if (r < 0.5) return SCIENTIFIC_COLORS.info; // Parasympathetic dominant
    if (r <= 2.0) return SCIENTIFIC_COLORS.success; // Balanced
    return SCIENTIFIC_COLORS.warning; // Sympathetic dominant
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
        max: 5,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.2, SCIENTIFIC_COLORS.info],
              [0.5, SCIENTIFIC_COLORS.success],
              [1, SCIENTIFIC_COLORS.warning],
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
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getColor(value) : "#94a3b8",
            color: "#fff",
          },
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

// PSD Line Chart
function PSDChart({ data }: { data: FrequencyDomainResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "Power Spectral Density",
      subtext: `Method: ${data.method}`,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: { left: 70, right: 30, top: 70, bottom: 60 },
    xAxis: {
      type: "value",
      name: "Frequency (Hz)",
      nameLocation: "middle",
      nameGap: 35,
      min: 0,
      max: 0.5,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value",
      name: "Power (ms²/Hz)",
      nameLocation: "middle",
      nameGap: 50,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: data.frequencies.length > 0
          ? data.frequencies.map((f, i) => [f, data.psd[i]])
          : [[0, 0]],
        smooth: true,
        symbol: "none",
        lineStyle: { width: 2, color: SCIENTIFIC_COLORS.primary },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(52, 152, 219, 0.4)" },
              { offset: 1, color: "rgba(52, 152, 219, 0.05)" },
            ],
          },
        },
        markArea: {
          silent: true,
          data: [
            [{ xAxis: 0.003, itemStyle: { color: "rgba(155, 89, 182, 0.15)" } }, { xAxis: 0.04 }],
            [{ xAxis: 0.04, itemStyle: { color: "rgba(241, 196, 15, 0.15)" } }, { xAxis: 0.15 }],
            [{ xAxis: 0.15, itemStyle: { color: "rgba(39, 174, 96, 0.15)" } }, { xAxis: 0.4 }],
          ],
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: unknown[]) => {
        const p = params as Array<{ value: [number, number] }>;
        if (p[0]) {
          return `Freq: ${p[0].value[0].toFixed(3)} Hz<br/>Power: ${p[0].value[1].toFixed(1)} ms²/Hz`;
        }
        return "";
      },
    },
  };

  return <EChartsWrapper option={option} height={350} />;
}

// Band Power Bar Chart
function BandPowerChart({ data }: { data: FrequencyDomainResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "Frequency Band Powers",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: ["VLF\n(0.003-0.04 Hz)", "LF\n(0.04-0.15 Hz)", "HF\n(0.15-0.4 Hz)"],
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, interval: 0 },
    },
    yAxis: {
      type: "value",
      name: "Power (ms²)",
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "bar",
        data: [
          { value: data.vlf?.power_ms2 ?? 0, itemStyle: { color: "#9b59b6" } },
          { value: data.lf?.power_ms2 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.warning } },
          { value: data.hf?.power_ms2 ?? 0, itemStyle: { color: SCIENTIFIC_COLORS.success } },
        ],
        barWidth: "50%",
        label: {
          show: true,
          position: "top",
          color: SCIENTIFIC_COLORS.textPrimary,
          formatter: (p: { value: number }) => p.value.toFixed(0),
        },
      },
    ],
    tooltip: { trigger: "axis" },
  };

  return <EChartsWrapper option={option} height={280} />;
}

// Pie Chart for Normalized Units
function NormalizedPieChart({ data }: { data: FrequencyDomainResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "Normalized Power",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "55%"],
        data: [
          { value: data.lf_nu ?? 50, name: "LF n.u.", itemStyle: { color: SCIENTIFIC_COLORS.warning } },
          { value: data.hf_nu ?? 50, name: "HF n.u.", itemStyle: { color: SCIENTIFIC_COLORS.success } },
        ],
        label: {
          color: SCIENTIFIC_COLORS.textPrimary,
          formatter: "{b}: {c}%",
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0, 0, 0, 0.5)" },
        },
      },
    ],
    tooltip: {
      trigger: "item",
      formatter: "{b}: {c}% ({d}%)",
    },
  };

  return <EChartsWrapper option={option} height={280} />;
}

// Radar Chart
function BalanceRadar({ data }: { data: FrequencyDomainResponse }) {
  const total = data.total_power ?? 1;
  
  const option: Record<string, unknown> = {
    title: {
      text: "Autonomic Balance",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    radar: {
      indicator: [
        { name: "VLF %", max: 100 },
        { name: "LF %", max: 100 },
        { name: "HF %", max: 100 },
        { name: "LF n.u.", max: 100 },
        { name: "HF n.u.", max: 100 },
      ],
      axisName: { color: SCIENTIFIC_COLORS.textPrimary },
      splitArea: { areaStyle: { color: ["rgba(52, 152, 219, 0.05)", "rgba(52, 152, 219, 0.1)"] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [
              ((data.vlf?.power_ms2 ?? 0) / total) * 100,
              ((data.lf?.power_ms2 ?? 0) / total) * 100,
              ((data.hf?.power_ms2 ?? 0) / total) * 100,
              data.lf_nu ?? 0,
              data.hf_nu ?? 0,
            ],
            name: "Current",
            areaStyle: { opacity: 0.3, color: SCIENTIFIC_COLORS.primary },
            lineStyle: { color: SCIENTIFIC_COLORS.primary },
            itemStyle: { color: SCIENTIFIC_COLORS.primary },
          },
        ],
      },
    ],
    tooltip: { trigger: "item" },
  };

  return <EChartsWrapper option={option} height={280} />;
}

function MetricBadge({ label, value, unit, color }: { label: string; value: number | null; unit: string; color: string }) {
  return (
    <div className="text-center p-3 rounded-lg border bg-card">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-bold" style={{ color }}>
        {value !== null ? value.toFixed(1) : "—"}
        <span className="text-xs font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
    </div>
  );
}

export default function FrequencyPage() {
  const [data, setData] = React.useState<FrequencyDomainResponse | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [method, setMethod] = React.useState<"welch" | "periodogram" | "ar">("welch");

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getHRVFrequency(DEMO_USER_ID, method);
      if (!result.vlf && !result.lf && !result.hf) {
        // Generate demo data
        const demoData: FrequencyDomainResponse = {
          frequencies: Array.from({ length: 100 }, (_, i) => i * 0.005),
          psd: Array.from({ length: 100 }, (_, i) => {
            const f = i * 0.005;
            if (f < 0.04) return 500 + Math.random() * 200;
            if (f < 0.15) return 800 + Math.random() * 400 - (f - 0.04) * 3000;
            if (f < 0.4) return 600 + Math.random() * 300 - (f - 0.15) * 2000;
            return 50 + Math.random() * 50;
          }),
          vlf: { power_ms2: 1240, power_pct: 42, peak_hz: 0.025, normalized_units: null },
          lf: { power_ms2: 980, power_pct: 33, peak_hz: 0.08, normalized_units: 57.6 },
          hf: { power_ms2: 720, power_pct: 25, peak_hz: 0.22, normalized_units: 42.4 },
          total_power: 2940,
          lf_hf_ratio: 1.36,
          lf_nu: 57.6,
          hf_nu: 42.4,
          method: "welch",
          window_length: 256,
          autonomic_balance: "balanced",
          clinical_notes: [],
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
  }, [method]);

  React.useEffect(() => {
    fetchData();
  }, [fetchData]);

  const getBalanceColor = (balance: string) => {
    switch (balance) {
      case "parasympathetic": return "text-info";
      case "sympathetic": return "text-warning";
      default: return "text-success";
    }
  };

  return (
    <PageWrapper
      title="Frequency Domain Analysis"
      description="Power Spectral Density and Autonomic Balance"
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
                <Badge variant="outline">Method: {data.method}</Badge>
                <Badge
                  variant="outline"
                  className={getBalanceColor(data.autonomic_balance)}
                >
                  {data.autonomic_balance.charAt(0).toUpperCase() + data.autonomic_balance.slice(1)}
                </Badge>
                <Badge variant="outline">
                  Total Power: {data.total_power?.toFixed(0) ?? "—"} ms²
                </Badge>
              </>
            )}
          </div>
          <div className="flex gap-2">
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as typeof method)}
              className="px-3 py-2 rounded-md border bg-background text-sm"
            >
              <option value="welch">Welch</option>
              <option value="periodogram">Periodogram</option>
              <option value="ar">Autoregressive</option>
            </select>
            <Button onClick={fetchData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Analyze
            </Button>
          </div>
        </motion.div>

        {data && (
          <>
            {/* PSD Chart */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Waves className="h-5 w-5 text-primary" />
                    Power Spectral Density
                  </CardTitle>
                  <CardDescription>
                    Frequency decomposition of HRV. Shaded regions: VLF (purple), LF (yellow), HF (green)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <PSDChart data={data} />
                </CardContent>
              </Card>
            </motion.div>

            {/* Band Powers and Gauge */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Activity className="h-5 w-5 text-info" />
                      Band Powers
                    </CardTitle>
                    <CardDescription>
                      Absolute power in each frequency band
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <BandPowerChart data={data} />
                    <div className="grid grid-cols-3 gap-3 mt-4">
                      <MetricBadge label="VLF Peak" value={data.vlf?.peak_hz ?? null} unit="Hz" color="#9b59b6" />
                      <MetricBadge label="LF Peak" value={data.lf?.peak_hz ?? null} unit="Hz" color={SCIENTIFIC_COLORS.warning} />
                      <MetricBadge label="HF Peak" value={data.hf?.peak_hz ?? null} unit="Hz" color={SCIENTIFIC_COLORS.success} />
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
                      <Zap className="h-5 w-5 text-warning" />
                      LF/HF Ratio
                    </CardTitle>
                    <CardDescription>
                      Sympathovagal balance indicator (interpret with caution)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <LFHFGauge ratio={data.lf_hf_ratio} />
                    <div className="text-center mt-2">
                      <p className="text-sm text-muted-foreground">
                        {data.lf_hf_ratio !== null && data.lf_hf_ratio < 0.5
                          ? "Parasympathetic dominant"
                          : data.lf_hf_ratio !== null && data.lf_hf_ratio > 2.0
                            ? "Sympathetic dominant"
                            : "Balanced autonomic tone"}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Normalized Units and Radar */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <PieChart className="h-5 w-5 text-success" />
                      Normalized Units
                    </CardTitle>
                    <CardDescription>
                      LF and HF as percentage of (LF + HF)
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <NormalizedPieChart data={data} />
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
                      <Activity className="h-5 w-5 text-purple-500" />
                      Balance Profile
                    </CardTitle>
                    <CardDescription>
                      Multi-dimensional autonomic profile
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <BalanceRadar data={data} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Clinical Notes */}
            {data.clinical_notes.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Info className="h-5 w-5 text-info" />
                      Clinical Notes
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {data.clinical_notes.map((note, idx) => (
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
              transition={{ delay: 0.7 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Scientific References</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    • Task Force (1996). HRV standards: VLF (0.003-0.04 Hz), LF (0.04-0.15 Hz), HF (0.15-0.4 Hz).
                    <span className="ml-1 text-primary">Circulation, 93(5), 1043-1065.</span>
                  </p>
                  <p>
                    • Billman (2013). LF/HF ratio does not accurately measure sympathetic-vagal balance.
                    <span className="ml-1 text-primary">Front Physiol, 4, 26.</span>
                  </p>
                  <p>
                    • Shaffer & Ginsberg (2017). HF power reflects parasympathetic (vagal) activity; LF is mixed.
                    <span className="ml-1 text-primary">Front Public Health, 5, 258.</span>
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
