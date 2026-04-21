"use client";

// Author: Dr Diego Malpica MD

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
  TrendingUp,
  BarChart3,
  Zap,
  Sun,
  Brain,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getCurrentSpaceWeather } from "@/lib/research-api";
import { getMission, listUsers, setMission } from "@/lib/api";
import type { GarminMetrics, SpaceWeatherSnapshot } from "@/types/research";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8180";

// ---------------------------------------------------------------------------
// Publication-Quality Colors (following plot rules)
// ---------------------------------------------------------------------------
const CHART_COLORS = {
  hrv: "#2563eb",        // Blue
  rhr: "#dc2626",        // Red
  spo2: "#0891b2",       // Cyan
  sleep: "#7c3aed",      // Purple
  stress: "#f97316",     // Orange
  bodyBattery: "#22c55e", // Green
  respiration: "#14b8a6", // Teal
  steps: "#8b5cf6",      // Violet
  text: "#1a1a1a",
  subtext: "#64748b",
  grid: "rgba(44, 62, 80, 0.1)",
};

// ---------------------------------------------------------------------------
// Clean Gauge Component (following plot rules)
// ---------------------------------------------------------------------------
function CleanGauge({
  value,
  min = 0,
  max = 100,
  unit = "",
  thresholds,
  label,
}: {
  value: number | null;
  min?: number;
  max?: number;
  unit?: string;
  thresholds: Array<[number, string]>; // [[ratio, color], ...]
  label: string;
}) {
  const displayValue = value ?? 0;
  const hasData = value !== null;
  
  const getColor = () => {
    const ratio = (displayValue - min) / (max - min);
    for (let i = thresholds.length - 1; i >= 0; i--) {
      if (ratio >= thresholds[i][0]) return thresholds[i][1];
    }
    return thresholds[0][1];
  };

  // Publication-quality gauge: clean, uncluttered, clear typography
  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "60%"],
        radius: "90%",
        startAngle: 180,
        endAngle: 0,
        min,
        max,
        axisLine: {
          lineStyle: {
            width: 14,
            color: thresholds,
          },
        },
        pointer: {
          length: "60%",
          width: 4,
          offsetCenter: [0, "0%"],
          itemStyle: {
            color: hasData ? getColor() : "#94a3b8",
            shadowColor: "rgba(0, 0, 0, 0.2)",
            shadowBlur: 4,
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 10,
          itemStyle: {
            borderWidth: 2,
            borderColor: hasData ? getColor() : "#94a3b8",
            color: "#fff",
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        // CRITICAL: Only show min and max to prevent clutter
        axisLabel: {
          show: true,
          distance: 6,
          color: CHART_COLORS.text,
          fontSize: 9,
          fontWeight: "600",
          formatter: (v: number) => {
            // Only show min and max values - no middle numbers
            if (v === min) return min.toString();
            if (v === max) return max.toString();
            return "";
          },
        },
        progress: { show: false },
        detail: {
          valueAnimation: true,
          formatter: () => hasData ? `${displayValue.toFixed(unit === "ms" ? 1 : 0)}` : "—",
          fontSize: 20,
          fontWeight: "bold",
          color: hasData ? getColor() : "#94a3b8",
          offsetCenter: [0, "30%"],
        },
        // Title/label shown BELOW the gauge value
        title: {
          show: false, // Hide to prevent overlap - label shown in card header
        },
        data: [{ value: displayValue, name: label }],
      },
    ],
  };

  return (
    <div className="relative">
      <EChartsWrapper option={option} height={140} showToolbox={false} />
      {/* Clean label below gauge */}
      <p className="text-xs text-muted-foreground text-center -mt-3 pb-1">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Time Series Chart Builder (following plot rules)
// ---------------------------------------------------------------------------
function buildTimeSeriesChart(
  dates: string[],
  series: Array<{
    name: string;
    data: (number | null)[];
    color: string;
    yAxisIndex?: number;
  }>,
  yAxisConfigs: Array<{
    name: string;
    position: "left" | "right";
    color: string;
  }>,
  title: string
): Record<string, unknown> {
  // Format dates for display
  const formattedDates = dates.map((d) => {
    const date = new Date(d);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });

  return {
    title: {
      text: title,
      left: "center",
      top: 8,
      textStyle: { color: CHART_COLORS.text, fontSize: 14, fontWeight: "bold" },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e2e8f0",
      textStyle: { color: CHART_COLORS.text, fontSize: 11 },
    },
    legend: {
      data: series.map((s) => s.name),
      top: 30,
      textStyle: { color: CHART_COLORS.text, fontSize: 10 },
    },
    grid: {
      left: 50,
      right: yAxisConfigs.length > 1 ? 50 : 25,
      top: 65,
      bottom: 35,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: formattedDates,
      axisLabel: {
        color: CHART_COLORS.text,
        fontSize: 10,
        interval: Math.max(0, Math.floor(dates.length / 7)),
      },
      axisLine: { lineStyle: { color: "#2c3e50" } },
      axisTick: { show: false },
    },
    yAxis: yAxisConfigs.map((config, idx) => ({
      type: "value",
      name: config.name,
      position: config.position,
      nameTextStyle: { color: config.color, fontSize: 10, fontWeight: "bold" },
      axisLabel: {
        color: config.color,
        fontSize: 9,
        formatter: (v: number) => v.toFixed(0),
      },
      axisLine: { show: false },
      splitLine: idx === 0 ? { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } } : { show: false },
    })),
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      data: s.data,
      smooth: true,
      yAxisIndex: s.yAxisIndex ?? 0,
      lineStyle: { color: s.color, width: 2 },
      symbol: "circle",
      symbolSize: 4,
      itemStyle: { color: s.color },
    })),
  };
}

// ---------------------------------------------------------------------------
// Correlation Scatter Chart
// ---------------------------------------------------------------------------
function buildCorrelationChart(
  xData: (number | null)[],
  yData: (number | null)[],
  xLabel: string,
  yLabel: string,
  title: string
): Record<string, unknown> {
  // Pair up valid data points
  const points: [number, number][] = [];
  for (let i = 0; i < Math.min(xData.length, yData.length); i++) {
    if (xData[i] !== null && yData[i] !== null) {
      points.push([xData[i] as number, yData[i] as number]);
    }
  }

  // Calculate Pearson correlation
  let correlation = 0;
  if (points.length > 2) {
    const xVals = points.map((p) => p[0]);
    const yVals = points.map((p) => p[1]);
    const xMean = xVals.reduce((a, b) => a + b, 0) / xVals.length;
    const yMean = yVals.reduce((a, b) => a + b, 0) / yVals.length;
    const num = xVals.reduce((sum, x, i) => sum + (x - xMean) * (yVals[i] - yMean), 0);
    const denX = Math.sqrt(xVals.reduce((sum, x) => sum + (x - xMean) ** 2, 0));
    const denY = Math.sqrt(yVals.reduce((sum, y) => sum + (y - yMean) ** 2, 0));
    if (denX > 0 && denY > 0) correlation = num / (denX * denY);
  }

  const corrColor = Math.abs(correlation) > 0.5 ? CHART_COLORS.hrv : CHART_COLORS.subtext;

  return {
    title: {
      text: title,
      subtext: `r = ${correlation.toFixed(3)} (n=${points.length})`,
      left: "center",
      top: 5,
      textStyle: { color: CHART_COLORS.text, fontSize: 13, fontWeight: "bold" },
      subtextStyle: { color: corrColor, fontSize: 11 },
    },
    tooltip: {
      trigger: "item",
      formatter: (p: { value: [number, number] }) =>
        `${xLabel}: ${p.value[0].toFixed(1)}<br/>${yLabel}: ${p.value[1].toFixed(1)}`,
    },
    grid: { left: 50, right: 25, top: 55, bottom: 40, containLabel: true },
    xAxis: {
      type: "value",
      name: xLabel,
      nameLocation: "middle",
      nameGap: 25,
      nameTextStyle: { color: CHART_COLORS.text, fontSize: 11 },
      axisLabel: { color: CHART_COLORS.text, fontSize: 9 },
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
    },
    yAxis: {
      type: "value",
      name: yLabel,
      nameLocation: "middle",
      nameGap: 35,
      nameTextStyle: { color: CHART_COLORS.text, fontSize: 11 },
      axisLabel: { color: CHART_COLORS.text, fontSize: 9 },
      splitLine: { lineStyle: { color: CHART_COLORS.grid, type: "dashed" } },
    },
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: 8,
        itemStyle: {
          color: CHART_COLORS.hrv,
          opacity: 0.7,
        },
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Metric Summary Card
// ---------------------------------------------------------------------------
function MetricCard({
  title,
  value,
  unit,
  icon: Icon,
  color,
  trend,
}: {
  title: string;
  value: number | string | null | undefined;
  unit?: string;
  icon: React.ElementType;
  color: string;
  trend?: "up" | "down" | "stable";
}) {
  return (
    <Card className="bg-gradient-to-br from-white to-slate-50 dark:from-slate-900 dark:to-slate-800">
      <CardContent className="pt-4 pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${color}`}>
              <Icon className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{title}</p>
              <p className="text-xl font-bold">
                {value !== null && value !== undefined ? value : "—"}
                {unit && value !== null && (
                  <span className="text-xs font-normal ml-1">{unit}</span>
                )}
              </p>
            </div>
          </div>
          {trend && (
            <TrendingUp
              className={`h-4 w-4 ${
                trend === "up"
                  ? "text-success"
                  : trend === "down"
                  ? "text-danger rotate-180"
                  : "text-muted-foreground rotate-90"
              }`}
            />
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Space Weather Correlation Panel
// ---------------------------------------------------------------------------
function SpaceWeatherPanel({
  spaceWeather,
  loading,
}: {
  spaceWeather: SpaceWeatherSnapshot | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6 flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const kp = spaceWeather?.data.kp_index ?? null;
  const dst = spaceWeather?.data.dst_index ?? null;
  const solarWind = spaceWeather?.data.solar_wind_speed ?? null;

  const getKpStatus = (k: number | null) => {
    if (k === null) return { label: "Unknown", color: "text-muted-foreground" };
    if (k < 4) return { label: "Quiet", color: "text-success" };
    if (k < 5) return { label: "Unsettled", color: "text-warning" };
    return { label: "Storm", color: "text-danger" };
  };

  const kpStatus = getKpStatus(kp);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Sun className="h-4 w-4 text-warning" />
          Space Weather Correlation
        </CardTitle>
        <CardDescription className="text-xs">
          Geomagnetic activity may influence HRV and sleep patterns (Nature Scientific Reports, 2018)
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-2 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Kp Index</p>
            <p className={`text-lg font-bold ${kpStatus.color}`}>
              {kp?.toFixed(1) ?? "—"}
            </p>
            <p className={`text-xs ${kpStatus.color}`}>{kpStatus.label}</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Dst</p>
            <p className="text-lg font-bold">{dst?.toFixed(0) ?? "—"}</p>
            <p className="text-xs text-muted-foreground">nT</p>
          </div>
          <div className="text-center p-2 rounded-lg bg-muted/50">
            <p className="text-xs text-muted-foreground">Solar Wind</p>
            <p className="text-lg font-bold">{solarWind?.toFixed(0) ?? "—"}</p>
            <p className="text-xs text-muted-foreground">km/s</p>
          </div>
        </div>
        <p className="text-xs text-muted-foreground mt-3 italic">
          Higher Kp associated with decreased HRV in sensitive individuals
        </p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Settings Dialog Component
// ---------------------------------------------------------------------------
function SettingsDialog({
  userId,
  setUserId,
  autoSync,
  setAutoSync,
  syncDays,
  setSyncDays,
  activeMission,
  onActiveMissionChange,
  onSettingsSaved,
  crewUserOptions,
}: {
  userId: string;
  setUserId: (id: string) => void;
  autoSync: boolean;
  setAutoSync: (auto: boolean) => void;
  syncDays: number;
  setSyncDays: (days: number) => void;
  activeMission: string;
  onActiveMissionChange: (mission: string) => void;
  onSettingsSaved?: () => void;
  crewUserOptions: Array<{ user_id: string; username: string }>;
}) {
  const [tempUserId, setTempUserId] = React.useState(userId);
  const [tempDays, setTempDays] = React.useState(syncDays);
  const [tempMission, setTempMission] = React.useState(activeMission);
  const [saving, setSaving] = React.useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const m = await setMission(tempMission);
      onActiveMissionChange(m.active_mission);
      setUserId(tempUserId);
      setSyncDays(tempDays);
      if (typeof window !== "undefined") {
        localStorage.setItem("garmin_user_id", tempUserId);
        localStorage.setItem("garmin_auto_sync", autoSync.toString());
        localStorage.setItem("garmin_sync_days", tempDays.toString());
      }
      onSettingsSaved?.();
    } catch (e) {
      console.error("Failed to save Garmin settings:", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      onOpenChange={(open) => {
        if (open) {
          setTempUserId(userId);
          setTempDays(syncDays);
          setTempMission(activeMission);
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Settings className="h-4 w-4 mr-2" />
          Settings
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Watch className="h-5 w-5" />
            Garmin Connect Settings
          </DialogTitle>
          <DialogDescription>
            Configure your Garmin Connect integration. Credentials are stored on the backend (.env file).
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Active mission (SQLite scope)</Label>
            <Select value={tempMission} onValueChange={setTempMission}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Mission" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Mission 1">Mission 1</SelectItem>
                <SelectItem value="Mission 2">Mission 2</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Must match Streamlit&apos;s mission selector (same{" "}
              <code className="bg-muted px-1 rounded">HRV_ACTIVE_MISSION</code> as the FastAPI
              process). Changing this switches which{" "}
              <code className="bg-muted px-1 rounded">crew/.../db/hrv_users.db</code> file is used.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="userId">User ID</Label>
            <Input
              id="userId"
              value={tempUserId}
              onChange={(e) => setTempUserId(e.target.value)}
              placeholder="Crew profile user_id (UUID)"
              list="garmin-crew-user-ids"
            />
            <datalist id="garmin-crew-user-ids">
              {crewUserOptions.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.username}
                </option>
              ))}
            </datalist>
            <p className="text-xs text-muted-foreground">
              Use the same <strong>user_id</strong> as the active Streamlit crew profile (usually a
              UUID), not a placeholder string.
            </p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="syncDays">Sync Days</Label>
            <Input
              id="syncDays"
              type="number"
              min={1}
              max={90}
              value={tempDays}
              onChange={(e) => setTempDays(parseInt(e.target.value) || 30)}
            />
            <p className="text-xs text-muted-foreground">
              Number of days to sync from Garmin Connect (1-90)
            </p>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Auto-Sync on Load</Label>
              <p className="text-xs text-muted-foreground">
                Automatically sync data when page loads
              </p>
            </div>
            <Switch
              checked={autoSync}
              onCheckedChange={(checked) => {
                setAutoSync(checked);
                if (typeof window !== "undefined") {
                  localStorage.setItem("garmin_auto_sync", checked.toString());
                }
              }}
            />
          </div>
          
          <Separator />
          
          <div className="bg-muted/50 rounded-lg p-3 space-y-2">
            <h4 className="text-sm font-medium">Backend Configuration</h4>
            <p className="text-xs text-muted-foreground">
              Ensure the following environment variables are set in your backend <code className="bg-muted px-1 rounded">.env</code> file:
            </p>
            <pre className="text-xs bg-muted p-2 rounded font-mono">
              GARMIN_EMAIL=your@email.com{"\n"}
              GARMIN_PASSWORD=your_password
            </pre>
            <p className="text-xs text-muted-foreground italic">
              Note: If MFA is enabled, you may need to pre-generate auth tokens.
            </p>
          </div>
          
          <Button onClick={() => void handleSave()} className="w-full" disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2 inline" /> : null}
            Save Settings
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------
export default function GarminPage() {
  const [metrics, setMetrics] = React.useState<GarminMetrics | null>(null);
  const [history, setHistory] = React.useState<GarminMetrics[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [syncing, setSyncing] = React.useState(false);
  const [connectionStatus, setConnectionStatus] = React.useState<
    "connected" | "disconnected" | "error"
  >("disconnected");
  const [error, setError] = React.useState<string | null>(null);
  const [spaceWeather, setSpaceWeather] = React.useState<SpaceWeatherSnapshot | null>(null);
  const [spaceWeatherLoading, setSpaceWeatherLoading] = React.useState(false);

  const [userId, setUserId] = React.useState("");
  const [crewUserOptions, setCrewUserOptions] = React.useState<
    Array<{ user_id: string; username: string }>
  >([]);
  const [apiMission, setApiMission] = React.useState("Mission 1");
  const [autoSync, setAutoSync] = React.useState(false);
  const [syncDays, setSyncDays] = React.useState(30);
  const [initialLoadDone, setInitialLoadDone] = React.useState(false);
  const [lastSync, setLastSync] = React.useState<{
    records_synced: number;
    message: string;
    date_range?: string | null;
    active_mission?: string;
    database_path?: string;
    garmin_rows_for_user?: number;
    error_detail?: string | null;
  } | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const savedAutoSync =
        typeof window !== "undefined" ? localStorage.getItem("garmin_auto_sync") : null;
      const savedSyncDays =
        typeof window !== "undefined" ? localStorage.getItem("garmin_sync_days") : null;
      const savedUserId =
        typeof window !== "undefined" ? localStorage.getItem("garmin_user_id") : null;

      if (savedAutoSync) setAutoSync(savedAutoSync === "true");
      if (savedSyncDays) setSyncDays(parseInt(savedSyncDays, 10) || 30);

      // Legacy placeholder: older builds used literal "default", which is never a real UUID in `users`.
      const rawStored = (savedUserId ?? "").trim();
      const legacyPlaceholder =
        !rawStored || rawStored.toLowerCase() === "default";
      let uid = legacyPlaceholder ? "" : rawStored;

      try {
        const res = await listUsers();
        if (!cancelled) {
          setCrewUserOptions(
            res.users.map((u) => ({ user_id: u.user_id, username: u.username }))
          );
        }
        if (!uid && res.users.length > 0) {
          uid = res.users[0].user_id;
        }
      } catch (e) {
        console.warn("[Garmin] listUsers failed (using saved or empty user id):", e);
      }

      if (!cancelled) {
        setUserId(uid);
        if (
          typeof window !== "undefined" &&
          uid &&
          legacyPlaceholder
        ) {
          localStorage.setItem("garmin_user_id", uid);
        }
        setInitialLoadDone(true);
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  React.useEffect(() => {
    void getMission()
      .then((m) => setApiMission(m.active_mission || "Mission 1"))
      .catch(() => {});
  }, []);

  // Fetch Garmin metrics
  const fetchMetrics = React.useCallback(async () => {
    if (!userId) {
      setLoading(false);
      setMetrics(null);
      setHistory([]);
      setConnectionStatus("disconnected");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      console.log(`[Garmin] Fetching metrics for user: ${userId}`);
      
      // Fetch latest metrics
      const response = await fetch(
        `${API_BASE}/api/research/garmin/latest/${userId}`,
        { 
          method: "GET", 
          headers: { "Content-Type": "application/json" },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[Garmin] API error: ${response.status}`, errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: GarminMetrics = await response.json();
      console.log("[Garmin] Received metrics:", data);
      setMetrics(data);

      // Check if we have actual data (not just empty response)
      const hasData = data.date || data.steps || data.resting_hr || data.hrv_overnight;
      if (hasData) {
        setConnectionStatus("connected");
      } else {
        setConnectionStatus("disconnected");
      }

      // Fetch history using configured syncDays for correlation analysis
      const historyResponse = await fetch(
        `${API_BASE}/api/research/garmin/history/${userId}?days=${syncDays}`,
        { method: "GET", headers: { "Content-Type": "application/json" } }
      );

      if (historyResponse.ok) {
        const historyData: GarminMetrics[] = await historyResponse.json();
        console.log(`[Garmin] Received ${historyData.length} history records`);
        setHistory(historyData);
      }
    } catch (err) {
      console.error("Failed to fetch Garmin metrics:", err);
      setConnectionStatus("error");
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, [userId, syncDays]);

  // Fetch space weather for correlation
  const fetchSpaceWeather = React.useCallback(async () => {
    setSpaceWeatherLoading(true);
    try {
      const data = await getCurrentSpaceWeather();
      setSpaceWeather(data);
    } catch (err) {
      console.error("Failed to fetch space weather:", err);
    } finally {
      setSpaceWeatherLoading(false);
    }
  }, []);

  // Sync data from Garmin Connect
  const syncData = React.useCallback(async () => {
    if (!userId) {
      setError("Set a User ID in Settings before syncing.");
      return;
    }
    setSyncing(true);
    setError(null);
    try {
      console.log(`[Garmin] Starting sync for user: ${userId}, days: ${syncDays}`);
      
      const response = await fetch(
        `${API_BASE}/api/research/garmin/sync/${userId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ days: syncDays }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch {
          // Use default error message
        }
        console.error("[Garmin] Sync error:", errorMessage);
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log("[Garmin] Sync result:", result);

      setLastSync({
        records_synced: result.records_synced,
        message: result.message,
        date_range: result.date_range,
        active_mission: result.active_mission,
        database_path: result.database_path,
        garmin_rows_for_user: result.garmin_rows_for_user,
        error_detail: result.error_detail,
      });
      if (result.success === false) {
        setConnectionStatus("error");
        setError(typeof result.message === "string" ? result.message : "Sync incomplete");
      } else {
        setConnectionStatus("connected");
        setError(null);
      }
      await fetchMetrics();
    } catch (err) {
      console.error("Failed to sync Garmin data:", err);
      setConnectionStatus("error");
      const errorMsg = err instanceof Error ? err.message : "Sync failed";
      
      // Provide more helpful error messages
      if (errorMsg.includes("GARMIN_EMAIL") || errorMsg.includes("not configured")) {
        setError("Garmin credentials not configured. Please set GARMIN_EMAIL and GARMIN_PASSWORD in backend .env file.");
      } else if (errorMsg.includes("authentication") || errorMsg.includes("401")) {
        setError("Garmin authentication failed. Check your credentials or generate new auth tokens if MFA is enabled.");
      } else {
        setError(errorMsg);
      }
    } finally {
      setSyncing(false);
    }
  }, [userId, syncDays, fetchMetrics]);

  React.useEffect(() => {
    if (!initialLoadDone || !userId) return;

    void fetchMetrics();
    void fetchSpaceWeather();
  }, [initialLoadDone, userId, fetchMetrics, fetchSpaceWeather]);

  // Auto-sync feature: sync from Garmin Connect when autoSync is enabled
  React.useEffect(() => {
    if (!initialLoadDone || !userId || !autoSync) return;

    const shouldAutoSync = !metrics?.date;
    if (shouldAutoSync) {
      void syncData();
    }
  }, [initialLoadDone, userId, autoSync, metrics?.date, syncData]);

  // Prepare time series data
  const dates = React.useMemo(
    () => history.map((m) => m.date || "").filter(Boolean).reverse(),
    [history]
  );
  
  const hrvData = React.useMemo(
    () => history.map((m) => m.hrv_overnight).reverse(),
    [history]
  );
  
  const rhrData = React.useMemo(
    () => history.map((m) => m.resting_hr).reverse(),
    [history]
  );
  
  const spo2Data = React.useMemo(
    () => history.map((m) => m.spo2_avg).reverse(),
    [history]
  );
  
  const sleepData = React.useMemo(
    () => history.map((m) => m.sleep_duration_hours).reverse(),
    [history]
  );
  
  const stressData = React.useMemo(
    () => history.map((m) => m.stress_avg).reverse(),
    [history]
  );
  
  const respirationData = React.useMemo(
    () => history.map((m) => m.respiration_sleep).reverse(),
    [history]
  );

  return (
    <PageWrapper
      title="Garmin Connect"
      description="Physiological data for research analysis and correlation studies"
    >
      <div className="space-y-6">
        {/* Connection Status Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className={
                connectionStatus === "connected"
                  ? "border-success text-success"
                  : connectionStatus === "error"
                  ? "border-danger text-danger"
                  : ""
              }
            >
              {connectionStatus === "connected" && <CheckCircle className="h-3 w-3 mr-1" />}
              {connectionStatus === "error" && <AlertCircle className="h-3 w-3 mr-1" />}
              {connectionStatus === "connected"
                ? "Connected"
                : connectionStatus === "error"
                ? "Error"
                : "Disconnected"}
            </Badge>
            <Badge variant="secondary">{userId || "no user id"}</Badge>
            <Badge variant="outline" className="text-xs font-normal">
              API mission: {apiMission}
            </Badge>
            {autoSync && (
              <Badge variant="outline" className="border-primary text-primary">
                <RefreshCw className="h-3 w-3 mr-1" />
                Auto-sync
              </Badge>
            )}
            {metrics?.date && (
              <Badge variant="outline">Last: {metrics.date}</Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <SettingsDialog
              userId={userId}
              setUserId={setUserId}
              autoSync={autoSync}
              setAutoSync={setAutoSync}
              syncDays={syncDays}
              setSyncDays={setSyncDays}
              activeMission={apiMission}
              onActiveMissionChange={setApiMission}
              onSettingsSaved={() => {
                void fetchMetrics();
              }}
              crewUserOptions={crewUserOptions}
            />
            <Button onClick={fetchMetrics} disabled={loading} variant="outline" size="sm">
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button onClick={syncData} disabled={syncing}>
              {syncing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Watch className="h-4 w-4 mr-2" />
              )}
              Sync from Garmin
            </Button>
          </div>
        </motion.div>

        {lastSync && (
          <Card className="border-muted">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Last sync</CardTitle>
              <CardDescription className="text-xs">
                {lastSync.message}
              </CardDescription>
            </CardHeader>
            <CardContent className="text-xs text-muted-foreground space-y-1 pt-0">
              <p>
                Records written this run:{" "}
                <span className="font-medium text-foreground">{lastSync.records_synced}</span>
                {lastSync.date_range ? (
                  <>
                    {" "}
                    · Range:{" "}
                    <span className="font-mono break-all">{lastSync.date_range}</span>
                  </>
                ) : null}
              </p>
              {lastSync.garmin_rows_for_user != null ? (
                <p>
                  Garmin rows for this user in DB:{" "}
                  <span className="font-medium text-foreground">{lastSync.garmin_rows_for_user}</span>
                </p>
              ) : null}
              {lastSync.active_mission ? (
                <p>
                  Active mission:{" "}
                  <span className="font-medium text-foreground">{lastSync.active_mission}</span>
                </p>
              ) : null}
              {lastSync.database_path ? (
                <p className="break-all">
                  Database: <span className="font-mono">{lastSync.database_path}</span>
                </p>
              ) : null}
              {lastSync.error_detail ? (
                <p className="break-all text-foreground/90">
                  <span className="font-medium">Detail:</span>{" "}
                  <span className="font-mono">{lastSync.error_detail}</span>
                </p>
              ) : null}
              <Button variant="ghost" size="sm" className="h-7 px-2 mt-2" onClick={() => setLastSync(null)}>
                Dismiss
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Setup Guide - Show when no crew user id resolved */}
        {!userId && initialLoadDone && !error && (
          <Card className="border-blue-200 bg-blue-50/50">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <Settings className="h-5 w-5 text-blue-500 mt-0.5" />
                <div className="space-y-2">
                  <p className="font-medium text-blue-900">No crew user id</p>
                  <p className="text-sm text-blue-700">
                    Open <strong>Settings</strong> and paste the same <code className="bg-blue-100 px-1 rounded text-xs">user_id</code>{" "}
                    as your Streamlit crew profile (UUID), or create a user via the API first.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Setup Guide - Show when no data */}
        {userId && !metrics?.date && !error && !loading && (
          <Card className="border-blue-200 bg-blue-50/50">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <Settings className="h-5 w-5 text-blue-500 mt-0.5" />
                <div className="space-y-2">
                  <p className="font-medium text-blue-900">Setup Required</p>
                  <p className="text-sm text-blue-700">
                    Configure your Garmin Connect integration to start syncing data:
                  </p>
                  <ol className="text-sm text-blue-700 list-decimal list-inside space-y-1">
                    <li>
                      In <strong>Settings</strong>, set <strong>Active mission</strong> and{" "}
                      <strong>User ID</strong> to match Streamlit (same crew DB and profile UUID)
                    </li>
                    <li>
                      Ensure <code className="bg-blue-100 px-1 rounded text-xs">GARMIN_EMAIL</code>{" "}
                      and <code className="bg-blue-100 px-1 rounded text-xs">GARMIN_PASSWORD</code>{" "}
                      are set in the backend <code className="bg-blue-100 px-1 rounded text-xs">.env</code>
                    </li>
                    <li>
                      Click <strong>Sync from Garmin</strong>, then <strong>Refresh</strong> if charts stay empty
                    </li>
                  </ol>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {error && (
          <Card className="border-destructive">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
                <div>
                  <p className="font-medium text-destructive">Sync Error</p>
                  <p className="text-sm text-muted-foreground">{error}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Ensure GARMIN_EMAIL and GARMIN_PASSWORD are set in backend .env
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="overview" className="gap-2">
              <Watch className="h-4 w-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="trends" className="gap-2">
              <TrendingUp className="h-4 w-4" />
              <span className="hidden sm:inline">Trends</span>
            </TabsTrigger>
            <TabsTrigger value="correlations" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              <span className="hidden sm:inline">Correlations</span>
            </TabsTrigger>
            <TabsTrigger value="sleep" className="gap-2">
              <Moon className="h-4 w-4" />
              <span className="hidden sm:inline">Sleep</span>
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Quick Metrics Grid */}
            <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
              <MetricCard
                title="HRV (Overnight)"
                value={metrics?.hrv_overnight?.toFixed(1)}
                unit="ms"
                icon={Activity}
                color="bg-blue-500"
              />
              <MetricCard
                title="Resting HR"
                value={metrics?.resting_hr}
                unit="bpm"
                icon={Heart}
                color="bg-red-500"
              />
              <MetricCard
                title="SpO2"
                value={metrics?.spo2_avg?.toFixed(0)}
                unit="%"
                icon={Wind}
                color="bg-cyan-500"
              />
              <MetricCard
                title="Stress"
                value={metrics?.stress_avg?.toFixed(0)}
                icon={Brain}
                color="bg-orange-500"
              />
            </div>

            {/* Gauges Row */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="pb-0 pt-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Activity className="h-4 w-4 text-blue-500" />
                    HRV RMSSD
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 pb-2">
                  <CleanGauge
                    value={metrics?.hrv_overnight ?? null}
                    min={10}
                    max={100}
                    unit="ms"
                    thresholds={[
                      [0, SCIENTIFIC_COLORS.danger],
                      [0.3, SCIENTIFIC_COLORS.warning],
                      [0.5, SCIENTIFIC_COLORS.primary],
                      [0.7, SCIENTIFIC_COLORS.success],
                    ]}
                    label="Parasympathetic"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-0 pt-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Battery className="h-4 w-4 text-green-500" />
                    Body Battery
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 pb-2">
                  <CleanGauge
                    value={metrics?.body_battery_high ?? null}
                    min={0}
                    max={100}
                    unit="%"
                    thresholds={[
                      [0, SCIENTIFIC_COLORS.danger],
                      [0.25, SCIENTIFIC_COLORS.warning],
                      [0.5, SCIENTIFIC_COLORS.primary],
                      [0.75, SCIENTIFIC_COLORS.success],
                    ]}
                    label="Energy Reserve"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-0 pt-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Moon className="h-4 w-4 text-purple-500" />
                    Sleep Score
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 pb-2">
                  <CleanGauge
                    value={metrics?.sleep_score ?? null}
                    min={0}
                    max={100}
                    thresholds={[
                      [0, SCIENTIFIC_COLORS.danger],
                      [0.4, SCIENTIFIC_COLORS.warning],
                      [0.7, SCIENTIFIC_COLORS.success],
                    ]}
                    label="Quality"
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-0 pt-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Wind className="h-4 w-4 text-cyan-500" />
                    SpO2
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 pb-2">
                  <CleanGauge
                    value={metrics?.spo2_avg ?? null}
                    min={85}
                    max={100}
                    unit="%"
                    thresholds={[
                      [0, SCIENTIFIC_COLORS.danger],
                      [0.6, SCIENTIFIC_COLORS.warning],
                      [0.85, SCIENTIFIC_COLORS.success],
                    ]}
                    label="Oxygen Saturation"
                  />
                </CardContent>
              </Card>
            </div>

            {/* Space Weather Panel */}
            <SpaceWeatherPanel
              spaceWeather={spaceWeather}
              loading={spaceWeatherLoading}
            />

            {/* Additional Metrics */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Additional Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Sleep Duration</p>
                    <p className="text-lg font-semibold">
                      {metrics?.sleep_duration_hours?.toFixed(1) ?? "—"} h
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Respiration (Sleep)</p>
                    <p className="text-lg font-semibold">
                      {metrics?.respiration_sleep?.toFixed(1) ?? "—"} br/min
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">Steps</p>
                    <p className="text-lg font-semibold">
                      {metrics?.steps?.toLocaleString() ?? "—"}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">VO2max</p>
                    <p className="text-lg font-semibold">
                      {metrics?.vo2max?.toFixed(0) ?? "—"} mL/kg/min
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Trends Tab */}
          <TabsContent value="trends" className="space-y-6">
            {dates.length > 0 ? (
              <>
                {/* HRV & RHR Time Series */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription className="text-xs">
                      Higher HRV indicates better parasympathetic tone; lower RHR suggests cardiovascular efficiency
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <EChartsWrapper
                      option={buildTimeSeriesChart(
                        dates,
                        [
                          { name: "HRV (ms)", data: hrvData, color: CHART_COLORS.hrv },
                          { name: "RHR (bpm)", data: rhrData, color: CHART_COLORS.rhr, yAxisIndex: 1 },
                        ],
                        [
                          { name: "ms", position: "left", color: CHART_COLORS.hrv },
                          { name: "bpm", position: "right", color: CHART_COLORS.rhr },
                        ],
                        "HRV & Resting Heart Rate"
                      )}
                      height={300}
                      showToolbox={false}
                    />
                  </CardContent>
                </Card>

                {/* Sleep & SpO2 */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription className="text-xs">
                      Sleep duration and nocturnal SpO2 - desaturation events may affect HRV
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <EChartsWrapper
                      option={buildTimeSeriesChart(
                        dates,
                        [
                          { name: "Sleep (h)", data: sleepData, color: CHART_COLORS.sleep },
                          { name: "SpO2 (%)", data: spo2Data, color: CHART_COLORS.spo2, yAxisIndex: 1 },
                        ],
                        [
                          { name: "Hours", position: "left", color: CHART_COLORS.sleep },
                          { name: "%", position: "right", color: CHART_COLORS.spo2 },
                        ],
                        "Sleep Duration & SpO2"
                      )}
                      height={300}
                      showToolbox={false}
                    />
                  </CardContent>
                </Card>

                {/* Stress & Respiration */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription className="text-xs">
                      Stress levels and sleep respiration rate - elevated respiration may indicate sleep disturbance
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <EChartsWrapper
                      option={buildTimeSeriesChart(
                        dates,
                        [
                          { name: "Stress", data: stressData, color: CHART_COLORS.stress },
                          { name: "Resp (br/min)", data: respirationData, color: CHART_COLORS.respiration, yAxisIndex: 1 },
                        ],
                        [
                          { name: "Score", position: "left", color: CHART_COLORS.stress },
                          { name: "br/min", position: "right", color: CHART_COLORS.respiration },
                        ],
                        "Stress & Sleep Respiration"
                      )}
                      height={300}
                      showToolbox={false}
                    />
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="pt-6 flex items-center justify-center h-64">
                  <div className="text-center max-w-md space-y-2">
                    <TrendingUp className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">No trend history yet for this user.</p>
                    <p className="text-xs text-muted-foreground">
                      Sync from Garmin, widen sync days in Settings, and confirm the User ID and
                      active mission match where Streamlit saved Garmin rows.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Correlations Tab */}
          <TabsContent value="correlations" className="space-y-6">
            {dates.length > 5 ? (
              <>
                <div className="grid gap-4 md:grid-cols-2">
                  {/* HRV vs Sleep */}
                  <Card>
                    <CardContent className="pt-4">
                      <EChartsWrapper
                        option={buildCorrelationChart(
                          sleepData,
                          hrvData,
                          "Sleep (h)",
                          "HRV (ms)",
                          "Sleep Duration vs HRV"
                        )}
                        height={280}
                        showToolbox={false}
                      />
                    </CardContent>
                  </Card>

                  {/* HRV vs Stress */}
                  <Card>
                    <CardContent className="pt-4">
                      <EChartsWrapper
                        option={buildCorrelationChart(
                          stressData,
                          hrvData,
                          "Stress",
                          "HRV (ms)",
                          "Stress vs HRV"
                        )}
                        height={280}
                        showToolbox={false}
                      />
                    </CardContent>
                  </Card>

                  {/* SpO2 vs Sleep */}
                  <Card>
                    <CardContent className="pt-4">
                      <EChartsWrapper
                        option={buildCorrelationChart(
                          sleepData,
                          spo2Data,
                          "Sleep (h)",
                          "SpO2 (%)",
                          "Sleep vs SpO2"
                        )}
                        height={280}
                        showToolbox={false}
                      />
                    </CardContent>
                  </Card>

                  {/* RHR vs HRV */}
                  <Card>
                    <CardContent className="pt-4">
                      <EChartsWrapper
                        option={buildCorrelationChart(
                          rhrData,
                          hrvData,
                          "RHR (bpm)",
                          "HRV (ms)",
                          "Resting HR vs HRV"
                        )}
                        height={280}
                        showToolbox={false}
                      />
                    </CardContent>
                  </Card>
                </div>

                {/* Scientific Context */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Correlation Analysis Notes</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground space-y-2">
                    <p>
                      • <strong>HRV-Sleep correlation</strong>: Higher sleep quality and duration 
                      typically associate with improved HRV (Shaffer &amp; Ginsberg, 2017)
                    </p>
                    <p>
                      • <strong>HRV-Stress correlation</strong>: Negative correlation expected; 
                      chronic stress suppresses parasympathetic activity (Thayer et al., 2012)
                    </p>
                    <p>
                      • <strong>SpO2 variations</strong>: Nocturnal desaturations may predict 
                      reduced HRV the following day (sleep-disordered breathing effect)
                    </p>
                    <p>
                      • <strong>Solar activity influence</strong>: Geomagnetic storms (Kp≥5) 
                      associated with decreased HRV in susceptible individuals (Sci Rep, 2018)
                    </p>
                  </CardContent>
                </Card>
              </>
            ) : dates.length > 0 ? (
              <Card>
                <CardContent className="pt-6 flex items-center justify-center min-h-48">
                  <div className="text-center max-w-md space-y-2">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">
                      Correlations need at least <strong>6 days</strong> with valid dates in history.
                    </p>
                    <p className="text-xs text-muted-foreground">
                      You currently have {dates.length} day(s). Increase &quot;Sync days&quot; in Settings
                      and sync again, or wait until more daily rows accumulate.
                    </p>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="pt-6 flex items-center justify-center min-h-48">
                  <div className="text-center max-w-md space-y-2">
                    <BarChart3 className="h-12 w-12 mx-auto mb-3 text-muted-foreground opacity-50" />
                    <p className="text-muted-foreground">No history rows with dates for correlations.</p>
                    <p className="text-xs text-muted-foreground">
                      After a successful sync you need six or more distinct days for scatter plots.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Sleep Tab */}
          <TabsContent value="sleep" className="space-y-6">
            <Card className="border-dashed">
              <CardContent className="py-3 text-xs text-muted-foreground">
                Sleep <strong>stage minutes</strong> (deep / REM / light) come from Garmin daily sleep
                summaries when the device reports them; duration, score, and efficiency below always
                reflect stored daily metrics. If architecture is empty, Garmin may not have returned
                stage seconds for the latest night yet—sync a longer window or another day.
              </CardContent>
            </Card>
            {/* Sleep Summary */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Duration"
                value={metrics?.sleep_duration_hours?.toFixed(1)}
                unit="h"
                icon={Moon}
                color="bg-purple-500"
              />
              <MetricCard
                title="Sleep Score"
                value={metrics?.sleep_score}
                icon={Zap}
                color="bg-indigo-500"
              />
              <MetricCard
                title="Efficiency"
                value={metrics?.sleep_efficiency ? `${(metrics.sleep_efficiency * 100).toFixed(0)}` : null}
                unit="%"
                icon={Activity}
                color="bg-violet-500"
              />
              <MetricCard
                title="Respiration"
                value={metrics?.respiration_sleep?.toFixed(1)}
                unit="br/min"
                icon={Wind}
                color="bg-teal-500"
              />
            </div>

            {/* Sleep Stages */}
            {(metrics?.sleep_deep_minutes || metrics?.sleep_rem_minutes || metrics?.sleep_light_minutes) && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Sleep Architecture</CardTitle>
                  <CardDescription className="text-xs">
                    Deep sleep critical for physical recovery; REM for cognitive consolidation
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 rounded-lg bg-indigo-500/10 border border-indigo-500/30">
                      <p className="text-3xl font-bold text-indigo-500">
                        {metrics?.sleep_deep_minutes ?? "—"}
                      </p>
                      <p className="text-sm text-muted-foreground">Deep (min)</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Target: 60-90 min
                      </p>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-purple-500/10 border border-purple-500/30">
                      <p className="text-3xl font-bold text-purple-500">
                        {metrics?.sleep_rem_minutes ?? "—"}
                      </p>
                      <p className="text-sm text-muted-foreground">REM (min)</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Target: 90-120 min
                      </p>
                    </div>
                    <div className="text-center p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                      <p className="text-3xl font-bold text-blue-500">
                        {metrics?.sleep_light_minutes ?? "—"}
                      </p>
                      <p className="text-sm text-muted-foreground">Light (min)</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        ~50% of total
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Sleep & HRV Relationship */}
            {dates.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs">
                    Sleep quality directly impacts overnight HRV recovery
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <EChartsWrapper
                    option={buildTimeSeriesChart(
                      dates,
                      [
                        { name: "Sleep Score", data: history.map((m) => m.sleep_score).reverse(), color: CHART_COLORS.sleep },
                        { name: "HRV (ms)", data: hrvData, color: CHART_COLORS.hrv, yAxisIndex: 1 },
                      ],
                      [
                        { name: "Score", position: "left", color: CHART_COLORS.sleep },
                        { name: "ms", position: "right", color: CHART_COLORS.hrv },
                      ],
                      "Sleep Score & HRV Recovery"
                    )}
                    height={300}
                    showToolbox={false}
                  />
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>

        {/* Scientific References */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scientific Context</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              • <strong>HRV-Solar Activity</strong>: Long-term studies show autonomic nervous system 
              responds to geomagnetic changes, with higher solar wind intensity associated with 
              biological stress response (McCraty et al., Nature Sci Rep, 2018)
            </p>
            <p>
              • <strong>Overnight RMSSD</strong>: Reflects parasympathetic activity during sleep; 
              higher values indicate better cardiovascular recovery (Plews et al., 2013)
            </p>
            <p>
              • <strong>SpO2 &amp; Sleep Quality</strong>: Nocturnal desaturations (&lt;90%) may indicate 
              sleep-disordered breathing affecting HRV (Haba-Rubio et al., 2016)
            </p>
            <Separator className="my-3" />
            <p className="text-xs italic">
              Data synchronized from Garmin Connect via python-garminconnect library.
              Credentials stored securely in backend environment variables.
            </p>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
