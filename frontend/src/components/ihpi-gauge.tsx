// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

// ---------------------------------------------------------------------------
// SMS Risk Level to Color Mapping
// ---------------------------------------------------------------------------

const SMS_GAUGE_COLORS: Record<string, string> = {
  // EVA (ICAO)
  Acceptable: "text-green-500",
  Tolerable: "text-yellow-500",
  Undesirable: "text-orange-500",
  Intolerable: "text-red-500",
  // Flight (MIL-STD-882E)
  Low: "text-green-500",
  Medium: "text-yellow-500",
  Serious: "text-orange-500",
  High: "text-red-500",
  // Fallback
  default: "text-muted/30",
};

function getIHPIColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

function getIHPIStrokeColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  return "text-red-500";
}

// ---------------------------------------------------------------------------
// Exported Props
// ---------------------------------------------------------------------------

export interface IHPIGaugeProps {
  name: string;
  role: string;
  status: string;
  ihpiScore: number;
  fatigueLevel: number;
  sleepDebt: number;
  readinessScore: number;
  smsRiskLevel?: string;
  flightFatigueBand?: "low" | "moderate" | "high";
  flightFatigueModel?: string;
  onClick?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function IHPIGauge({
  name,
  role,
  status,
  ihpiScore,
  fatigueLevel,
  sleepDebt,
  readinessScore,
  smsRiskLevel,
  flightFatigueBand,
  flightFatigueModel,
  onClick,
}: IHPIGaugeProps) {
  const score = ihpiScore;
  const strokeColorClass = smsRiskLevel
    ? SMS_GAUGE_COLORS[smsRiskLevel] || SMS_GAUGE_COLORS.default
    : getIHPIStrokeColor(score);

  return (
    <motion.div
      className={`p-4 rounded-lg border bg-card transition-all ${
        onClick ? "cursor-pointer hover:bg-accent/50 hover:shadow-md" : ""
      }`}
      onClick={onClick}
      whileHover={onClick ? { scale: 1.02 } : undefined}
      whileTap={onClick ? { scale: 0.98 } : undefined}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="font-bold text-primary">{role}</span>
        </div>
        <div>
          <h4 className="font-medium text-sm">{name}</h4>
          <p className="text-xs text-muted-foreground capitalize">
            {status.replace("_", " ")}
          </p>
        </div>
        {onClick && (
          <ChevronRight className="h-4 w-4 ml-auto text-muted-foreground" />
        )}
      </div>

      {/* Circular Gauge with SMS-colored ring */}
      <div className="relative w-24 h-24 mx-auto">
        <svg className="w-full h-full transform -rotate-90">
          {/* Background ring — colored by SMS risk level */}
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className={smsRiskLevel ? `${strokeColorClass} opacity-20` : "text-muted/30"}
          />
          {/* Progress ring — colored by SMS risk level */}
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${(score / 100) * 251.2} 251.2`}
            className={strokeColorClass}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-2xl font-bold ${getIHPIColor(score)}`}>
            {score}
          </span>
        </div>
      </div>

      <div className="text-center mt-2">
        <p className="text-xs text-muted-foreground">IHPI Score</p>
        {smsRiskLevel && (
          <p className="text-xs font-medium mt-0.5" style={{
            color: smsRiskLevel === "Acceptable" || smsRiskLevel === "Low" ? "#16a34a"
              : smsRiskLevel === "Tolerable" || smsRiskLevel === "Medium" ? "#ca8a04"
              : smsRiskLevel === "Undesirable" || smsRiskLevel === "Serious" ? "#ea580c"
              : "#dc2626"
          }}>
            SMS: {smsRiskLevel}
          </p>
        )}
        <p
          className="text-[11px] font-medium mt-0.5"
          style={{
            color:
              flightFatigueBand === "low"
                ? "#16a34a"
                : flightFatigueBand === "moderate"
                  ? "#ca8a04"
                  : flightFatigueBand === "high"
                    ? "#dc2626"
                    : "#64748b",
          }}
        >
          Flight fatigue: {flightFatigueBand ? flightFatigueBand.toUpperCase() : "INSUFFICIENT DATA"}
        </p>
        {flightFatigueModel && (
          <p className="text-[10px] text-muted-foreground">{flightFatigueModel}</p>
        )}
        {onClick && (
          <p className="text-xs text-primary mt-1 font-medium">Click for details</p>
        )}
      </div>

      {/* Sub-metrics */}
      <div className="grid grid-cols-3 gap-1 mt-3 text-center">
        <div>
          <p className="text-xs text-muted-foreground">Fatigue</p>
          <p className="text-sm font-medium">{fatigueLevel}%</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Sleep</p>
          <p className="text-sm font-medium">{sleepDebt}h</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Ready</p>
          <p className="text-sm font-medium">{readinessScore}%</p>
        </div>
      </div>
    </motion.div>
  );
}
