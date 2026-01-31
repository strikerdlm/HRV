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
import { getHRVSpaceWeatherCorrelations } from "@/lib/research-api";
import type { CorrelationAnalysisResult, CorrelationResult } from "@/types/research";
import { SOLAR_METRIC_INFO, HRV_METRIC_INFO } from "@/types/research";

// Significance colors
const significanceColors: Record<string, string> = {
  not_significant: "#888888",
  marginal: SCIENTIFIC_COLORS.warning,
  significant: SCIENTIFIC_COLORS.success,
  highly_significant: SCIENTIFIC_COLORS.primary,
  very_highly_significant: "#8e44ad",
};

// Correlation strength badge
function StrengthBadge({ strength }: { strength: string }) {
  const variants: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
    negligible: "secondary",
    weak: "outline",
    moderate: "warning",
    strong: "success",
    very_strong: "destructive",
  };
  return <Badge variant={variants[strength] || "secondary"}>{strength}</Badge>;
}

// Correlation Heatmap Chart
function CorrelationHeatmap({
  correlations,
}: {
  correlations: CorrelationResult[];
}) {
  // Build heatmap data
  const solarMetrics = Array.from(new Set(correlations.map((c) => c.solar_metric)));
  const physioMetrics = Array.from(new Set(correlations.map((c) => c.physio_metric)));

  const data: [number, number, number][] = [];
  correlations.forEach((c) => {
    const x = solarMetrics.indexOf(c.solar_metric);
    const y = physioMetrics.indexOf(c.physio_metric);
    if (x >= 0 && y >= 0) {
      data.push([x, y, c.r]);
    }
  });

  const option: any = {
    title: {
      text: "Solar-HRV Correlation Matrix",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
    },
    grid: { left: 100, right: 80, top: 50, bottom: 80 },
    xAxis: {
      type: "category" as const,
      data: solarMetrics.map((m) => SOLAR_METRIC_INFO[m]?.name || m),
      axisLabel: {
        color: SCIENTIFIC_COLORS.textPrimary,
        rotate: 30,
        fontSize: 10,
      },
    },
    yAxis: {
      type: "category" as const,
      data: physioMetrics.map((m) => HRV_METRIC_INFO[m]?.name || m),
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 10 },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "vertical",
      right: 10,
      top: "center",
      inRange: {
        color: [SCIENTIFIC_COLORS.danger, "#ffffff", SCIENTIFIC_COLORS.success],
      },
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "heatmap",
        data: data,
        label: {
          show: true,
          formatter: (params: any) => params.value[2].toFixed(2),
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 10,
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0, 0, 0, 0.5)" },
        },
      },
    ],
    tooltip: {
      formatter: (params: any) => {
        const [x, y, r] = params.value;
        return `${solarMetrics[x]} ↔ ${physioMetrics[y]}<br/>r = ${r.toFixed(3)}`;
      },
    },
  };

  return <EChartsWrapper option={option} height={320} />;
}

// Lag Analysis Chart
function LagAnalysisChart({
  correlations,
}: {
  correlations: CorrelationResult[];
}) {
  // Group by lag
  const lagData: Record<number, number[]> = {};
  correlations.forEach((c) => {
    if (!lagData[c.lag_hours]) lagData[c.lag_hours] = [];
    lagData[c.lag_hours].push(Math.abs(c.r));
  });

  const lags = Object.keys(lagData)
    .map(Number)
    .sort((a, b) => a - b);
  const avgCorrelations = lags.map(
    (lag) => lagData[lag].reduce((a, b) => a + b, 0) / lagData[lag].length
  );

  const option: any = {
    title: {
      text: "Average |r| by Lag Time",
      subtext: "Optimal lag: strongest correlations",
      textStyle: { color: SCIENTIFIC_COLORS.textPrimary, fontSize: 14 },
      subtextStyle: { color: SCIENTIFIC_COLORS.textSecondary },
    },
    grid: { left: 50, right: 30, top: 60, bottom: 50 },
    xAxis: {
      type: "category" as const,
      data: lags.map((l) => `${l}h`),
      name: "Lag (hours)",
      nameLocation: "middle",
      nameGap: 30,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    yAxis: {
      type: "value" as const,
      name: "Mean |r|",
      min: 0,
      max: 0.5,
      axisLabel: { color: SCIENTIFIC_COLORS.textPrimary },
      nameTextStyle: { color: SCIENTIFIC_COLORS.textPrimary },
    },
    series: [
      {
        type: "line",
        data: avgCorrelations,
        smooth: true,
        areaStyle: { opacity: 0.2, color: SCIENTIFIC_COLORS.primary },
        lineStyle: { color: SCIENTIFIC_COLORS.primary, width: 2 },
        itemStyle: { color: SCIENTIFIC_COLORS.primary },
        markPoint: {
          data: [{ type: "max", name: "Optimal Lag" }],
          label: { color: SCIENTIFIC_COLORS.textPrimary },
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      formatter: (params: any) =>
        `Lag: ${params[0].name}<br/>Mean |r|: ${params[0].value.toFixed(3)}`,
    },
  };

  return <EChartsWrapper option={option} height={280} />;
}

// Correlation Result Card
function CorrelationCard({ result }: { result: CorrelationResult }) {
  const solarInfo = SOLAR_METRIC_INFO[result.solar_metric];
  const hrvInfo = HRV_METRIC_INFO[result.physio_metric];

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 rounded-lg border bg-card"
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sun className="h-4 w-4 text-warning" />
            <span className="font-medium">
              {solarInfo?.name || result.solar_metric}
            </span>
            <span className="text-muted-foreground">↔</span>
            <Heart className="h-4 w-4 text-danger" />
            <span className="font-medium">
              {hrvInfo?.name || result.physio_metric}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-3 w-3" />
            Lag: {result.lag_hours}h | n = {result.n_samples}
          </div>
        </div>
        <div className="text-right">
          <p
            className="text-xl font-bold"
            style={{ color: result.r > 0 ? SCIENTIFIC_COLORS.success : SCIENTIFIC_COLORS.danger }}
          >
            r = {result.r.toFixed(3)}
          </p>
          <p className="text-xs text-muted-foreground">
            p = {result.p_value.toFixed(4)}
          </p>
        </div>
      </div>
      <Separator className="my-3" />
      <div className="flex items-center justify-between">
        <StrengthBadge strength={result.strength} />
        <Badge
          style={{
            backgroundColor: significanceColors[result.significance] + "20",
            color: significanceColors[result.significance],
          }}
        >
          {result.significance.replace("_", " ")}
        </Badge>
      </div>
      {result.interpretation && (
        <p className="text-sm text-muted-foreground mt-3">
          {result.interpretation}
        </p>
      )}
    </motion.div>
  );
}

export default function CorrelationsPage() {
  const [data, setData] = React.useState<CorrelationAnalysisResult | null>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchCorrelations = async () => {
    setLoading(true);
    try {
      const result = await getHRVSpaceWeatherCorrelations();
      setData(result);
    } catch (error) {
      console.error("Failed to fetch correlations:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchCorrelations();
  }, []);

  return (
    <PageWrapper
      title="Solar-HRV Correlations"
      description="Analyze relationships between space weather and physiological parameters"
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
                <Badge variant="outline">
                  {data.n_days} days analyzed
                </Badge>
                <Badge variant="success" className="flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" />
                  {data.significant_correlations.length} significant
                </Badge>
                {data.optimal_lag_hours !== null && (
                  <Badge variant="info" className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Optimal lag: {data.optimal_lag_hours}h
                  </Badge>
                )}
              </>
            )}
          </div>
          <Button onClick={fetchCorrelations} disabled={loading}>
            <RefreshCw
              className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Run Analysis
          </Button>
        </motion.div>

        {/* Charts Row */}
        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card className="h-full">
              <CardContent className="pt-6">
                {data && data.all_correlations.length > 0 ? (
                  <CorrelationHeatmap correlations={data.all_correlations} />
                ) : (
                  <div className="flex items-center justify-center h-[320px] text-muted-foreground">
                    No correlation data available
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card className="h-full">
              <CardContent className="pt-6">
                {data && data.all_correlations.length > 0 ? (
                  <LagAnalysisChart correlations={data.all_correlations} />
                ) : (
                  <div className="flex items-center justify-center h-[280px] text-muted-foreground">
                    No lag data available
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Significant Correlations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitCompare className="h-5 w-5 text-primary" />
                Significant Correlations
              </CardTitle>
              <CardDescription>
                Correlations with p &lt; 0.05
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data?.significant_correlations.map((corr, idx) => (
                  <CorrelationCard key={idx} result={corr} />
                ))}
                {(!data || data.significant_correlations.length === 0) && (
                  <div className="col-span-full text-center py-8 text-muted-foreground">
                    <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p>No significant correlations found</p>
                    <p className="text-sm">
                      Accumulate more data points for robust analysis
                    </p>
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
            transition={{ delay: 0.4 }}
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
                  {data?.pattern_insights.map((insight, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-success mt-0.5 flex-shrink-0" />
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
            transition={{ delay: 0.5 }}
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
                  {data?.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Scientific Context */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Scientific Background</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                <strong>Geomagnetic Activity & ANS:</strong> Multiple studies
                have documented associations between geomagnetic disturbances
                (measured by Kp, Dst indices) and autonomic nervous system
                activity. Effects typically appear with 12-36 hour delays.
              </p>
              <p>
                <strong>Correlation Interpretation:</strong> Due to the
                complexity of physiological regulation, even modest correlations
                (r = 0.2-0.4) may be biologically meaningful. Individual
                sensitivity varies considerably.
              </p>
              <p>
                <strong>Causality Note:</strong> Correlations do not imply
                causation. Multiple confounding factors (sleep, activity,
                stress) should be controlled when interpreting results.
              </p>
              <Separator className="my-3" />
              <p className="text-xs">
                References: Alabdulgader et al. (2018), Stoupel et al. (2008),
                Otsuka et al. (2001)
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
