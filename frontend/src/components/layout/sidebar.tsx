// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Calendar,
  FlaskConical,
  User,
  Info,
  Rocket,
  ChevronLeft,
  ChevronRight,
  Sun,
  Settings,
  Activity,
  GitCompare,
  Watch,
  Microscope,
  TrendingUp,
  Waves,
  Network,
  Zap,
  Layers,
  BarChart3,
  Target,
  Moon,
  Clock,
  Users,
  Download,
  Book,
  Heart,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppStore } from "@/lib/store";

// Operational navigation items
const operationalNav = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { id: "scheduling", label: "Crew Scheduling", icon: Calendar, href: "/scheduling" },
  { id: "experiments", label: "Experiments", icon: FlaskConical, href: "/experiments" },
  { id: "profile", label: "User Profile", icon: User, href: "/profile" },
];

// Research navigation items - Core
const researchNavCore = [
  { id: "research", label: "Research Hub", icon: Microscope, href: "/research" },
  { id: "space-weather", label: "Space Weather", icon: Sun, href: "/research/space-weather" },
  { id: "garmin", label: "Garmin Data", icon: Watch, href: "/research/garmin" },
];

// Research navigation items - HRV Analysis
const researchNavHRV = [
  { id: "hrv-analysis", label: "HRV Overview", icon: Activity, href: "/research/hrv-analysis" },
  { id: "time-series", label: "Time Series", icon: TrendingUp, href: "/research/time-series" },
  { id: "frequency", label: "Frequency Domain", icon: Waves, href: "/research/frequency" },
  { id: "nonlinear", label: "Nonlinear", icon: Network, href: "/research/nonlinear" },
  { id: "hrf", label: "HRF Analysis", icon: Zap, href: "/research/hrf" },
  { id: "windowed", label: "Windowed", icon: Layers, href: "/research/windowed" },
];

// Research navigation items - Clinical Tools
const researchNavClinical = [
  { id: "readiness", label: "Readiness", icon: Target, href: "/research/readiness" },
  { id: "ans-tests", label: "ANS Tests", icon: Heart, href: "/research/ans-tests" },
  { id: "fatigue", label: "Fatigue", icon: Moon, href: "/research/fatigue" },
  { id: "circadian", label: "Circadian", icon: Clock, href: "/research/circadian" },
  { id: "norms", label: "Population Norms", icon: Users, href: "/research/norms" },
];

// Research navigation items - Tools & Reference
const researchNavTools = [
  { id: "timeline", label: "Timeline", icon: TrendingUp, href: "/research/timeline" },
  { id: "correlations", label: "Correlations", icon: GitCompare, href: "/research/correlations" },
  { id: "export", label: "Export Center", icon: Download, href: "/research/export" },
  { id: "science", label: "References", icon: Book, href: "/research/science" },
];

// Combined for backward compatibility
const researchNav = [
  ...researchNavCore,
  ...researchNavHRV,
  ...researchNavClinical,
  ...researchNavTools,
];

// About/Info
const infoNav = [
  { id: "about", label: "About", icon: Info, href: "/about" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, setSidebarOpen, activeMission, setActiveMission } =
    useAppStore();

  return (
    <TooltipProvider>
      <motion.aside
        initial={false}
        animate={{ width: sidebarOpen ? 280 : 80 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="fixed left-0 top-0 z-40 flex h-screen flex-col border-r bg-card"
      >
        {/* Logo / Header */}
        <div className="flex h-16 items-center justify-between px-4">
          <motion.div
            initial={false}
            animate={{ opacity: sidebarOpen ? 1 : 0 }}
            className="flex items-center gap-2 overflow-hidden"
          >
            <Rocket className="h-8 w-8 text-primary" />
            <div className="flex flex-col">
              <span className="font-bold text-foreground">Mission Control</span>
              <span className="text-xs text-muted-foreground">
                Flight Surgeon
              </span>
            </div>
          </motion.div>
          {!sidebarOpen && (
            <Rocket className="h-8 w-8 text-primary mx-auto" />
          )}
        </div>

        <Separator />

        {/* Mission Selector */}
        <div className="p-4">
          {sidebarOpen ? (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Active Mission
              </label>
              <Select value={activeMission} onValueChange={setActiveMission}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select mission" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Mission 1">Mission 1</SelectItem>
                  <SelectItem value="Mission 2">Mission 2</SelectItem>
                </SelectContent>
              </Select>
            </div>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex justify-center">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-xs font-bold text-primary">
                      {activeMission.replace("Mission ", "M")}
                    </span>
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>{activeMission}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
          {/* Operational Section */}
          {sidebarOpen && (
            <p className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Operational
            </p>
          )}
          {operationalNav.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          {/* Research Section - Core */}
          <Separator className="my-2" />
          {sidebarOpen && (
            <p className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Research
            </p>
          )}
          {researchNavCore.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/research" && pathname.startsWith(item.href));
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          {/* Research Section - HRV Analysis */}
          {sidebarOpen && (
            <p className="px-3 py-1 mt-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              HRV Analysis
            </p>
          )}
          {researchNavHRV.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        sidebarOpen ? "pl-5" : "",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          {/* Research Section - Clinical Tools */}
          {sidebarOpen && (
            <p className="px-3 py-1 mt-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Clinical Tools
            </p>
          )}
          {researchNavClinical.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        sidebarOpen ? "pl-5" : "",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          {/* Research Section - Tools */}
          {sidebarOpen && (
            <p className="px-3 py-1 mt-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Tools
            </p>
          )}
          {researchNavTools.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        sidebarOpen ? "pl-5" : "",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}

          {/* Info Section */}
          <Separator className="my-2" />
          {infoNav.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link href={item.href}>
                    <motion.div
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className={cn(
                        "flex items-center gap-3 rounded-lg px-3 py-2 transition-colors",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                      )}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      {sidebarOpen && (
                        <motion.span
                          initial={false}
                          animate={{ opacity: sidebarOpen ? 1 : 0 }}
                          className="font-medium text-sm"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </motion.div>
                  </Link>
                </TooltipTrigger>
                {!sidebarOpen && (
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                )}
              </Tooltip>
            );
          })}
        </nav>

        <Separator />

        {/* Footer */}
        <div className="p-4 space-y-2">
          {sidebarOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-xs text-muted-foreground"
            >
              <p className="font-medium">Dr Diego Malpica MD</p>
              <p>Aerospace Medicine</p>
            </motion.div>
          )}

          {/* Collapse Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full justify-center"
          >
            {sidebarOpen ? (
              <>
                <ChevronLeft className="h-4 w-4 mr-2" />
                Collapse
              </>
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </Button>
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}
