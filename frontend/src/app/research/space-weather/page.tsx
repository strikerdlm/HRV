// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Sun,
  Zap,
  Wind,
  AlertTriangle,
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
import { getCurrentSpaceWeather } from "@/lib/research-api";
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

// Kp Index Gauge
function KpGauge({ value }: { value: number | null }) {
  const displayValue = value ?? 0;
  
  const getKpColor = (kp: number) => {
    if (kp < 4) return SCIENTIFIC_COLORS.success;
    if (kp < 5) return SCIENTIFIC_COLORS.warning;
    if (kp < 7) return "#e67e22";
    return SCIENTIFIC_COLORS.danger;
  };

  const option: any = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "60%"],
        radius: "90%",
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 9,
        splitNumber: 9,
        axisLine: {
          lineStyle: {
            width: 15,
            color: [
              [0.33, SCIENTIFIC_COLORS.success],
              [0.55, SCIENTIFIC_COLORS.warning],
              [0.77, "#e67e22"],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          length: "60%",
          width: 6,
          itemStyle: { color: getKpColor(displayValue) },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: 25,
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 11,
        },
        detail: {
          valueAnimation: true,
          formatter: (val: number) => (value !== null ? val.toFixed(1) : "N/A"),
          fontSize: 28,
          fontWeight: "bold",
          color: SCIENTIFIC_COLORS.textPrimary,
          offsetCenter: [0, "25%"],
        },
        data: [{ value: displayValue }],
      },
    ],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Compass className="h-5 w-5 text-primary" />
          Kp Index
        </CardTitle>
        <CardDescription>Planetary geomagnetic activity (0-9)</CardDescription>
      </CardHeader>
      <CardContent>
        <EChartsWrapper option={option} height={220} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// Solar Wind Gauge
function SolarWindGauge({
  speed,
  density,
}: {
  speed: number | null;
  density: number | null;
}) {
  const speedValue = speed ?? 0;

  const option: any = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "60%"],
        radius: "90%",
        startAngle: 200,
        endAngle: -20,
        min: 200,
        max: 900,
        splitNumber: 7,
        axisLine: {
          lineStyle: {
            width: 15,
            color: [
              [0.4, SCIENTIFIC_COLORS.success],
              [0.6, SCIENTIFIC_COLORS.primary],
              [0.8, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: {
          length: "60%",
          width: 6,
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: 25,
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 10,
        },
        detail: {
          valueAnimation: true,
          formatter: (val: number) =>
            speed !== null ? `${val.toFixed(0)} km/s` : "N/A",
          fontSize: 20,
          fontWeight: "bold",
          color: SCIENTIFIC_COLORS.textPrimary,
          offsetCenter: [0, "25%"],
        },
        data: [{ value: speedValue }],
      },
    ],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Wind className="h-5 w-5 text-info" />
          Solar Wind
        </CardTitle>
        <CardDescription>
          Density: {density?.toFixed(1) ?? "N/A"} p/cm³
        </CardDescription>
      </CardHeader>
      <CardContent>
        <EChartsWrapper option={option} height={220} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// F10.7 Flux Gauge
function F107Gauge({ value }: { value: number | null }) {
  const displayValue = value ?? 70;

  const option: any = {
    series: [
      {
        type: "gauge" as const,
        center: ["50%", "60%"],
        radius: "90%",
        startAngle: 200,
        endAngle: -20,
        min: 60,
        max: 300,
        splitNumber: 6,
        axisLine: {
          lineStyle: {
            width: 15,
            color: [
              [0.25, SCIENTIFIC_COLORS.success],
              [0.5, SCIENTIFIC_COLORS.primary],
              [0.75, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        pointer: { length: "60%", width: 6 },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          distance: 25,
          color: SCIENTIFIC_COLORS.textPrimary,
          fontSize: 10,
        },
        detail: {
          valueAnimation: true,
          formatter: (val: number) =>
            value !== null ? `${val.toFixed(0)} SFU` : "N/A",
          fontSize: 20,
          fontWeight: "bold",
          color: SCIENTIFIC_COLORS.textPrimary,
          offsetCenter: [0, "25%"],
        },
        data: [{ value: displayValue }],
      },
    ],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Radio className="h-5 w-5 text-warning" />
          F10.7 Flux
        </CardTitle>
        <CardDescription>Solar radio flux (10.7 cm)</CardDescription>
      </CardHeader>
      <CardContent>
        <EChartsWrapper option={option} height={220} showToolbox={false} />
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

  const fetchData = async () => {
    setLoading(true);
    try {
      const snapshot = await getCurrentSpaceWeather();
      setData(snapshot);
      setLastFetch(new Date());
    } catch (error) {
      console.error("Failed to fetch space weather:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();
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
          <Button onClick={fetchData} disabled={loading}>
            <RefreshCw
              className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Refresh Data
          </Button>
        </motion.div>

        {/* Gauges Grid */}
        <div className="grid gap-4 md:grid-cols-3">
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
                  <h4 className="font-medium">Kp Index & HRV</h4>
                  <p className="text-muted-foreground">
                    Higher Kp values (≥5) have been associated with reduced
                    parasympathetic activity (RMSSD, HF power) in multiple
                    studies (Alabdulgader et al., 2018).
                  </p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium">Solar Wind Effects</h4>
                  <p className="text-muted-foreground">
                    Solar wind speed &gt;500 km/s may precede autonomic changes
                    by 12-36 hours. Monitor for potential HRV fluctuations.
                  </p>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium">Polar H10 Timing</h4>
                  <p className="text-muted-foreground">
                    For clean HRV recordings, avoid measurements during
                    geomagnetically disturbed periods (Kp ≥ 5).
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
