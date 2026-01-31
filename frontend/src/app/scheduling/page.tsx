// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Calendar,
  Clock,
  Users,
  Plus,
  Filter,
  Download,
  RefreshCw,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppStore } from "@/lib/store";

// Sample schedule data for demonstration
const sampleSchedule = [
  {
    id: "1",
    time: "06:00 - 07:00",
    activity: "Post-Sleep Assessment",
    crew: "All Crew",
    category: "medical",
    status: "scheduled",
  },
  {
    id: "2",
    time: "07:00 - 08:00",
    activity: "Morning Exercise",
    crew: "CDR, PLT",
    category: "exercise",
    status: "scheduled",
  },
  {
    id: "3",
    time: "08:00 - 08:30",
    activity: "Breakfast",
    crew: "All Crew",
    category: "meal",
    status: "scheduled",
  },
  {
    id: "4",
    time: "09:00 - 12:00",
    activity: "Science Operations",
    crew: "MS1, MS2",
    category: "experiment",
    status: "scheduled",
  },
  {
    id: "5",
    time: "12:00 - 13:00",
    activity: "Lunch",
    crew: "All Crew",
    category: "meal",
    status: "scheduled",
  },
  {
    id: "6",
    time: "14:00 - 17:00",
    activity: "EVA Preparation",
    crew: "CDR, MS1",
    category: "work",
    status: "pending",
  },
];

const categoryColors: Record<string, string> = {
  medical: "bg-info text-info-foreground",
  exercise: "bg-success text-success-foreground",
  meal: "bg-warning text-warning-foreground",
  experiment: "bg-purple-500 text-white",
  work: "bg-primary text-primary-foreground",
  rest: "bg-muted text-muted-foreground",
};

function ScheduleItem({
  item,
}: {
  item: (typeof sampleSchedule)[0];
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
    >
      <div className="flex-shrink-0 w-32">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Clock className="h-4 w-4 text-muted-foreground" />
          {item.time}
        </div>
      </div>
      <Separator orientation="vertical" className="h-10" />
      <div className="flex-1">
        <h4 className="font-medium">{item.activity}</h4>
        <p className="text-sm text-muted-foreground">{item.crew}</p>
      </div>
      <Badge className={categoryColors[item.category] || "bg-muted"}>
        {item.category}
      </Badge>
    </motion.div>
  );
}

function DaySelector() {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const [selected, setSelected] = React.useState(0);

  return (
    <div className="flex gap-2">
      {days.map((day, index) => (
        <Button
          key={day}
          variant={selected === index ? "default" : "outline"}
          size="sm"
          onClick={() => setSelected(index)}
          className="w-12"
        >
          {day}
        </Button>
      ))}
    </div>
  );
}

export default function SchedulingPage() {
  const { activeMission } = useAppStore();

  return (
    <PageWrapper
      title="Crew Scheduling"
      description="Plan and manage crew activities"
    >
      <div className="space-y-6">
        {/* Header Actions */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-4"
        >
          <div className="flex items-center gap-4">
            <DaySelector />
          </div>
          <div className="flex items-center gap-2">
            <Select defaultValue="all">
              <SelectTrigger className="w-40">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Activities</SelectItem>
                <SelectItem value="medical">Medical</SelectItem>
                <SelectItem value="exercise">Exercise</SelectItem>
                <SelectItem value="experiment">Experiments</SelectItem>
                <SelectItem value="work">Work</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon">
              <Download className="h-4 w-4" />
            </Button>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Activity
            </Button>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Schedule Timeline */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      Daily Schedule
                    </CardTitle>
                    <CardDescription>
                      {activeMission} - January 30, 2026
                    </CardDescription>
                  </div>
                  <Badge variant="outline">GMT-5</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {sampleSchedule.map((item, index) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <ScheduleItem item={item} />
                  </motion.div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            {/* Crew Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Crew Status
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { role: "CDR", name: "Commander", status: "On Duty" },
                  { role: "PLT", name: "Pilot", status: "On Duty" },
                  { role: "MS1", name: "Mission Specialist 1", status: "Rest" },
                  { role: "MS2", name: "Mission Specialist 2", status: "On Duty" },
                ].map((member) => (
                  <div
                    key={member.role}
                    className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                  >
                    <div>
                      <p className="font-medium text-sm">{member.role}</p>
                      <p className="text-xs text-muted-foreground">{member.name}</p>
                    </div>
                    <Badge
                      variant={member.status === "On Duty" ? "default" : "secondary"}
                    >
                      {member.status}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Summary Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Day Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Work Hours</span>
                  <span className="font-medium">8h 30m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Rest Hours</span>
                  <span className="font-medium">8h 00m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Exercise</span>
                  <span className="font-medium">2h 00m</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-sm text-muted-foreground">Compliance</span>
                  <Badge variant="success">100%</Badge>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </PageWrapper>
  );
}
