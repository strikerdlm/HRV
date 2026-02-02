// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Sun,
  Zap,
  Wind,
  AlertTriangle,
  AlertCircle,
  Clock,
  RefreshCw,
  Activity,
  Radio,
  Compass,
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
import { getCurrentSpaceWeather, refreshSpaceWeather } from "@/lib/research-api";
import type {
  SpaceWeatherSnapshot,
  ImpactPrediction,
  ImpactSeverity,
} from "@/types/research";
import { SEVERITY_COLORS, CATEGORY_ICONS } from "@/types/research";
import { formatDateTime } from "@/lib/utils";

// Severity badge colors
const severityVariants: Record<ImpactSeverity, "success" | "info" | "warning" | "destructive" | "secondary"> = {
  quiet: "success",
  minor: "info",
  moderate: "warning",
  strong: "warning",
  severe: "destructive",
  extreme: "destructive",
};

// Kp Index Gauge - Elegant design with large arc and thin needle
function KpGauge({ value }: { value: number | null }) {
  const displayValue = value ?? 0;
  const hasData = value !== null;
  
  const getKpColor = (kp: number) => {
    if (kp < 4) return SCIENTIFIC_COLORS.success;
    if (kp < 5) return SCIENTIFIC_COLORS.warning;
    if (kp < 7) return "#e67e22";
    return SCIENTIFIC_COLORS.danger;
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "65%"],
        radius: "95%",
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 9,
        splitNumber: 9,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.33, SCIENTIFIC_COLORS.success],
              [0.55, SCIENTIFIC_COLORS.warning],
              [0.77, "#e67e22"],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: {
            color: hasData ? getKpColor(displayValue) : "#94a3b8",
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getKpColor(displayValue) : "#94a3b8",
            color: "#fff",
          },
        },
        axisTick: {
          show: true,
          splitNumber: 1,
          length: 8,
          distance: 5,
          lineStyle: { color: "#64748b", width: 1 },
        },
        splitLine: {
          show: true,
          length: 15,
          distance: 5,
          lineStyle: { color: "#475569", width: 2 },
        },
        axisLabel: {
          distance: 30,
          color: "#1e293b",
          fontSize: 13,
          fontWeight: "600",
        },
        detail: {
          valueAnimation: true,
          formatter: () => hasData ? displayValue.toFixed(1) : "—",
          fontSize: 42,
          fontWeight: "bold",
          color: hasData ? getKpColor(displayValue) : "#94a3b8",
          offsetCenter: [0, "35%"],
        },
        data: [{ value: displayValue }],
      },
    ],
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Compass className="h-5 w-5 text-primary" />
          Kp Index
        </CardTitle>
        <CardDescription>Planetary geomagnetic activity (0-9)</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <EChartsWrapper option={option} height={260} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// Solar Wind Gauge - Elegant design with large arc and thin needle
function SolarWindGauge({
  speed,
  density,
}: {
  speed: number | null;
  density: number | null;
}) {
  const speedValue = speed ?? 350;
  const hasData = speed !== null;
  
  const getWindColor = (v: number) => {
    if (v < 400) return SCIENTIFIC_COLORS.success;
    if (v < 500) return SCIENTIFIC_COLORS.primary;
    if (v < 700) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "65%"],
        radius: "95%",
        startAngle: 180,
        endAngle: 0,
        min: 200,
        max: 900,
        splitNumber: 7,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.29, SCIENTIFIC_COLORS.success],
              [0.43, SCIENTIFIC_COLORS.primary],
              [0.71, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: {
            color: hasData ? getWindColor(speedValue) : "#94a3b8",
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getWindColor(speedValue) : "#94a3b8",
            color: "#fff",
          },
        },
        axisTick: {
          show: true,
          splitNumber: 2,
          length: 8,
          distance: 5,
          lineStyle: { color: "#64748b", width: 1 },
        },
        splitLine: {
          show: true,
          length: 15,
          distance: 5,
          lineStyle: { color: "#475569", width: 2 },
        },
        axisLabel: {
          distance: 30,
          color: "#1e293b",
          fontSize: 12,
          fontWeight: "600",
        },
        detail: {
          valueAnimation: true,
          formatter: () => hasData ? speedValue.toFixed(0) : "—",
          fontSize: 38,
          fontWeight: "bold",
          color: hasData ? getWindColor(speedValue) : "#94a3b8",
          offsetCenter: [0, "25%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "50%"],
          fontSize: 16,
          fontWeight: "500",
          color: "#64748b",
        },
        data: [{ value: speedValue, name: "km/s" }],
      },
    ],
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Wind className="h-5 w-5 text-info" />
          Solar Wind
        </CardTitle>
        <CardDescription>
          Density: {density?.toFixed(1) ?? "—"} p/cm³
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <EChartsWrapper option={option} height={260} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// F10.7 Flux Gauge - Elegant design with large arc and thin needle
function F107Gauge({ value }: { value: number | null }) {
  const displayValue = value ?? 100;
  const hasData = value !== null;
  
  const getFluxColor = (v: number) => {
    if (v < 100) return SCIENTIFIC_COLORS.success;
    if (v < 150) return SCIENTIFIC_COLORS.primary;
    if (v < 200) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "65%"],
        radius: "95%",
        startAngle: 180,
        endAngle: 0,
        min: 60,
        max: 300,
        splitNumber: 6,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.17, SCIENTIFIC_COLORS.success],
              [0.37, SCIENTIFIC_COLORS.primary],
              [0.58, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: {
            color: hasData ? getFluxColor(displayValue) : "#94a3b8",
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getFluxColor(displayValue) : "#94a3b8",
            color: "#fff",
          },
        },
        axisTick: {
          show: true,
          splitNumber: 2,
          length: 8,
          distance: 5,
          lineStyle: { color: "#64748b", width: 1 },
        },
        splitLine: {
          show: true,
          length: 15,
          distance: 5,
          lineStyle: { color: "#475569", width: 2 },
        },
        axisLabel: {
          distance: 30,
          color: "#1e293b",
          fontSize: 12,
          fontWeight: "600",
        },
        detail: {
          valueAnimation: true,
          formatter: () => hasData ? displayValue.toFixed(0) : "—",
          fontSize: 38,
          fontWeight: "bold",
          color: hasData ? getFluxColor(displayValue) : "#94a3b8",
          offsetCenter: [0, "25%"],
        },
        title: {
          show: true,
          offsetCenter: [0, "50%"],
          fontSize: 16,
          fontWeight: "500",
          color: "#64748b",
        },
        data: [{ value: displayValue, name: "SFU" }],
      },
    ],
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Radio className="h-5 w-5 text-warning" />
          F10.7 Flux
        </CardTitle>
        <CardDescription>Solar radio flux (10.7 cm)</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <EChartsWrapper option={option} height={260} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// Impact Prediction Card
function ImpactCard({ prediction }: { prediction: ImpactPrediction }) {
  const icon = CATEGORY_ICONS[prediction.category] || "⚡";

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-4 rounded-lg border bg-card"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h4 className="font-medium capitalize">
              {prediction.category.replace("_", " ")}
            </h4>
            <p className="text-xs text-muted-foreground">
              {prediction.arrival_time
                ? formatDateTime(prediction.arrival_time)
                : "Unknown arrival"}
            </p>
          </div>
        </div>
        <Badge variant={severityVariants[prediction.severity]}>
          {prediction.severity}
        </Badge>
      </div>
      {prediction.biological_effect && (
        <p className="text-sm text-muted-foreground mt-3">
          {prediction.biological_effect}
        </p>
      )}
      {prediction.polar_h10_recommendation && (
        <div className="mt-3 p-2 rounded bg-muted/50">
          <p className="text-xs font-medium">📍 Polar H10 Recommendation:</p>
          <p className="text-xs text-muted-foreground">
            {prediction.polar_h10_recommendation}
          </p>
        </div>
      )}
    </motion.div>
  );
}

export default function SpaceWeatherPage() {
  const [data, setData] = React.useState<SpaceWeatherSnapshot | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [lastFetch, setLastFetch] = React.useState<Date | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  // Messages that are informational, not actual errors
  const informationalPatterns = [
    "No ENLIL record",
    "No solar wind plasma",
    "No CME",
    "not found",
    "No data available",
    "no recent",
  ];

  const isInformationalMessage = (msg: string): boolean => {
    const lowerMsg = msg.toLowerCase();
    return informationalPatterns.some((pattern) =>
      lowerMsg.includes(pattern.toLowerCase())
    );
  };

  const fetchData = async (forceRefresh: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      // Use refresh endpoint for force refresh, otherwise try current first
      let snapshot: SpaceWeatherSnapshot;
      if (forceRefresh) {
        snapshot = await refreshSpaceWeather(true);
      } else {
        snapshot = await getCurrentSpaceWeather();
      }
      setData(snapshot);
      setLastFetch(new Date());
      
      // Check for actual errors in response (filter out informational messages)
      if (snapshot.errors && Object.keys(snapshot.errors).length > 0) {
        const actualErrors = Object.values(snapshot.errors).filter(
          (msg) => !isInformationalMessage(msg)
        );
        if (actualErrors.length > 0) {
          setError(actualErrors.join(", "));
        }
      }
    } catch (err) {
      console.error("Failed to fetch space weather:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData(false);
  }, []);

  return (
    <PageWrapper
      title="Space Weather Dashboard"
      description="Real-time NOAA/NASA data for Bogotá (UTC-5)"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            {lastFetch && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated: {formatDateTime(lastFetch.toISOString())}
              </Badge>
            )}
            {data?.most_severe && (
              <Badge
                variant={severityVariants[data.most_severe.severity]}
                className="flex items-center gap-1"
              >
                <AlertTriangle className="h-3 w-3" />
                {data.most_severe.severity.toUpperCase()} conditions
              </Badge>
            )}
          </div>
          <Button onClick={() => fetchData(true)} disabled={loading}>
            <RefreshCw
              className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Refresh Data
          </Button>
        </motion.div>

        {/* Error Display */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <Card className="border-destructive">
              <CardContent className="pt-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
                  <div>
                    <p className="font-medium text-destructive">
                      Data Fetch Error
                    </p>
                    <p className="text-sm text-muted-foreground">{error}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Ensure the backend API is running on port 8180 and can
                      reach NOAA/NASA services.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Info messages for missing optional data */}
        {data?.errors && Object.keys(data.errors).length > 0 && !error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-wrap gap-2"
          >
            {Object.entries(data.errors).map(([key, msg]) => (
              <Badge key={key} variant="secondary" className="text-xs">
                {key}: {msg.length > 50 ? msg.substring(0, 50) + "..." : msg}
              </Badge>
            ))}
          </motion.div>
        )}

        {/* Gauges Grid */}
        <div className="grid gap-6 md:grid-cols-3">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <KpGauge value={data?.data.kp_index ?? null} />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <SolarWindGauge
              speed={data?.data.solar_wind_speed ?? null}
              density={data?.data.solar_wind_density ?? null}
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <F107Gauge value={data?.data.f10_7_flux ?? null} />
          </motion.div>
        </div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Impact Predictions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="h-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-warning" />
                  Impact Predictions
                </CardTitle>
                <CardDescription>
                  Arrival times for different energy categories
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {data?.predictions && data.predictions.length > 0 ? (
                  data.predictions.map((pred, idx) => (
                    <ImpactCard key={idx} prediction={pred} />
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Sun className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No significant impacts predicted</p>
                    <p className="text-sm">Conditions are nominal</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Additional Metrics */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="space-y-4"
          >
            {/* X-ray / Proton Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-danger" />
                  Solar Radiation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">X-ray Flux</p>
                    <p className="text-lg font-semibold">
                      {data?.data.xray_class || "N/A"}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">
                      Proton &gt;10 MeV
                    </p>
                    <p className="text-lg font-semibold">
                      {data?.data.proton_flux_10mev?.toExponential(1) || "N/A"}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Dst Index</p>
                    <p className="text-lg font-semibold">
                      {data?.data.dst_index?.toFixed(0) || "N/A"} nT
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Bz (IMF)</p>
                    <p className="text-lg font-semibold">
                      {data?.data.solar_wind_bz?.toFixed(1) || "N/A"} nT
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Scientific Context */}
            <Card>
              <CardHeader>
                <CardTitle>Scientific Context</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div>
                  <h4 className="font-medium">Kp Index & Cardiovascular Effects</h4>
                  <p className="text-muted-foreground">
                    The Kp index (0-9 scale) measures global geomagnetic disturbance. 
                    Values ≥5 indicate geomagnetic storms that have been associated 
                    with reduced parasympathetic activity (RMSSD, HF power) and 
                    increased cardiovascular events in multiple epidemiological studies.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 italic">
                    Alabdulgader et al. (2018) found significant correlations between 
                    Kp and HRV metrics in long-term monitoring.
                  </p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium">Solar Wind & IMF Bz</h4>
                  <p className="text-muted-foreground">
                    Solar wind speed &gt;500 km/s combined with southward IMF 
                    (Bz &lt; 0) creates optimal conditions for geomagnetic coupling. 
                    Effects on human physiology typically appear 12-36 hours after 
                    the solar wind arrives at Earth.
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 italic">
                    The delay reflects both magnetospheric response time and 
                    biological adaptation processes.
                  </p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium">F10.7 Solar Radio Flux</h4>
                  <p className="text-muted-foreground">
                    F10.7 (measured in Solar Flux Units) is a proxy for overall 
                    solar activity including UV/EUV radiation. Values &gt;150 SFU 
                    indicate high solar activity periods. This index follows the 
                    ~11-year solar cycle.
                  </p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium">Polar H10 Recording Guidance</h4>
                  <p className="text-muted-foreground">
                    For optimal HRV baseline measurements, prefer geomagnetically 
                    quiet periods (Kp &lt; 4). During storms (Kp ≥ 5), document 
                    conditions but interpret results with caution. The app displays 
                    recommended recording windows based on current conditions.
                  </p>
                </div>
              </CardContent>
            </Card>
            
            {/* Measurement Recommendation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-success" />
                  Current Measurement Recommendation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`p-4 rounded-lg ${
                  (data?.data.kp_index ?? 0) < 4 
                    ? "bg-success/10 border border-success/30" 
                    : (data?.data.kp_index ?? 0) < 5 
                      ? "bg-warning/10 border border-warning/30"
                      : "bg-danger/10 border border-danger/30"
                }`}>
                  <p className="font-medium">
                    {(data?.data.kp_index ?? 0) < 4 
                      ? "✓ Good Conditions for HRV Recording"
                      : (data?.data.kp_index ?? 0) < 5 
                        ? "⚠ Moderate Conditions - Proceed with Awareness"
                        : "⚠ Disturbed Conditions - Consider Rescheduling Baseline Measurements"}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    {(data?.data.kp_index ?? 0) < 4 
                      ? "Current geomagnetic conditions are quiet. This is an optimal window for establishing or updating your HRV baseline."
                      : (data?.data.kp_index ?? 0) < 5 
                        ? "Minor geomagnetic activity detected. Recordings are acceptable but document current space weather conditions."
                        : "Geomagnetic storm in progress. HRV measurements may show atypical patterns. Document conditions for later correlation analysis."}
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  );
}
