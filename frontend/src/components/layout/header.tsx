// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Sun,
  Activity,
  Wifi,
  WifiOff,
  Settings,
  Bell,
  Rocket,
  Microscope,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAppStore } from "@/lib/store";
import { checkHealth } from "@/lib/api";
import { cn } from "@/lib/utils";
import { RRTracingLoader } from "@/components/research/rr-tracing-loader";

interface HeaderProps {
  title: string;
  description?: string;
}

export function Header({ title, description }: HeaderProps) {
  const { debugMode, setDebugMode, activeMission, appMode } = useAppStore();
  const [apiStatus, setApiStatus] = React.useState<"online" | "offline" | "checking">("checking");

  React.useEffect(() => {
    const checkAPI = async () => {
      try {
        await checkHealth();
        setApiStatus("online");
      } catch {
        setApiStatus("offline");
      }
    };

    checkAPI();
    const interval = setInterval(checkAPI, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const ModeIcon = appMode === "operational" ? Rocket : Microscope;
  const modeLabel = appMode === "operational" ? "Operational" : "Research";
  const modeColor = appMode === "operational" ? "text-primary" : "text-success";

  return (
    <TooltipProvider>
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6"
      >
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-xl font-semibold text-foreground">{title}</h1>
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {/* Mode Badge */}
          <Badge
            variant="outline"
            className={cn("hidden sm:flex items-center gap-1.5", modeColor)}
          >
            <ModeIcon className="h-3 w-3" />
            {modeLabel}
          </Badge>
          {/* Mission Badge - only in operational mode */}
          {appMode === "operational" && (
            <Badge variant="secondary" className="hidden md:flex">
              {activeMission}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {appMode === "research" && <RRTracingLoader />}

          {/* API Status */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted">
                {apiStatus === "online" ? (
                  <>
                    <Wifi className="h-4 w-4 text-success" />
                    <span className="text-xs font-medium text-success hidden sm:inline">
                      API Online
                    </span>
                  </>
                ) : apiStatus === "offline" ? (
                  <>
                    <WifiOff className="h-4 w-4 text-danger" />
                    <span className="text-xs font-medium text-danger hidden sm:inline">
                      API Offline
                    </span>
                  </>
                ) : (
                  <>
                    <Activity className="h-4 w-4 text-warning animate-pulse" />
                    <span className="text-xs font-medium text-warning hidden sm:inline">
                      Checking...
                    </span>
                  </>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>
                {apiStatus === "online"
                  ? "Connected to FastAPI backend"
                  : apiStatus === "offline"
                  ? "Cannot reach API server"
                  : "Checking connection..."}
              </p>
            </TooltipContent>
          </Tooltip>

          {/* Space Weather Indicator */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Sun className="h-5 w-5 text-warning" />
                <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-success" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Space Weather: Nominal</p>
            </TooltipContent>
          </Tooltip>

          {/* Notifications */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Notifications</p>
            </TooltipContent>
          </Tooltip>

          {/* Debug Mode Toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={debugMode ? "default" : "ghost"}
                size="icon"
                onClick={() => setDebugMode(!debugMode)}
              >
                <Settings className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Debug Mode: {debugMode ? "On" : "Off"}</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </motion.header>
    </TooltipProvider>
  );
}
