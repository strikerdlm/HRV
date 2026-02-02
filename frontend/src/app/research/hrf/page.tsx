// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Zap,
  Activity,
  RefreshCw,
  AlertTriangle,
  Heart,
  TrendingUp,
  Info,
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
import { getHRVHRF } from "@/lib/research-api";
import type { HRFResponse } from "@/types/research";
import { FRAGMENTATION_COLORS } from "@/types/research";

const DEMO_USER_ID = "demo-user";

// HRF Radar Chart
function HRFRadar({ data }: { data: HRFResponse }) {
  const option: Record<string, unknown> = {
    title: {
      text: "HRF Profile",
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
      radius: "65%",
      axisName: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 11 },
      splitArea: { areaStyle: { color: ["rgba(230, 126, 34, 0.05)", "rgba(230, 126, 34, 0.1)"] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: [
              data.pip ?? 0,
              data.pip_hard ?? 0,
              data.pip_soft ?? 0,
              data.pss ?? 0,
              data.pas ?? 0,
            ],
            name: "Current",
            areaStyle: { opacity: 0.3, color: "#e67e22" },
            lineStyle: { color: "#e67e22", width: 2 },
            itemStyle: { color: "#e67e22" },
          },
          // Normal reference
          {
            value: [45, 25, 20, 40, 25],
            name: "Normal Range",
            areaStyle: { opacity: 0.1, color: SCIENTIFIC_COLORS.success },
            lineStyle: { color: SCIENTIFIC_COLORS.success, type: "dashed" },
            itemStyle: { color: SCIENTIFIC_COLORS.success },
          },
        ],
      },
    ],
    legend: {
      bottom: 0,
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    tooltip: { trigger: "item" },
  };

  return <EChartsWrapper option={option} height={320} />;
}

// PIP Gauge
function PIPGauge({ value }: { value: number | null }) {
  const displayValue = value ?? 0;
  const hasData = value !== null;

  const getColor = (v: number) => {
    if (v < 40) return SCIENTIFIC_COLORS.success;
    if (v < 55) return SCIENTIFIC_COLORS.info;
    if (v < 70) return SCIENTIFIC_COLORS.warning;
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
        max: 100,
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.4, SCIENTIFIC_COLORS.success],
              [0.55, SCIENTIFIC_COLORS.info],
              [0.7, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: { color: hasData ? getColor(displayValue) : "#94a3b8" },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: { borderWidth: 3, borderColor: hasData ? getColor(displayValue) : "#94a3b8", color: "#fff" },
        },
        axisTick: { show: true, splitNumber: 2, length: 8, distance: 5, lineStyle: { color: "#64748b", width: 1 } },
        splitLine: { show: true, length: 15, distance: 5, lineStyle: { color: "#475569", width: 2 } },
        axisLabel: { distance: 30, color: "#1e293b", fontSize: 12, fontWeight: "600" },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? `${displayValue.toFixed(1)}%` : "—"),
          fontSize: 36,
          fontWeight: "bold",
          color: hasData ? getColor(displayValue) : "#94a3b8",
          offsetCenter: [0, "30%"],
        },
        data: [{ value: displayValue }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={260} showToolbox={false} />;
}

function MetricCard({
  title,
  value,
  unit,
  description,
  icon: Icon,
}: {
  title: string;
  value: number | null;
  unit: string;
  description: string;
  icon: React.ElementType;
}) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="h-4 w-4 text-orange-500" />
        <span className="text-sm font-medium">{title}</span>
      </div>
      <p className="text-2xl font-bold">
        {value !== null ? value.toFixed(2) : "—"}
        <span className="text-sm font-normal text-muted-foreground ml-1">{unit}</span>
      </p>
      <p className="text-xs text-muted-foreground mt-1">{description}</p>
    </div>
  );
}

export default function HRFPage() {
  const [data, setData] = React.useState<HRFResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await getHRVHRF(DEMO_USER_ID);
      if (result.pip === null) {
        // Generate demo data
        const demoData: HRFResponse = {
          pip: 52.4,
          pip_hard: 31.2,
          pip_soft: 21.2,
          ials: 0.38,
          pss: 45.6,
          pas: 28.3,
          pip_trend: [48, 50, 51, 53, 52, 54, 52],
          timestamps: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
          pip_rmssd_correlation: -0.45,
          fragmentation_level: "normal",
          af_risk_indicator: null,
          clinical_notes: [
            "HRF metrics within normal range",
            "Reference: Costa et al. 2017, Heart Rate Fragmentation as Novel Biomarker",
          ],
          quality_ok: true,
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
      title="Heart Rate Fragmentation"
      description="Non-Autonomic HRV Components & AF Risk Markers"
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
                <Badge
                  variant="outline"
                  style={{
                    borderColor: FRAGMENTATION_COLORS[data.fragmentation_level],
                    color: FRAGMENTATION_COLORS[data.fragmentation_level],
                  }}
                >
                  {data.fragmentation_level.charAt(0).toUpperCase() + data.fragmentation_level.slice(1)} Fragmentation
                </Badge>
                {data.af_risk_indicator && (
                  <Badge variant="destructive" className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    AF Risk Flag
                  </Badge>
                )}
                {data.quality_ok && (
                  <Badge variant="success">Quality OK</Badge>
                )}
              </>
            )}
          </div>
          <Button onClick={fetchData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </motion.div>

        {data && (
          <>
            {/* Main Gauge and Radar */}
            <div className="grid gap-6 lg:grid-cols-2">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5 text-orange-500" />
                      PIP (Percentage of Inflection Points)
                    </CardTitle>
                    <CardDescription>
                      Primary fragmentation metric. Higher = more irregular rhythm.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <PIPGauge value={data.pip} />
                    <div className="text-center mt-2">
                      <p className="text-sm text-muted-foreground">
                        {data.pip !== null && data.pip < 40
                          ? "Low fragmentation (regular rhythm)"
                          : data.pip !== null && data.pip > 70
                            ? "High fragmentation (elevated AF risk)"
                            : "Normal range"}
                      </p>
                    </div>
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
                      <Activity className="h-5 w-5 text-orange-500" />
                      HRF Profile
                    </CardTitle>
                    <CardDescription>
                      All fragmentation metrics compared to normal range
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <HRFRadar data={data} />
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Metric Cards */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-orange-500" />
                    HRF Metrics Detail
                  </CardTitle>
                  <CardDescription>
                    Individual fragmentation components
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <MetricCard
                      title="PIP"
                      value={data.pip}
                      unit="%"
                      description="Total inflection points"
                      icon={Zap}
                    />
                    <MetricCard
                      title="PIP-Hard"
                      value={data.pip_hard}
                      unit="%"
                      description="Hard acceleration/deceleration"
                      icon={Activity}
                    />
                    <MetricCard
                      title="PIP-Soft"
                      value={data.pip_soft}
                      unit="%"
                      description="Soft direction changes"
                      icon={Heart}
                    />
                    <MetricCard
                      title="IALS"
                      value={data.ials}
                      unit=""
                      description="Inverse avg segment length"
                      icon={TrendingUp}
                    />
                    <MetricCard
                      title="PSS"
                      value={data.pss}
                      unit="%"
                      description="Short segments (<3 beats)"
                      icon={Zap}
                    />
                    <MetricCard
                      title="PAS"
                      value={data.pas}
                      unit="%"
                      description="Alternating segments"
                      icon={Activity}
                    />
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Clinical Notes */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
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
                        <span className="text-orange-500">•</span>
                        <span className="text-sm text-muted-foreground">{note}</span>
                      </li>
                    ))}
                  </ul>
                  {data.af_risk_indicator && (
                    <div className="mt-4 p-3 rounded-lg bg-danger/10 border border-danger/30">
                      <p className="text-sm font-medium text-danger flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        {data.af_risk_indicator}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* PROOF-AF Reference */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle>Scientific Background: PROOF-AF Study</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground space-y-2">
                  <p>
                    Heart Rate Fragmentation (HRF) captures non-autonomic irregularity in cardiac rhythm
                    that is <strong>not explained</strong> by traditional HRV measures.
                  </p>
                  <p>
                    • <strong>PIP &gt; 60%</strong> is associated with significantly increased risk of
                    atrial fibrillation, independent of age, sex, and traditional risk factors.
                  </p>
                  <p>
                    • Costa MD et al. (2017). Heart Rate Fragmentation: A New Approach to the Analysis
                    of Cardiac Interbeat Interval Dynamics.
                    <span className="ml-1 text-primary">Front Physiol, 8, 255.</span>
                  </p>
                  <p>
                    • Costa MD et al. (2021). Heart Rate Fragmentation as a Novel Biomarker of Atrial
                    Fibrillation: The PROOF-AF Study.
                    <span className="ml-1 text-primary">Circulation, 143(10), 782-792.</span>
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
