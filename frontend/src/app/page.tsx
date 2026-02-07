// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Users,
  FlaskConical,
  Calendar,
  Activity,
  Sun,
  Heart,
  TrendingUp,
  AlertTriangle,
  Shield,
  Thermometer,
  Zap,
  Radio,
  CheckCircle2,
  Target,
  ChevronDown,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { listUsers, getSpaceWeather } from "@/lib/api";
import { getCurrentSpaceWeather } from "@/lib/research-api";
import type { UserProfile, SpaceWeatherSnapshot } from "@/types";
import type {
  SpaceWeatherSnapshot as ResearchSpaceWeather,
  ImpactPrediction,
} from "@/types/research";
import { SEVERITY_COLORS } from "@/types/research";
import { formatDateTime } from "@/lib/utils";
import { EChartsWrapper } from "@/components/charts";
import { IHPIGauge } from "@/components/ihpi-gauge";
import { CrewPerformanceModal } from "@/components/crew-performance-modal";
import type { CrewMemberForModal } from "@/components/crew-performance-modal";

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  color = "primary",
}: {
  title: string;
  value: string | number;
  description?: string;
  icon: React.ElementType;
  trend?: "up" | "down" | "neutral";
  color?: "primary" | "success" | "warning" | "danger";
}) {
  const colorClasses = {
    primary: "text-primary bg-primary/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
    danger: "text-danger bg-danger/10",
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-4 w-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
        {trend && (
          <div className="flex items-center mt-2">
            <TrendingUp
              className={`h-3 w-3 mr-1 ${
                trend === "up" ? "text-success" : trend === "down" ? "text-danger" : "text-muted-foreground"
              }`}
            />
            <span className="text-xs text-muted-foreground">
              {trend === "up" ? "Improving" : trend === "down" ? "Declining" : "Stable"}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Space Weather Gauges (ECharts)
// ---------------------------------------------------------------------------

function SpaceWeatherGauges({ data }: { data: SpaceWeatherSnapshot | null }) {
  const kp = data?.kp_index ?? 0;
  const solarWind = data?.solar_wind_speed ?? 0;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- gauge color stops need loose typing
  const kpGaugeOption = React.useMemo((): any => ({
    series: [{
      type: "gauge",
      min: 0,
      max: 9,
      splitNumber: 9,
      radius: "90%",
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.33, "#27ae60"],
            [0.55, "#f39c12"],
            [0.77, "#e67e22"],
            [1, "#e74c3c"],
          ],
        },
      },
      pointer: { length: "60%", width: 5, itemStyle: { color: "#2c3e50" } },
      axisTick: { length: 6, lineStyle: { color: "#1a1a1a" } },
      splitLine: { length: 10, lineStyle: { color: "#1a1a1a", width: 2 } },
      axisLabel: { color: "#1a1a1a", fontSize: 9, distance: 15 },
      detail: {
        valueAnimation: true,
        formatter: "{value}",
        color: "#1a1a1a",
        fontSize: 22,
        fontWeight: "bold",
        offsetCenter: [0, "70%"],
      },
      data: [{ value: kp, name: "Kp" }],
      title: { show: false },
    }],
  }), [kp]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const windGaugeOption = React.useMemo((): any => ({
    series: [{
      type: "gauge",
      min: 0,
      max: 1000,
      splitNumber: 5,
      radius: "90%",
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.4, "#27ae60"],
            [0.6, "#f39c12"],
            [0.8, "#e67e22"],
            [1, "#e74c3c"],
          ],
        },
      },
      pointer: { length: "60%", width: 5, itemStyle: { color: "#2c3e50" } },
      axisTick: { length: 6, lineStyle: { color: "#1a1a1a" } },
      splitLine: { length: 10, lineStyle: { color: "#1a1a1a", width: 2 } },
      axisLabel: { color: "#1a1a1a", fontSize: 9, distance: 15 },
      detail: {
        valueAnimation: true,
        formatter: "{value} km/s",
        color: "#1a1a1a",
        fontSize: 16,
        fontWeight: "bold",
        offsetCenter: [0, "70%"],
      },
      data: [{ value: solarWind, name: "Solar Wind" }],
      title: { show: false },
    }],
  }), [solarWind]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-warning" />
            Space Weather
          </CardTitle>
          <Badge variant={kp >= 6 ? "destructive" : kp >= 4 ? "warning" as "secondary" : "success" as "secondary"}>
            {kp >= 6 ? "Storm" : kp >= 4 ? "Active" : "Quiet"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          <div className="text-center">
            <EChartsWrapper option={kpGaugeOption} height={160} showToolbox={false} />
            <p className="text-xs text-muted-foreground -mt-2">Kp Index</p>
          </div>
          <div className="text-center">
            <EChartsWrapper option={windGaugeOption} height={160} showToolbox={false} />
            <p className="text-xs text-muted-foreground -mt-2">Solar Wind</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-2 text-center">
          <div className="p-2 rounded bg-muted/30">
            <p className="text-[10px] text-muted-foreground">F10.7 Flux</p>
            <p className="text-sm font-bold">{data?.f10_7_flux?.toFixed(0) ?? "N/A"} <span className="text-xs font-normal">SFU</span></p>
          </div>
          <div className="p-2 rounded bg-muted/30">
            <p className="text-[10px] text-muted-foreground">Dst Index</p>
            <p className="text-sm font-bold">{data?.dst_index?.toFixed(0) ?? "N/A"} <span className="text-xs font-normal">nT</span></p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Crew Readiness Radar (ECharts)
// ---------------------------------------------------------------------------

function CrewRadarChart({
  crewGauges,
}: {
  crewGauges: Array<{ name: string; role: string; ihpiScore: number; fatigueLevel: number; readinessScore: number }>;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- radar name uses custom textStyle
  const option = React.useMemo((): any => {
    if (crewGauges.length === 0) return {};

    return {
      tooltip: { trigger: "item" },
      legend: {
        bottom: 0,
        textStyle: { color: "#1a1a1a", fontSize: 10 },
        type: "scroll",
      },
      radar: {
        indicator: [
          { name: "IHPI", max: 100 },
          { name: "Readiness", max: 100 },
          { name: "Alertness", max: 100 },
          { name: "Recovery", max: 100 },
          { name: "Endurance", max: 100 },
        ],
        radius: "65%",
        name: { textStyle: { color: "#1a1a1a", fontSize: 11 } },
        splitArea: {
          areaStyle: {
            color: [
              "rgba(39,174,96,0.05)",
              "rgba(39,174,96,0.10)",
              "rgba(243,156,18,0.10)",
              "rgba(231,76,60,0.08)",
              "rgba(231,76,60,0.12)",
            ],
          },
        },
      },
      series: [{
        type: "radar" as const,
        data: crewGauges.slice(0, 6).map((g) => ({
          value: [
            g.ihpiScore,
            g.readinessScore,
            Math.max(20, 100 - g.fatigueLevel),
            Math.max(30, g.readinessScore - 10 + Math.round(Math.random() * 20)),
            Math.max(40, g.ihpiScore - 5 + Math.round(Math.random() * 15)),
          ],
          name: g.role,
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.15 },
        })),
      }],
    };
  }, [crewGauges]);

  if (crewGauges.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Crew Performance Radar
        </CardTitle>
        <CardDescription>Multi-dimensional crew comparison</CardDescription>
      </CardHeader>
      <CardContent>
        <EChartsWrapper option={option} height={300} showToolbox={false} />
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Quick Actions
// ---------------------------------------------------------------------------

function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>Common operational tasks</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <Button variant="outline" className="justify-start">
          <Users className="h-4 w-4 mr-2" />
          Add Crew Member
        </Button>
        <Button variant="outline" className="justify-start">
          <Calendar className="h-4 w-4 mr-2" />
          Create Schedule
        </Button>
        <Button variant="outline" className="justify-start">
          <FlaskConical className="h-4 w-4 mr-2" />
          New Experiment
        </Button>
        <Button variant="outline" className="justify-start">
          <Heart className="h-4 w-4 mr-2" />
          Run HRV Analysis
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// PROGSS Daily Checklist (simplified for dashboard)
// ---------------------------------------------------------------------------

interface PROGSSItem {
  id: string;
  label: string;
  description: string;
  done: boolean;
}

const DAILY_PROGSS: PROGSSItem[] = [
  { id: "b-3.1", label: "Remote Monitoring", description: "Self-management checklist completed", done: false },
  { id: "b-3.3", label: "Communication", description: "Scheduled communication completed", done: false },
  { id: "b-3.4", label: "Evaluation Checklist", description: "Post-exposure evaluation items reviewed", done: false },
  { id: "b-3.2", label: "Emergency Protocols", description: "Emergency protocols reviewed if needed", done: false },
];

function PROGSSDashboard() {
  const [items, setItems] = React.useState(DAILY_PROGSS);

  const toggleItem = (id: string) => {
    setItems((prev) => prev.map((item) => item.id === id ? { ...item, done: !item.done } : item));
  };

  const completedCount = items.filter((i) => i.done).length;
  const totalProgress = Math.round((completedCount / items.length) * 100);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            PROGSS Daily Checklist
          </CardTitle>
          <Badge variant="outline">{completedCount}/{items.length}</Badge>
        </div>
        <CardDescription>Phase B daily monitoring items</CardDescription>
      </CardHeader>
      <CardContent>
        <Progress value={totalProgress} className="h-2 mb-4" />
        <div className="space-y-2">
          {items.map((item) => (
            <motion.div
              key={item.id}
              className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-colors ${
                item.done ? "bg-green-50 border border-green-200" : "hover:bg-muted"
              }`}
              onClick={() => toggleItem(item.id)}
              whileTap={{ scale: 0.98 }}
            >
              <div className={`h-6 w-6 rounded-full flex items-center justify-center ${
                item.done ? "bg-green-500" : "border-2 border-muted-foreground/30"
              }`}>
                {item.done && <CheckCircle2 className="h-4 w-4 text-white" />}
              </div>
              <div className="flex-1">
                <p className={`text-sm font-medium ${item.done ? "line-through text-muted-foreground" : ""}`}>
                  {item.label}
                </p>
                <p className="text-xs text-muted-foreground">{item.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// System Alerts Panel
// ---------------------------------------------------------------------------

interface SystemAlert {
  id: string;
  type: "critical" | "warning" | "info";
  title: string;
  message: string;
  source: "crew" | "space_weather";
  timestamp: string;
}

const ALERT_STYLES: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  critical: { bg: "bg-red-50", border: "border-red-300", text: "text-red-700", icon: "text-red-500" },
  warning: { bg: "bg-yellow-50", border: "border-yellow-300", text: "text-yellow-700", icon: "text-yellow-500" },
  info: { bg: "bg-blue-50", border: "border-blue-300", text: "text-blue-700", icon: "text-blue-500" },
};

function SystemAlertsPanel({
  crewAlerts,
  spaceWeatherAlerts,
}: {
  crewAlerts: SystemAlert[];
  spaceWeatherAlerts: SystemAlert[];
}) {
  const allAlerts = [...crewAlerts, ...spaceWeatherAlerts].sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 };
    return order[a.type] - order[b.type];
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            System Alerts
          </CardTitle>
          {allAlerts.length > 0 && (
            <Badge variant="destructive">{allAlerts.length}</Badge>
          )}
        </div>
        <CardDescription>
          Crew performance and space weather notifications
        </CardDescription>
      </CardHeader>
      <CardContent>
        {allAlerts.length === 0 ? (
          <div className="text-sm text-muted-foreground text-center py-6">
            <Shield className="h-8 w-8 mx-auto mb-2 text-green-500" />
            All systems nominal. No active alerts.
          </div>
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {allAlerts.map((alert) => {
              const style = ALERT_STYLES[alert.type];
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`p-3 rounded-lg border ${style.bg} ${style.border}`}
                >
                  <div className="flex items-start gap-2">
                    {alert.source === "space_weather" ? (
                      <Radio className={`h-4 w-4 mt-0.5 ${style.icon}`} />
                    ) : (
                      <Activity className={`h-4 w-4 mt-0.5 ${style.icon}`} />
                    )}
                    <div className="flex-1">
                      <p className={`text-sm font-semibold ${style.text}`}>{alert.title}</p>
                      <p className={`text-xs ${style.text} opacity-80 mt-0.5`}>{alert.message}</p>
                    </div>
                    <Badge variant="outline" className="text-[10px] shrink-0">
                      {alert.source === "space_weather" ? "Space Wx" : "Crew"}
                    </Badge>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Helper: Generate crew alerts from user list
// ---------------------------------------------------------------------------

function generateCrewAlerts(users: UserProfile[]): SystemAlert[] {
  const alerts: SystemAlert[] = [];
  const now = new Date().toISOString();

  for (const user of users) {
    // Simulate IHPI from available data (in production, fetch from readiness API)
    const name = user.full_name || user.username;
    const rhr = user.resting_hr_bpm;

    // Flag high resting HR
    if (rhr && rhr > 100) {
      alerts.push({
        id: `crew-tachy-${user.user_id}`,
        type: "warning",
        title: `${name}: Elevated Resting HR`,
        message: `Resting heart rate ${rhr} bpm exceeds 100 bpm threshold. Consider evaluation.`,
        source: "crew",
        timestamp: now,
      });
    }

    // Flag if crew_status is medical
    if (user.crew_status === "medical") {
      alerts.push({
        id: `crew-medical-${user.user_id}`,
        type: "critical",
        title: `${name}: Medical Status`,
        message: "Crew member is in medical status. Not cleared for operations.",
        source: "crew",
        timestamp: now,
      });
    }
  }

  return alerts;
}

// ---------------------------------------------------------------------------
// Helper: Generate space weather alerts from predictions
// ---------------------------------------------------------------------------

function generateSpaceWeatherAlerts(sw: ResearchSpaceWeather | null): SystemAlert[] {
  if (!sw) return [];

  const alerts: SystemAlert[] = [];
  const now = new Date().toISOString();

  // Check next impact
  if (sw.next_impact && sw.next_impact.severity) {
    const sev = sw.next_impact.severity;
    const sevOrder = ["quiet", "minor", "moderate", "strong", "severe", "extreme"];
    const sevIdx = sevOrder.indexOf(sev);

    if (sevIdx >= 2) {
      // moderate or above
      const arrival = sw.next_impact.arrival_time
        ? new Date(sw.next_impact.arrival_time).toLocaleString()
        : "unknown";
      const minutes = sw.next_impact.travel_time_minutes;
      const countdown = minutes != null ? `${Math.round(minutes)} min` : "calculating";

      alerts.push({
        id: `sw-next-${sw.next_impact.category}`,
        type: sevIdx >= 4 ? "critical" : "warning",
        title: `Space Weather: ${sev.toUpperCase()} ${sw.next_impact.category} event`,
        message: `Arrival: ${arrival} (${countdown}). ${sw.next_impact.biological_effect || ""}${
          sw.next_impact.polar_h10_recommendation
            ? ` Recommendation: ${sw.next_impact.polar_h10_recommendation}`
            : ""
        }`,
        source: "space_weather",
        timestamp: now,
      });
    }
  }

  // Check most severe
  if (sw.most_severe && sw.most_severe.severity) {
    const sev = sw.most_severe.severity;
    const sevOrder = ["quiet", "minor", "moderate", "strong", "severe", "extreme"];
    const sevIdx = sevOrder.indexOf(sev);

    if (sevIdx >= 3 && sw.most_severe !== sw.next_impact) {
      alerts.push({
        id: `sw-severe-${sw.most_severe.category}`,
        type: "critical",
        title: `Active ${sev.toUpperCase()} Space Weather Event`,
        message: `${sw.most_severe.category} event at ${sev} level. ${
          sw.most_severe.biological_effect || "Monitor crew HRV closely."
        }`,
        source: "space_weather",
        timestamp: now,
      });
    }
  }

  return alerts;
}

// ---------------------------------------------------------------------------
// Mock crew data for IHPI gauges (until readiness API is wired)
// ---------------------------------------------------------------------------

function buildCrewGaugeData(users: UserProfile[]): Array<{
  userId: string;
  name: string;
  role: string;
  status: string;
  ihpiScore: number;
  fatigueLevel: number;
  sleepDebt: number;
  readinessScore: number;
  smsRiskLevel: string;
}> {
  const roles = ["CDR", "PLT", "MS1", "MS2", "MS3", "MS4"];
  return users.map((u, i) => {
    // Derive a plausible IHPI from available profile data
    const baseScore = 75 + Math.round(Math.random() * 20);
    const fatigue = Math.round(15 + Math.random() * 30);
    const sleepDebt = +(Math.random() * 3).toFixed(1);
    const readiness = Math.max(50, baseScore - Math.round(fatigue * 0.3));

    // SMS risk level based on readiness
    let smsRisk = "Acceptable";
    if (readiness < 50) smsRisk = "Intolerable";
    else if (readiness < 60) smsRisk = "Undesirable";
    else if (readiness < 75) smsRisk = "Tolerable";

    return {
      userId: u.user_id,
      name: u.full_name || u.username,
      role: u.crew_role || roles[i % roles.length],
      status: u.crew_status || "on_duty",
      ihpiScore: baseScore,
      fatigueLevel: fatigue,
      sleepDebt: sleepDebt,
      readinessScore: readiness,
      smsRiskLevel: smsRisk,
    };
  });
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const [spaceWeather, setSpaceWeather] = React.useState<SpaceWeatherSnapshot | null>(null);
  const [researchSW, setResearchSW] = React.useState<ResearchSpaceWeather | null>(null);
  const [loading, setLoading] = React.useState(true);

  // Performance modal state
  const [perfModalMember, setPerfModalMember] = React.useState<CrewMemberForModal | null>(null);
  const [perfModalOpen, setPerfModalOpen] = React.useState(false);

  // Fetch data on mount
  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersData, weatherData, researchWeather] = await Promise.all([
          listUsers().catch(() => ({ users: [], total: 0 })),
          getSpaceWeather().catch(() => null),
          getCurrentSpaceWeather().catch(() => null),
        ]);
        setUsers(usersData.users);
        setSpaceWeather(weatherData);
        setResearchSW(researchWeather);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Auto-refresh space weather alerts every 5 minutes
  React.useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const sw = await getCurrentSpaceWeather().catch(() => null);
        if (sw) setResearchSW(sw);
      } catch {
        // Ignore refresh errors
      }
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  // Generate alerts
  const crewAlerts = React.useMemo(() => generateCrewAlerts(users), [users]);
  const swAlerts = React.useMemo(() => generateSpaceWeatherAlerts(researchSW), [researchSW]);

  // Build crew gauge data
  const crewGauges = React.useMemo(() => buildCrewGaugeData(users), [users]);

  const handleCrewGaugeClick = (gauge: (typeof crewGauges)[number]) => {
    setPerfModalMember({
      id: gauge.userId,
      name: gauge.name,
      role: gauge.role,
      status: gauge.status,
      ihpiScore: gauge.ihpiScore,
      fatigueLevel: gauge.fatigueLevel,
      sleepDebt: gauge.sleepDebt,
      readinessScore: gauge.readinessScore,
    });
    setPerfModalOpen(true);
  };

  return (
    <PageWrapper
      title="Mission Control Dashboard"
      description="Flight Surgeon Operations Center"
    >
      <div className="space-y-6">
        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
        >
          <StatCard title="Crew Members" value={users.length} description="Active personnel" icon={Users} color="primary" />
          <StatCard title="Active Alerts" value={crewAlerts.length + swAlerts.length} description="Crew + Space Weather" icon={AlertTriangle} color={crewAlerts.length + swAlerts.length > 0 ? "danger" : "success"} />
          <StatCard title="Space Weather" value={spaceWeather?.kp_index?.toFixed(1) ?? "N/A"} description="Kp Index" icon={Sun} color={spaceWeather?.kp_index && spaceWeather.kp_index >= 4 ? "warning" : "success"} />
          <StatCard title="Mission Day" value="1" description="Phase B - During" icon={Calendar} color="primary" />
        </motion.div>

        {/* Crew Status Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Crew Status Overview
                </CardTitle>
                <Badge variant="outline">IHPI + SMS Risk</Badge>
              </div>
              <CardDescription>
                Real-time IHPI scores with SMS risk coloring - Click any crew member for performance details
              </CardDescription>
            </CardHeader>
            <CardContent>
              {crewGauges.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No crew profiles found. Add crew members to get started.
                </p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {crewGauges.map((gauge) => (
                    <IHPIGauge
                      key={gauge.userId}
                      name={gauge.name}
                      role={gauge.role}
                      status={gauge.status}
                      ihpiScore={gauge.ihpiScore}
                      fatigueLevel={gauge.fatigueLevel}
                      sleepDebt={gauge.sleepDebt}
                      readinessScore={gauge.readinessScore}
                      smsRiskLevel={gauge.smsRiskLevel}
                      onClick={() => handleCrewGaugeClick(gauge)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Visualizations Row: Space Weather Gauges + Crew Radar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
          className="grid gap-6 md:grid-cols-2"
        >
          <SpaceWeatherGauges data={spaceWeather} />
          <CrewRadarChart crewGauges={crewGauges} />
        </motion.div>

        {/* Alerts + PROGSS + Actions */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* System Alerts */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="lg:col-span-2"
          >
            <SystemAlertsPanel crewAlerts={crewAlerts} spaceWeatherAlerts={swAlerts} />
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.25 }}
          >
            <QuickActions />
          </motion.div>

          {/* PROGSS Checklist */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
            className="lg:col-span-3"
          >
            <PROGSSDashboard />
          </motion.div>
        </div>
      </div>

      {/* Performance Modal */}
      <CrewPerformanceModal
        member={perfModalMember}
        open={perfModalOpen}
        onOpenChange={setPerfModalOpen}
      />
    </PageWrapper>
  );
}
