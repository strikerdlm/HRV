// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Watch,
  Heart,
  Battery,
  Moon,
  Wind,
  Activity,
  Footprints,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Loader2,
  Settings,
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
import { Input } from "@/components/ui/input";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import type { GarminMetrics } from "@/types/research";
import { formatDateTime } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

// Metric Card Component
function MetricCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
  description,
}: {
  title: string;
  value: number | string | null | undefined;
  unit?: string;
  icon: React.ElementType;
  color: string;
  description?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${color}`}>
              <Icon className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{title}</p>
              <p className="text-2xl font-bold">
                {value !== null && value !== undefined ? value : "N/A"}
                {unit && value !== null && (
                  <span className="text-sm font-normal ml-1">{unit}</span>
                )}
              </p>
              {description && (
                <p className="text-xs text-muted-foreground mt-1">
                  {description}
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Body Battery Gauge - Elegant design with large arc and thin needle
function BodyBatteryGauge({
  high,
  low,
}: {
  high: number | null | undefined;
  low: number | null | undefined;
}) {
  const highValue = high ?? 0;
  const hasData = high !== null;
  
  const getBatteryColor = (v: number) => {
    if (v >= 75) return SCIENTIFIC_COLORS.success;
    if (v >= 50) return SCIENTIFIC_COLORS.primary;
    if (v >= 25) return SCIENTIFIC_COLORS.warning;
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
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 25,
            color: [
              [0.25, SCIENTIFIC_COLORS.danger],
              [0.5, SCIENTIFIC_COLORS.warning],
              [0.75, SCIENTIFIC_COLORS.primary],
              [1, SCIENTIFIC_COLORS.success],
            ],
          },
        },
        pointer: {
          icon: "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
          length: "65%",
          width: 6,
          offsetCenter: [0, "-10%"],
          itemStyle: {
            color: hasData ? getBatteryColor(highValue) : "#94a3b8",
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 18,
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getBatteryColor(highValue) : "#94a3b8",
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
          formatter: () => hasData ? `${highValue}%` : "—",
          fontSize: 38,
          fontWeight: "bold",
          color: hasData ? getBatteryColor(highValue) : "#94a3b8",
          offsetCenter: [0, "30%"],
        },
        data: [{ value: highValue }],
      },
    ],
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-0">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Battery className="h-5 w-5 text-success" />
          Body Battery
        </CardTitle>
        <CardDescription>
          High: {high ?? "—"}% | Low: {low ?? "—"}%
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <EChartsWrapper
          option={option}
          height={260}
          showToolbox={false}
        />
      </CardContent>
    </Card>
  );
}

// Sleep Quality Visualization
function SleepCard({ metrics }: { metrics: GarminMetrics | null }) {
  const sleepHours = metrics?.sleep_duration_hours;
  const sleepScore = metrics?.sleep_score;
  const efficiency = metrics?.sleep_efficiency;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Moon className="h-5 w-5 text-primary" />
          Sleep Analysis
        </CardTitle>
        <CardDescription>Last night&apos;s sleep metrics</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold">
              {sleepHours?.toFixed(1) ?? "N/A"}
            </p>
            <p className="text-xs text-muted-foreground">Hours</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold">{sleepScore ?? "N/A"}</p>
            <p className="text-xs text-muted-foreground">Score</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold">
              {efficiency
                ? `${(efficiency * 100).toFixed(0)}%`
                : "N/A"}
            </p>
            <p className="text-xs text-muted-foreground">Efficiency</p>
          </div>
        </div>

        {/* Sleep Stages */}
        {(metrics?.sleep_deep_minutes ||
          metrics?.sleep_rem_minutes ||
          metrics?.sleep_light_minutes) && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Sleep Stages</p>
            <div className="flex gap-2">
              <Badge variant="secondary" className="bg-indigo-500/10">
                Deep: {metrics?.sleep_deep_minutes ?? "N/A"} min
              </Badge>
              <Badge variant="secondary" className="bg-purple-500/10">
                REM: {metrics?.sleep_rem_minutes ?? "N/A"} min
              </Badge>
              <Badge variant="secondary" className="bg-blue-500/10">
                Light: {metrics?.sleep_light_minutes ?? "N/A"} min
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Connection Status
function ConnectionStatus({
  status,
  onSync,
  syncing,
}: {
  status: "connected" | "disconnected" | "error";
  onSync: () => void;
  syncing: boolean;
}) {
  const statusConfig = {
    connected: {
      icon: CheckCircle,
      color: "text-success",
      bg: "bg-success/10",
      label: "Connected",
    },
    disconnected: {
      icon: AlertCircle,
      color: "text-warning",
      bg: "bg-warning/10",
      label: "Disconnected",
    },
    error: {
      icon: AlertCircle,
      color: "text-danger",
      bg: "bg-danger/10",
      label: "Error",
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${config.bg}`}>
              <Icon className={`h-5 w-5 ${config.color}`} />
            </div>
            <div>
              <p className="font-medium">Garmin Connect</p>
              <p className="text-sm text-muted-foreground">{config.label}</p>
            </div>
          </div>
          <Button onClick={onSync} disabled={syncing} size="sm">
            {syncing ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="h-4 w-4 mr-2" />
            )}
            {syncing ? "Syncing..." : "Sync Data"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function GarminPage() {
  const [metrics, setMetrics] = React.useState<GarminMetrics | null>(null);
  const [history, setHistory] = React.useState<GarminMetrics[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [syncing, setSyncing] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<
    "connected" | "disconnected" | "error"
  >("disconnected");
  const [userId, setUserId] = React.useState("default");
  const [error, setError] = React.useState<string | null>(null);

  const fetchMetrics = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/research/garmin/latest/${userId}`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: GarminMetrics = await response.json();
      setMetrics(data);

      // Check if we have actual data
      if (data.date || data.steps || data.resting_hr) {
        setConnectionStatus("connected");
      } else {
        setConnectionStatus("disconnected");
      }

      // Fetch history
      const historyResponse = await fetch(
        `${API_BASE}/api/research/garmin/history/${userId}?days=7`,
        {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        }
      );

      if (historyResponse.ok) {
        const historyData: GarminMetrics[] = await historyResponse.json();
        setHistory(historyData);
      }
    } catch (err) {
      console.error("Failed to fetch Garmin metrics:", err);
      setConnectionStatus("error");
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const syncData = async () => {
    setSyncing(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/research/garmin/sync/${userId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ days: 14 }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      const result = await response.json();
      setConnectionStatus("connected");

      // Refresh metrics after sync
      await fetchMetrics();
    } catch (err) {
      console.error("Failed to sync Garmin data:", err);
      setConnectionStatus("error");
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  React.useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return (
    <PageWrapper
      title="Garmin Integration"
      description="Vivosmart 5 and compatible devices - Health metrics analysis"
    >
      <div className="space-y-6">
        {/* Connection Status */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <ConnectionStatus
            status={connectionStatus}
            onSync={syncData}
            syncing={syncing}
          />
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
                    <p className="font-medium text-destructive">Sync Error</p>
                    <p className="text-sm text-muted-foreground">{error}</p>
                    <p className="text-xs text-muted-foreground mt-2">
                      Ensure GARMIN_EMAIL and GARMIN_PASSWORD are set in your
                      backend .env file.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* User Selection */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings className="h-5 w-5" />
                Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <label className="text-sm text-muted-foreground">
                    User ID
                  </label>
                  <Input
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    placeholder="Enter user ID"
                    className="mt-1"
                  />
                </div>
                <Button
                  onClick={fetchMetrics}
                  disabled={loading}
                  className="mt-6"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-2" />
                  )}
                  Refresh
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Main Metrics Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <MetricCard
              title="Resting HR"
              value={metrics?.resting_hr}
              unit="bpm"
              icon={Heart}
              color="bg-danger"
              description="Overnight average"
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
          >
            <MetricCard
              title="HRV (Overnight)"
              value={metrics?.hrv_overnight?.toFixed(1)}
              unit="ms"
              icon={Activity}
              color="bg-primary"
              description="RMSSD during sleep"
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <MetricCard
              title="SpO2"
              value={metrics?.spo2_avg?.toFixed(0)}
              unit="%"
              icon={Wind}
              color="bg-info"
              description="Blood oxygen average"
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
          >
            <MetricCard
              title="Steps"
              value={metrics?.steps?.toLocaleString()}
              icon={Footprints}
              color="bg-success"
            />
          </motion.div>
        </div>

        {/* Body Battery & Sleep */}
        <div className="grid gap-6 md:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <BodyBatteryGauge
              high={metrics?.body_battery_high}
              low={metrics?.body_battery_low}
            />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }}
          >
            <SleepCard metrics={metrics} />
          </motion.div>
        </div>

        {/* Additional Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Additional Metrics</CardTitle>
              <CardDescription>
                Stress, respiration, and activity data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">
                    Avg Stress
                  </p>
                  <p className="text-lg font-semibold">
                    {metrics?.stress_avg?.toFixed(0) ?? "N/A"}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">
                    Respiration (Awake)
                  </p>
                  <p className="text-lg font-semibold">
                    {metrics?.respiration_awake?.toFixed(1) ?? "N/A"}{" "}
                    <span className="text-sm font-normal">br/min</span>
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">
                    Respiration (Sleep)
                  </p>
                  <p className="text-lg font-semibold">
                    {metrics?.respiration_sleep?.toFixed(1) ?? "N/A"}{" "}
                    <span className="text-sm font-normal">br/min</span>
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-muted/50">
                  <p className="text-xs text-muted-foreground">
                    VO2 Max
                  </p>
                  <p className="text-lg font-semibold">
                    {metrics?.vo2max?.toFixed(0) ?? "N/A"}{" "}
                    <span className="text-sm font-normal">mL/kg/min</span>
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Scientific Context */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Scientific Context</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <h4 className="font-medium">Overnight HRV & Recovery</h4>
                <p className="text-muted-foreground">
                  Overnight RMSSD reflects parasympathetic activity during
                  restorative sleep. Higher values typically indicate better
                  recovery and cardiovascular health (Plews et al., 2013).
                </p>
              </div>
              <Separator />
              <div>
                <h4 className="font-medium">Body Battery Algorithm</h4>
                <p className="text-muted-foreground">
                  Garmin&apos;s Body Battery combines HRV, stress, sleep
                  quality, and activity data using Firstbeat Analytics
                  algorithms to estimate energy levels throughout the day.
                </p>
              </div>
              <Separator />
              <div>
                <h4 className="font-medium">SpO2 & Sleep Quality</h4>
                <p className="text-muted-foreground">
                  Nocturnal SpO2 dips may indicate sleep-disordered breathing.
                  Consistent readings above 95% during sleep suggest healthy
                  oxygenation (Haba-Rubio et al., 2016).
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Data Date */}
        {metrics?.date && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-center"
          >
            <Badge variant="outline">Data from: {metrics.date}</Badge>
          </motion.div>
        )}
      </div>
    </PageWrapper>
  );
}
