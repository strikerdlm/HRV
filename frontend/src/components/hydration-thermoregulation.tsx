// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Droplets,
  Thermometer,
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Flame,
  Zap,
  Heart,
  BookOpen,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";

// ---------------------------------------------------------------------------
// Client-side hydration & thermoregulation calculators
// (Same formulas as Python backend hydration_thermoregulation.py)
// ---------------------------------------------------------------------------

const ACTIVITY_SR_BASE: Record<string, number> = {
  sedentary: 100,
  light: 300,
  moderate: 600,
  vigorous: 1000,
  hard: 1500,
  very_hard: 2000,
};

const ACTIVITY_MET_RATES: Record<string, number> = {
  sedentary: 58,
  light: 93,
  moderate: 175,
  vigorous: 290,
  hard: 400,
  very_hard: 520,
};

const ACTIVITY_LABELS: Record<string, string> = {
  sedentary: "Sedentary (resting)",
  light: "Light (walking)",
  moderate: "Moderate (brisk walk)",
  vigorous: "Vigorous (jogging)",
  hard: "Hard (running)",
  very_hard: "Very Hard (sprinting)",
};

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

function wbgtHeatFactor(wbgt: number): number {
  if (wbgt <= 22) return 1.0;
  const excess = wbgt - 22;
  return Math.min(1.0 + 0.045 * excess, 2.5);
}

function estimateSweatRate(
  activity: string,
  wbgt: number,
  bodyMass: number,
  acclimatized: boolean,
): number {
  const base = ACTIVITY_SR_BASE[activity] || 600;
  const massFactor = bodyMass / 70;
  const heatFactor = wbgtHeatFactor(wbgt);
  const acclimFactor = acclimatized ? 1.12 : 1.0;
  return clamp(base * massFactor * heatFactor * acclimFactor, 50, 3500);
}

function estimateDehydrationPct(
  sweatRateMlH: number,
  durationH: number,
  bodyMassKg: number,
  fluidIntakeMlH: number,
): number {
  const totalSweat = sweatRateMlH * durationH;
  const totalIntake = fluidIntakeMlH * durationH;
  const deficit = Math.max(0, totalSweat - totalIntake);
  return (deficit / (bodyMassKg * 1000)) * 100;
}

function estimateCoreTemp(
  activity: string,
  durationH: number,
  wbgt: number,
  dehydrationPct: number,
  baseline: number = 37.0,
): number {
  const metRate = ACTIVITY_MET_RATES[activity] || 175;
  const metNorm = clamp((metRate - 58) / (520 - 58), 0, 1);
  const maxRise = metNorm * 2.5;
  const k = 2.3;
  const exerciseRise = durationH > 0 ? maxRise * (1 - Math.exp(-k * durationH)) : 0;
  const wbgtExcess = Math.max(0, wbgt - 22);
  const heatRise = 0.03 * wbgtExcess * Math.min(durationH, 3) / 3;
  const dehyRise = 0.18 * dehydrationPct;
  return clamp(baseline + exerciseRise + heatRise + dehyRise, 35, 42);
}

function computePhSI(
  coreTemp: number,
  hr: number,
  baseTemp: number = 37.0,
  restHR: number = 70,
  maxHR: number = 190,
): number {
  const thermal = 5 * clamp(coreTemp - baseTemp, 0, 5) / (39.5 - baseTemp);
  const cardio = 5 * clamp(hr - restHR, 0, maxHR - restHR) / (maxHR - restHR);
  return clamp(thermal + cardio, 0, 10);
}

interface PerformanceResult {
  aerobic: number;
  cognitive: number;
  strength: number;
  overall: number;
  readinessModifier: number;
}

function computePerformance(dehyPct: number, heatStress: boolean): PerformanceResult {
  const d = clamp(dehyPct, 0, 15);
  const hm = heatStress ? 1.5 : 1.0;

  let aeroLoss: number;
  if (d <= 1) aeroLoss = 0;
  else if (d <= 2) aeroLoss = (d - 1) * 2 * hm;
  else aeroLoss = (2 + (d - 2) * 4.5) * hm;
  const aerobic = clamp(100 - aeroLoss, 40, 100);

  let cogLoss: number;
  if (d <= 1) cogLoss = d;
  else if (d <= 2) cogLoss = 1 + (d - 1) * 2.5;
  else cogLoss = 3.5 + (d - 2) * 4;
  const cognitive = clamp(100 - cogLoss * hm, 45, 100);

  let strLoss: number;
  if (d <= 3) strLoss = d * 0.5;
  else strLoss = 1.5 + (d - 3) * 3;
  const strength = clamp(100 - strLoss * hm, 50, 100);

  const overall = 0.4 * aerobic + 0.35 * cognitive + 0.25 * strength;
  const deficit = 100 - overall;
  const mod = Math.max(-10, -Math.min(10, deficit * 0.2));

  return {
    aerobic: Math.round(aerobic * 10) / 10,
    cognitive: Math.round(cognitive * 10) / 10,
    strength: Math.round(strength * 10) / 10,
    overall: Math.round(overall * 10) / 10,
    readinessModifier: Math.round(mod * 10) / 10,
  };
}

function dehydrationCategory(pct: number): string {
  if (pct < 1) return "Euhydrated";
  if (pct < 2) return "Mild";
  if (pct < 3) return "Moderate";
  if (pct < 5) return "Significant";
  if (pct < 7) return "Severe";
  return "Dangerous";
}

function coreTempRisk(tc: number): string {
  if (tc < 38) return "Normal";
  if (tc < 39) return "Mild Hyperthermia";
  if (tc < 40) return "Moderate Hyperthermia";
  if (tc < 40.5) return "Severe Hyperthermia";
  return "Heat Stroke Risk";
}

function phsiCategory(v: number): string {
  if (v < 3) return "Low";
  if (v < 5) return "Low-Moderate";
  if (v < 7) return "Moderate";
  if (v < 9) return "High";
  return "Very High";
}

function riskColor(risk: string): string {
  const colors: Record<string, string> = {
    Low: "#27ae60",
    "Low-Moderate": "#2ecc71",
    Moderate: "#f39c12",
    High: "#e67e22",
    "Very High": "#e74c3c",
    Extreme: "#8e44ad",
    Normal: "#27ae60",
    Euhydrated: "#27ae60",
    Mild: "#f39c12",
    Significant: "#e67e22",
    Severe: "#e74c3c",
    Dangerous: "#8e44ad",
    "Mild Hyperthermia": "#f39c12",
    "Moderate Hyperthermia": "#e67e22",
    "Severe Hyperthermia": "#e74c3c",
    "Heat Stroke Risk": "#8e44ad",
  };
  return colors[risk] || "#27ae60";
}

// ---------------------------------------------------------------------------
// SVG Ring Gauge (matching SWRingGauge and IHPI style)
// ---------------------------------------------------------------------------

function HydrationRingGauge({
  value,
  max,
  unit,
  label,
  color,
  size = 96,
  invert = false,
}: {
  value: number;
  max: number;
  unit: string;
  label: string;
  color: string;
  size?: number;
  invert?: boolean;
}) {
  const r = size * 0.375;
  const circ = 2 * Math.PI * r;
  const absVal = Math.abs(value);
  const pct = clamp(invert ? (max - absVal) / max : absVal / max, 0, 1);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full transform -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="7"
            opacity="0.15"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeDasharray={`${pct * circ} ${circ}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold" style={{ color }}>
            {typeof value === "number" ? (value % 1 === 0 ? value : value.toFixed(1)) : value}
          </span>
          <span className="text-[8px] text-muted-foreground">{unit}</span>
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground mt-1 font-medium text-center leading-tight">
        {label}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Performance Bars
// ---------------------------------------------------------------------------

function PerformanceBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold" style={{ color }}>
          {value.toFixed(0)}%
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable Section
// ---------------------------------------------------------------------------

function ExpandSection({
  title,
  icon,
  defaultOpen,
  badge,
  badgeColor,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen: boolean;
  badge?: string;
  badgeColor?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-2 p-2.5 hover:bg-muted/50 transition-colors text-left"
        onClick={() => setOpen(!open)}
        type="button"
      >
        {icon}
        <span className="text-xs font-semibold flex-1">{title}</span>
        {badge && (
          <Badge
            style={{ backgroundColor: badgeColor || "#888", color: "#fff" }}
            className="text-[10px]"
          >
            {badge}
          </Badge>
        )}
        {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="p-3 pt-1 border-t">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component: HydrationThermoregulationPanel
// ---------------------------------------------------------------------------

export function HydrationThermoregulationPanel() {
  // Input state
  const [activity, setActivity] = React.useState("moderate");
  const [duration, setDuration] = React.useState("1.0");
  const [wbgt, setWbgt] = React.useState("28");
  const [bodyMass, setBodyMass] = React.useState("70");
  const [fluidIntake, setFluidIntake] = React.useState("200");
  const [heartRate, setHeartRate] = React.useState("120");
  const [restingHR, setRestingHR] = React.useState("70");
  const [age, setAge] = React.useState("35");

  // Parse inputs
  const durationH = parseFloat(duration) || 1;
  const wbgtC = parseFloat(wbgt) || 22;
  const massKg = parseFloat(bodyMass) || 70;
  const intakeMlH = parseFloat(fluidIntake) || 0;
  const hr = parseFloat(heartRate) || 120;
  const rhr = parseFloat(restingHR) || 70;
  const ageYears = parseInt(age, 10) || 35;
  const maxHR = Math.max(180, 220 - ageYears);

  // Calculations
  const sweatRate = estimateSweatRate(activity, wbgtC, massKg, true);
  const dehyPct = estimateDehydrationPct(sweatRate, durationH, massKg, intakeMlH);
  const coreTemp = estimateCoreTemp(activity, durationH, wbgtC, dehyPct);
  const phsi = computePhSI(coreTemp, hr, 37.0, rhr, maxHR);
  const perf = computePerformance(dehyPct, wbgtC >= 28);

  const fluidRecMlH = Math.min(Math.round(sweatRate * 0.8), 1200);
  const totalSweatLoss = Math.round(sweatRate * durationH);

  const dehyCat = dehydrationCategory(dehyPct);
  const tcRisk = coreTempRisk(coreTemp);
  const phsiCat = phsiCategory(phsi);

  // Determine overall heat stress color
  const overallColor =
    dehyPct >= 5 || coreTemp >= 40 || phsi >= 9
      ? "#e74c3c"
      : dehyPct >= 3 || coreTemp >= 39 || phsi >= 7
        ? "#e67e22"
        : dehyPct >= 2 || coreTemp >= 38 || phsi >= 5
          ? "#f39c12"
          : "#27ae60";

  const perfColor = (v: number) =>
    v >= 90 ? "#27ae60" : v >= 75 ? "#f39c12" : v >= 60 ? "#e67e22" : "#e74c3c";

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Droplets className="h-5 w-5 text-blue-500" />
            Hydration & Thermoregulation
          </CardTitle>
          <Badge
            style={{ backgroundColor: overallColor, color: "#fff" }}
            className="text-xs"
          >
            {dehyPct < 2 && coreTemp < 38 ? "Nominal" : dehyPct < 3 ? "Caution" : "Alert"}
          </Badge>
        </div>
        <CardDescription>
          Sweat rate, dehydration, core temp & performance (Sawka et al. 2007; Cheuvront & Kenefick 2014)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Inputs */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-[10px]">Activity</Label>
            <Select value={activity} onValueChange={setActivity}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(ACTIVITY_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key} className="text-xs">
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-[10px]">WBGT (C)</Label>
            <Input
              type="number"
              value={wbgt}
              onChange={(e) => setWbgt(e.target.value)}
              className="h-8 text-sm"
              min={0}
              max={50}
            />
          </div>
          <div>
            <Label className="text-[10px]">Duration (h)</Label>
            <Input
              type="number"
              value={duration}
              onChange={(e) => setDuration(e.target.value)}
              className="h-8 text-sm"
              min={0}
              max={24}
              step={0.5}
            />
          </div>
          <div>
            <Label className="text-[10px]">Body Mass (kg)</Label>
            <Input
              type="number"
              value={bodyMass}
              onChange={(e) => setBodyMass(e.target.value)}
              className="h-8 text-sm"
              min={30}
              max={200}
            />
          </div>
          <div>
            <Label className="text-[10px]">Fluid Intake (mL/h)</Label>
            <Input
              type="number"
              value={fluidIntake}
              onChange={(e) => setFluidIntake(e.target.value)}
              className="h-8 text-sm"
              min={0}
              max={2000}
            />
          </div>
          <div>
            <Label className="text-[10px]">Heart Rate (bpm)</Label>
            <Input
              type="number"
              value={heartRate}
              onChange={(e) => setHeartRate(e.target.value)}
              className="h-8 text-sm"
              min={40}
              max={220}
            />
          </div>
        </div>

        {/* Main Gauges */}
        <div className="grid grid-cols-3 gap-1 py-2">
          <HydrationRingGauge
            value={Math.round(sweatRate)}
            max={3000}
            unit="mL/h"
            label="Sweat Rate"
            color={sweatRate > 1500 ? "#e74c3c" : sweatRate > 800 ? "#f39c12" : "#27ae60"}
          />
          <HydrationRingGauge
            value={Math.round(dehyPct * 10) / 10}
            max={8}
            unit="% BM"
            label="Dehydration"
            color={riskColor(dehyCat)}
          />
          <HydrationRingGauge
            value={Math.round(coreTemp * 10) / 10}
            max={41}
            unit="C"
            label="Core Temp"
            color={riskColor(tcRisk)}
          />
        </div>

        <div className="grid grid-cols-3 gap-1">
          <HydrationRingGauge
            value={Math.round(phsi * 10) / 10}
            max={10}
            unit=""
            label="PhSI"
            color={riskColor(phsiCat)}
          />
          <HydrationRingGauge
            value={Math.round(perf.overall)}
            max={100}
            unit="%"
            label="Performance"
            color={perfColor(perf.overall)}
          />
          <HydrationRingGauge
            value={fluidRecMlH}
            max={1500}
            unit="mL/h"
            label="Fluid Target"
            color="#3498db"
          />
        </div>

        {/* Expandable Sections */}
        <ExpandSection
          title="Dehydration & Water Loss"
          icon={<Droplets className="h-3.5 w-3.5 text-blue-500" />}
          defaultOpen={dehyPct >= 2}
          badge={dehyCat}
          badgeColor={riskColor(dehyCat)}
        >
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Sweat Loss</span>
              <span className="font-semibold">{totalSweatLoss} mL ({(totalSweatLoss / 1000).toFixed(1)} L)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Fluid Intake</span>
              <span className="font-semibold">{Math.round(intakeMlH * durationH)} mL</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Net Deficit</span>
              <span className="font-bold" style={{ color: riskColor(dehyCat) }}>
                {Math.round(Math.max(0, totalSweatLoss - intakeMlH * durationH))} mL
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Body Mass Loss</span>
              <span className="font-bold" style={{ color: riskColor(dehyCat) }}>
                {dehyPct.toFixed(1)}%
              </span>
            </div>
            {dehyPct >= 2 && (
              <div className="flex items-start gap-1 mt-1 p-2 bg-orange-50 border border-orange-200 rounded">
                <AlertTriangle className="h-3 w-3 mt-0.5 text-orange-500 shrink-0" />
                <p className="text-[10px] text-orange-700">
                  ACSM recommends limiting body mass loss to &lt;2% during exercise.
                  Increase fluid intake to {fluidRecMlH} mL/h.
                </p>
              </div>
            )}
            <p className="text-[9px] text-muted-foreground">
              Sawka et al. (2007). <i>Med Sci Sports Exerc</i>, 39(2). DOI: 10.1249/mss.0b013e31802ca597
            </p>
          </div>
        </ExpandSection>

        <ExpandSection
          title="Core Temperature & Heat Strain"
          icon={<Thermometer className="h-3.5 w-3.5 text-orange-500" />}
          defaultOpen={coreTemp >= 38}
          badge={tcRisk}
          badgeColor={riskColor(tcRisk)}
        >
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Estimated Tc</span>
              <span className="font-bold" style={{ color: riskColor(tcRisk) }}>
                {coreTemp.toFixed(1)} C
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rise from Exercise</span>
              <span>{(coreTemp - 37 - 0.18 * dehyPct - 0.03 * Math.max(0, wbgtC - 22) * Math.min(durationH, 3) / 3).toFixed(2)} C</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rise from Heat Stress</span>
              <span>{(0.03 * Math.max(0, wbgtC - 22) * Math.min(durationH, 3) / 3).toFixed(2)} C</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Rise from Dehydration</span>
              <span>{(0.18 * dehyPct).toFixed(2)} C</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">PhSI Score</span>
              <span className="font-bold" style={{ color: riskColor(phsiCat) }}>
                {phsi.toFixed(1)}/10 ({phsiCat})
              </span>
            </div>
            {coreTemp >= 39 && (
              <div className="flex items-start gap-1 mt-1 p-2 bg-red-50 border border-red-200 rounded">
                <AlertTriangle className="h-3 w-3 mt-0.5 text-red-500 shrink-0" />
                <p className="text-[10px] text-red-700">
                  Core temperature &ge;39 C: apply active cooling, reduce intensity.
                </p>
              </div>
            )}
            <p className="text-[9px] text-muted-foreground">
              Gonzalez-Alonso et al. (1999). <i>J Appl Physiol</i>, 86(3). DOI: 10.1152/jappl.1999.86.3.1032;
              Moran et al. (1998). <i>Am J Physiol</i>, 275(1). DOI: 10.1152/ajpregu.1998.275.1.R129
            </p>
          </div>
        </ExpandSection>

        <ExpandSection
          title="Performance Impact"
          icon={<Activity className="h-3.5 w-3.5 text-primary" />}
          defaultOpen={perf.overall < 90}
          badge={`${perf.overall.toFixed(0)}%`}
          badgeColor={perfColor(perf.overall)}
        >
          <div className="space-y-2">
            <PerformanceBar
              label="Aerobic (endurance)"
              value={perf.aerobic}
              color={perfColor(perf.aerobic)}
            />
            <PerformanceBar
              label="Cognitive (attention)"
              value={perf.cognitive}
              color={perfColor(perf.cognitive)}
            />
            <PerformanceBar
              label="Strength / Power"
              value={perf.strength}
              color={perfColor(perf.strength)}
            />
            <div className="flex justify-between text-xs mt-2 pt-2 border-t">
              <span className="text-muted-foreground">Readiness Modifier</span>
              <span
                className="font-bold"
                style={{ color: perf.readinessModifier < -3 ? "#e74c3c" : perf.readinessModifier < -1 ? "#f39c12" : "#27ae60" }}
              >
                {perf.readinessModifier >= 0 ? "+" : ""}{perf.readinessModifier.toFixed(1)} pts
              </span>
            </div>
            <p className="text-[9px] text-muted-foreground">
              Cheuvront & Kenefick (2014). <i>Compr Physiol</i>, 4(1). DOI: 10.1002/cphy.c130017;
              Sawka et al. (2015). <i>Sports Med</i>, 45(S1). DOI: 10.1007/s40279-015-0395-7
            </p>
          </div>
        </ExpandSection>

        <ExpandSection
          title="Fluid Replacement Guidance"
          icon={<Zap className="h-3.5 w-3.5 text-yellow-500" />}
          defaultOpen={false}
        >
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Target Intake</span>
              <span className="font-bold text-blue-600">{fluidRecMlH} mL/h</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Current Intake</span>
              <span>{intakeMlH} mL/h</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Deficit Rate</span>
              <span
                className="font-semibold"
                style={{
                  color: intakeMlH >= fluidRecMlH ? "#27ae60" : "#e74c3c",
                }}
              >
                {intakeMlH >= fluidRecMlH
                  ? "Adequate"
                  : `-${Math.round(fluidRecMlH - intakeMlH)} mL/h`}
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              ACSM recommends replacing ~80% of sweat losses during exercise.
              Maximum gastric emptying rate ~1.0-1.2 L/h (Sawka et al., 2007).
              Add 0.5-0.7 g/L sodium for exercise &gt;60 min in heat.
            </p>
          </div>
        </ExpandSection>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Compact Dashboard Gauges (for embedding in Operational Dashboard)
// ---------------------------------------------------------------------------

export interface HydrationDashboardProps {
  activity?: string;
  durationH?: number;
  wbgtC?: number;
  bodyMassKg?: number;
  fluidIntakeMlH?: number;
  heartRateBpm?: number;
  restingHrBpm?: number;
  ageYears?: number;
}

export function HydrationDashboardGauges({
  activity = "moderate",
  durationH = 1.0,
  wbgtC = 28,
  bodyMassKg = 70,
  fluidIntakeMlH = 200,
  heartRateBpm = 120,
  restingHrBpm = 70,
  ageYears = 35,
}: HydrationDashboardProps) {
  const maxHR = Math.max(180, 220 - ageYears);
  const sr = estimateSweatRate(activity, wbgtC, bodyMassKg, true);
  const dehy = estimateDehydrationPct(sr, durationH, bodyMassKg, fluidIntakeMlH);
  const tc = estimateCoreTemp(activity, durationH, wbgtC, dehy);
  const phsi = computePhSI(tc, heartRateBpm, 37.0, restingHrBpm, maxHR);
  const perf = computePerformance(dehy, wbgtC >= 28);

  const dehyCat = dehydrationCategory(dehy);
  const tcRisk = coreTempRisk(tc);
  const phsiCat = phsiCategory(phsi);
  const perfClr = (v: number) =>
    v >= 90 ? "#27ae60" : v >= 75 ? "#f39c12" : v >= 60 ? "#e67e22" : "#e74c3c";

  return (
    <div className="grid grid-cols-3 gap-2">
      <HydrationRingGauge
        value={Math.round(dehy * 10) / 10}
        max={8}
        unit="% BM"
        label="Dehydration"
        color={riskColor(dehyCat)}
        size={80}
      />
      <HydrationRingGauge
        value={Math.round(tc * 10) / 10}
        max={41}
        unit="C"
        label="Core Temp"
        color={riskColor(tcRisk)}
        size={80}
      />
      <HydrationRingGauge
        value={Math.round(perf.overall)}
        max={100}
        unit="%"
        label="Hydration Perf"
        color={perfClr(perf.overall)}
        size={80}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Readiness Modifier Export
// ---------------------------------------------------------------------------

export function computeHydrationReadinessModifier(
  activity: string = "moderate",
  durationH: number = 1.0,
  wbgtC: number = 22,
  bodyMassKg: number = 70,
  fluidIntakeMlH: number = 200,
  heartRateBpm: number = 120,
  restingHrBpm: number = 70,
  ageYears: number = 35,
): { modifier: number; hydrationStatus: string; coreTemp: number; phsi: number } {
  const maxHR = Math.max(180, 220 - ageYears);
  const sr = estimateSweatRate(activity, wbgtC, bodyMassKg, true);
  const dehy = estimateDehydrationPct(sr, durationH, bodyMassKg, fluidIntakeMlH);
  const tc = estimateCoreTemp(activity, durationH, wbgtC, dehy);
  const phi = computePhSI(tc, heartRateBpm, 37.0, restingHrBpm, maxHR);
  const perf = computePerformance(dehy, wbgtC >= 28);

  let mod = perf.readinessModifier;
  if (phi >= 7) {
    mod = Math.max(-10, mod + -Math.min(3, (phi - 7) * 1.5));
  }

  return {
    modifier: Math.round(mod * 10) / 10,
    hydrationStatus: dehydrationCategory(dehy),
    coreTemp: Math.round(tc * 10) / 10,
    phsi: Math.round(phi * 10) / 10,
  };
}
