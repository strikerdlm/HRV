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
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { listUsers, getSpaceWeather } from "@/lib/api";
import type { UserProfile, SpaceWeatherSnapshot } from "@/types";
import { formatDateTime } from "@/lib/utils";

// Stat card component
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
                trend === "up"
                  ? "text-success"
                  : trend === "down"
                  ? "text-danger"
                  : "text-muted-foreground"
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

// Space weather widget
function SpaceWeatherWidget({ data }: { data: SpaceWeatherSnapshot | null }) {
  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-warning" />
            Space Weather
          </CardTitle>
          <CardDescription>Loading space weather data...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const getKpStatus = (kp: number | null) => {
    if (kp === null) return { label: "Unknown", color: "secondary" as const };
    if (kp < 4) return { label: "Quiet", color: "success" as const };
    if (kp < 6) return { label: "Active", color: "warning" as const };
    return { label: "Storm", color: "destructive" as const };
  };

  const kpStatus = getKpStatus(data.kp_index);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-warning" />
            Space Weather
          </CardTitle>
          <Badge variant={kpStatus.color}>{kpStatus.label}</Badge>
        </div>
        <CardDescription>
          {data.fetched_at
            ? `Updated ${formatDateTime(data.fetched_at)}`
            : "Real-time NOAA/NASA data"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-muted-foreground">Kp Index</p>
            <p className="text-lg font-semibold">
              {data.kp_index?.toFixed(1) ?? "N/A"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">F10.7 Flux</p>
            <p className="text-lg font-semibold">
              {data.f10_7_flux?.toFixed(0) ?? "N/A"} SFU
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Solar Wind</p>
            <p className="text-lg font-semibold">
              {data.solar_wind_speed?.toFixed(0) ?? "N/A"} km/s
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Dst Index</p>
            <p className="text-lg font-semibold">
              {data.dst_index?.toFixed(0) ?? "N/A"} nT
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Quick actions
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

// Recent activity
function RecentActivity({ users }: { users: UserProfile[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Crew Profiles</CardTitle>
        <CardDescription>Active mission personnel</CardDescription>
      </CardHeader>
      <CardContent>
        {users.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No crew profiles found. Add crew members to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {users.slice(0, 5).map((user) => (
              <div
                key={user.user_id}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-xs font-medium text-primary">
                      {(user.full_name || user.username).charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      {user.full_name || user.username}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      @{user.username}
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className="capitalize">
                  {user.sex}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const [spaceWeather, setSpaceWeather] = React.useState<SpaceWeatherSnapshot | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const [usersData, weatherData] = await Promise.all([
          listUsers().catch(() => ({ users: [], total: 0 })),
          getSpaceWeather().catch(() => null),
        ]);
        setUsers(usersData.users);
        setSpaceWeather(weatherData);
      } catch (error) {
        console.error("Failed to fetch data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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
          <StatCard
            title="Crew Members"
            value={users.length}
            description="Active personnel"
            icon={Users}
            color="primary"
          />
          <StatCard
            title="Experiments"
            value="0"
            description="In progress"
            icon={FlaskConical}
            color="success"
          />
          <StatCard
            title="Scheduled Tasks"
            value="0"
            description="This week"
            icon={Calendar}
            color="warning"
          />
          <StatCard
            title="HRV Analyses"
            value="0"
            description="Total recorded"
            icon={Activity}
            color="primary"
          />
        </motion.div>

        {/* Main Content Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="lg:col-span-2"
          >
            <RecentActivity users={users} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <SpaceWeatherWidget data={spaceWeather} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
          >
            <QuickActions />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.4 }}
            className="lg:col-span-2"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-warning" />
                  System Alerts
                </CardTitle>
                <CardDescription>
                  Important notifications and warnings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground text-center py-8">
                  No active alerts. All systems nominal.
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  );
}
