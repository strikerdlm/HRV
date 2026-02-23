// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { Rocket, Microscope } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore, type AppMode } from "@/lib/store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ModeSwitcherProps {
  collapsed?: boolean;
}

const modes: { id: AppMode; label: string; icon: React.ElementType; description: string; homePath: string }[] = [
  {
    id: "operational",
    label: "Operational",
    icon: Rocket,
    description: "Mission control, scheduling, crew management",
    homePath: "/",
  },
  {
    id: "research",
    label: "Research",
    icon: Microscope,
    description: "HRV analysis, space weather, correlations",
    homePath: "/research",
  },
];

export function ModeSwitcher({ collapsed = false }: ModeSwitcherProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { appMode, setAppMode } = useAppStore();

  // Handle mode change with navigation
  const handleModeChange = React.useCallback(
    (newMode: AppMode) => {
      if (newMode === appMode) return;
      
      setAppMode(newMode);
      
      // Navigate to the home page of the new mode if not already there
      const targetMode = modes.find((m) => m.id === newMode);
      if (targetMode) {
        if (newMode === "operational" && pathname.startsWith("/research")) {
          router.push(targetMode.homePath);
        } else if (newMode === "research" && !pathname.startsWith("/research")) {
          router.push(targetMode.homePath);
        }
      }
    },
    [appMode, pathname, router, setAppMode]
  );

  if (collapsed) {
    return (
      <div className="flex flex-col gap-1">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isActive = appMode === mode.id;

          return (
            <Tooltip key={mode.id}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => handleModeChange(mode.id)}
                  title={`Switch to ${mode.label} mode`}
                  aria-label={`Switch to ${mode.label} mode - ${mode.description}`}
                  className={cn(
                    "p-2 rounded-lg transition-all duration-200",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-5 w-5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">{mode.label}</p>
                <p className="text-xs text-muted-foreground">{mode.description}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Application Mode
      </label>
      <div className="relative grid grid-cols-2 rounded-lg bg-muted p-1">
        {/* Animated background indicator */}
        <div
          className="pointer-events-none absolute inset-y-1 left-1 w-[calc(50%-4px)] rounded-md bg-background shadow-sm transition-transform duration-200 ease-out"
          style={{
            transform: appMode === "operational" ? "translateX(0%)" : "translateX(100%)",
          }}
        />

        {modes.map((mode) => {
          const Icon = mode.icon;
          const isActive = appMode === mode.id;

          return (
            <button
              key={mode.id}
              onClick={() => handleModeChange(mode.id)}
              title={`Switch to ${mode.label} mode`}
              aria-label={`Switch to ${mode.label} mode - ${mode.description}`}
              className={cn(
                "relative flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors z-10",
                isActive
                  ? "text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{mode.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
