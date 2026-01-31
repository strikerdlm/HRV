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

// Research navigation items
const researchNav = [
  { id: "research", label: "Research Hub", icon: Microscope, href: "/research" },
  { id: "space-weather", label: "Space Weather", icon: Sun, href: "/research/space-weather" },
  { id: "hrv-analysis", label: "HRV Analysis", icon: Activity, href: "/research/hrv-analysis" },
  { id: "correlations", label: "Correlations", icon: GitCompare, href: "/research/correlations" },
  { id: "garmin", label: "Garmin Data", icon: Watch, href: "/research/garmin" },
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

          {/* Research Section */}
          <Separator className="my-2" />
          {sidebarOpen && (
            <p className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Research
            </p>
          )}
          {researchNav.map((item) => {
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
