// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Stethoscope,
  Apple,
  Droplets,
  Mountain,
  Thermometer,
  Activity,
  Heart,
  Wind,
  ChevronDown,
  ChevronUp,
  Maximize2,
  Minimize2,
  X,
  AlertTriangle,
  BookOpen,
  Brain,
  Flame,
  Zap,
  Moon,
  Eye,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";

// ---------------------------------------------------------------------------
// Constants & Scientific Reference Data
// ---------------------------------------------------------------------------

/**
 * NASA-STD-3001 Vol. 2, Rev B (2019) and Lane & Schoeller (2000)
 * Baseline energy requirements for spaceflight and analog environments.
 * Smith & Zwart (2008) Nutritional Biochemistry of Spaceflight.
 */

/** Activity multiplier factors (NASA JSC-63555 / Harris-Benedict PAL) */
const ACTIVITY_FACTORS: Record<string, { label: string; factor: number }> = {
  sedentary: { label: "Sedentary (confined rest)", factor: 1.2 },
  light: { label: "Light (station maintenance)", factor: 1.375 },
  moderate: { label: "Moderate (EVA prep / field work)", factor: 1.55 },
  active: { label: "Active (EVA / traverse)", factor: 1.725 },
  very_active: { label: "Very Active (heavy EVA / expedition)", factor: 1.9 },
};

/** Cold exposure metabolic multipliers (Castellani & Young, 2007) */
const COLD_FACTORS: Record<string, { label: string; factor: number; tempRange: string }> = {
  thermoneutral: { label: "Thermoneutral (20-25 C)", factor: 1.0, tempRange: "20-25" },
  mild_cold: { label: "Mild Cold (5-20 C)", factor: 1.05, tempRange: "5-20" },
  moderate_cold: { label: "Moderate Cold (-10 to 5 C)", factor: 1.15, tempRange: "-10 to 5" },
  severe_cold: { label: "Severe Cold (-25 to -10 C)", factor: 1.25, tempRange: "-25 to -10" },
  extreme_cold: { label: "Extreme Cold (< -25 C)", factor: 1.40, tempRange: "< -25" },
};

/** Altitude factors for increased metabolic demand (Butterfield et al., 1992) */
const ALTITUDE_FACTORS: Record<string, { label: string; factor: number; altRange: string; spo2Est: string }> = {
  sea_level: { label: "Sea Level (0-500 m)", factor: 1.0, altRange: "0-500", spo2Est: "96-99%" },
  low: { label: "Low Altitude (500-1500 m)", factor: 1.02, altRange: "500-1500", spo2Est: "94-97%" },
  moderate: { label: "Moderate (1500-2500 m)", factor: 1.05, altRange: "1500-2500", spo2Est: "92-95%" },
  high: { label: "High (2500-3500 m)", factor: 1.10, altRange: "2500-3500", spo2Est: "88-92%" },
  very_high: { label: "Very High (3500-5500 m)", factor: 1.18, altRange: "3500-5500", spo2Est: "80-88%" },
  extreme: { label: "Extreme (>5500 m)", factor: 1.30, altRange: ">5500", spo2Est: "65-80%" },
};

/**
 * NASA-STD-3001 Vol. 2 macronutrient ranges (% of TEE):
 * Protein: 12-15%, Carbohydrate: 50-55%, Fat: 25-35%
 * Smith et al. (2005) J Nutr, 135(3), 437-443.
 */
const MACRO_TARGETS = {
  protein: { min: 0.12, max: 0.15, kcalPerG: 4, label: "Protein" },
  carbohydrate: { min: 0.50, max: 0.55, kcalPerG: 4, label: "Carbohydrate" },
  fat: { min: 0.25, max: 0.35, kcalPerG: 9, label: "Fat" },
};

/**
 * NASA-STD-3001 micronutrient requirements (daily) adapted from
 * Smith & Zwart (2008) and Lane et al. (2013).
 */
const MICRONUTRIENT_TARGETS = [
  { name: "Vitamin D", amount: "1000 IU", note: "Critical in polar/confined environments" },
  { name: "Calcium", amount: "1000-1200 mg", note: "Bone loss prevention (Smith et al., 2012)" },
  { name: "Iron", amount: "8-10 mg", note: "Reduced at altitude; monitor ferritin" },
  { name: "Vitamin C", amount: "90-100 mg", note: "Antioxidant, immune support" },
  { name: "Vitamin B12", amount: "2.4 mcg", note: "Neurological function" },
  { name: "Folate", amount: "400 mcg", note: "DNA synthesis, RBC production" },
  { name: "Potassium", amount: "3500 mg", note: "Electrolyte balance (increased in cold)" },
  { name: "Sodium", amount: "1500-2300 mg", note: "Sweat losses; adjust for activity" },
  { name: "Omega-3 FA", amount: "1-2 g", note: "Anti-inflammatory (Zwart et al., 2010)" },
  { name: "Magnesium", amount: "320-420 mg", note: "Muscle/nerve function" },
];

/**
 * Water requirements notes (used in computeWaterRequirement):
 *   Baseline: ~33 mL/kg/day (~2.3 L for 70 kg, NASA-STD-3001)
 *   Altitude: +0.5-1.0 L above 2500m (Butterfield, 1999)
 *   Cold: +0.2-0.8 L (Freund & Sawka, 1996)
 *   Activity: +0.4-1.4 L per hour of exercise (Sawka et al., 2007)
 */

// ---------------------------------------------------------------------------
// Helper: clamp
// ---------------------------------------------------------------------------

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

// ---------------------------------------------------------------------------
// Calculation Functions
// ---------------------------------------------------------------------------

/**
 * Mifflin-St Jeor BMR (more accurate than Harris-Benedict per
 * Frankenfield et al., 2005 JADA review):
 *   Male:   10*W + 6.25*H - 5*A + 5
 *   Female: 10*W + 6.25*H - 5*A - 161
 * Where W=kg, H=cm, A=years
 */
function computeBMR(
  weightKg: number,
  heightCm: number,
  ageYears: number,
  sex: "male" | "female",
): number {
  const base = 10 * weightKg + 6.25 * heightCm - 5 * ageYears;
  return sex === "male" ? base + 5 : base - 161;
}

/**
 * Total Energy Expenditure with environmental adjustments.
 * TEE = BMR * PAL * ColdFactor * AltitudeFactor
 * References: Lane & Schoeller (2000), Castellani & Young (2007),
 * Butterfield et al. (1992).
 */
function computeTEE(
  bmr: number,
  activityFactor: number,
  coldFactor: number,
  altitudeFactor: number,
): number {
  return bmr * activityFactor * coldFactor * altitudeFactor;
}

/**
 * Macronutrient breakdown from TEE (NASA-STD-3001 Vol. 2 ranges).
 */
function computeMacros(tee: number): {
  proteinG: number;
  carbG: number;
  fatG: number;
  proteinKcal: number;
  carbKcal: number;
  fatKcal: number;
} {
  const proteinKcal = tee * (MACRO_TARGETS.protein.min + MACRO_TARGETS.protein.max) / 2;
  const carbKcal = tee * (MACRO_TARGETS.carbohydrate.min + MACRO_TARGETS.carbohydrate.max) / 2;
  const fatKcal = tee * (MACRO_TARGETS.fat.min + MACRO_TARGETS.fat.max) / 2;
  return {
    proteinG: Math.round(proteinKcal / 4),
    carbG: Math.round(carbKcal / 4),
    fatG: Math.round(fatKcal / 9),
    proteinKcal: Math.round(proteinKcal),
    carbKcal: Math.round(carbKcal),
    fatKcal: Math.round(fatKcal),
  };
}

/**
 * Daily water requirement computation.
 * Base: ~30-35 mL/kg/day (IOM 2004, adapted for analog missions).
 * Activity: +500-1500 mL/h of exercise (Sawka et al., 2007).
 * Altitude: +500 mL above 2500m, +1000 mL above 4000m (Butterfield, 1999).
 * Cold: +500 mL due to respiratory and cold-induced diuresis (Freund & Sawka, 1996).
 * Heat: Handled by sweat rate (see hydration-thermoregulation component).
 */
function computeWaterRequirement(
  weightKg: number,
  activityKey: string,
  altitudeKey: string,
  coldKey: string,
  exerciseHours: number,
): {
  baseMl: number;
  activityMl: number;
  altitudeMl: number;
  coldMl: number;
  totalMl: number;
} {
  const baseMl = Math.round(weightKg * 33); // ~33 mL/kg/day

  // Activity-related water increase
  const activityWaterRates: Record<string, number> = {
    sedentary: 0,
    light: 400,
    moderate: 700,
    active: 1000,
    very_active: 1400,
  };
  const activityMl = Math.round((activityWaterRates[activityKey] ?? 500) * exerciseHours);

  // Altitude water increase
  const altWaterMap: Record<string, number> = {
    sea_level: 0,
    low: 0,
    moderate: 250,
    high: 500,
    very_high: 750,
    extreme: 1000,
  };
  const altitudeMl = altWaterMap[altitudeKey] ?? 0;

  // Cold exposure water increase (respiratory losses + cold-induced diuresis)
  const coldWaterMap: Record<string, number> = {
    thermoneutral: 0,
    mild_cold: 200,
    moderate_cold: 400,
    severe_cold: 600,
    extreme_cold: 800,
  };
  const coldMl = coldWaterMap[coldKey] ?? 0;

  const totalMl = baseMl + activityMl + altitudeMl + coldMl;

  return { baseMl, activityMl, altitudeMl, coldMl, totalMl };
}

/**
 * Altitude-SpO2 estimation using a continuous piecewise model.
 * Based on Severinghaus (1979) oxygen dissociation curve and
 * West (2004) altitude physiology data.
 *
 * Boundary-continuous segments:
 *   0-1500m:    98.0 -> 96.5% (slope -0.001/m)
 *   1500-3500m: 96.5 -> 90.5% (slope -0.003/m)
 *   3500-5500m: 90.5 -> 80.5% (slope -0.005/m)
 *   >5500m:     80.5 -> ... (slope -0.008/m)
 */
function estimateSpO2(altitudeM: number): number {
  // Segment 1: 0-1500m => 98.0 down to 96.5
  if (altitudeM <= 1500) return clamp(98 - altitudeM * 0.001, 90, 99);
  // Segment 2: 1500-3500m => 96.5 down to 90.5
  if (altitudeM <= 3500) return clamp(96.5 - (altitudeM - 1500) * 0.003, 80, 97);
  // Segment 3: 3500-5500m => 90.5 down to 80.5
  if (altitudeM <= 5500) return clamp(90.5 - (altitudeM - 3500) * 0.005, 70, 91);
  // Segment 4: >5500m => 80.5 downward
  return clamp(80.5 - (altitudeM - 5500) * 0.008, 55, 81);
}

/**
 * Estimated resting HR increase with altitude.
 * ~10% increase per 1000m above 2500m (Bartsch & Saltin, 2008).
 */
function estimateAltitudeHR(baseHR: number, altitudeM: number): number {
  if (altitudeM <= 2500) return baseHR;
  const excessKm = (altitudeM - 2500) / 1000;
  return Math.round(baseHR * (1 + 0.10 * excessKm));
}

// ---------------------------------------------------------------------------
// SVG Ring Gauge (matching existing project style)
// ---------------------------------------------------------------------------

function ConsoleRingGauge({
  value,
  max,
  unit,
  label,
  color,
  size = 88,
}: {
  value: number;
  max: number;
  unit: string;
  label: string;
  color: string;
  size?: number;
}) {
  const r = size * 0.375;
  const circ = 2 * Math.PI * r;
  const pct = clamp(Math.abs(value) / max, 0, 1);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          className="w-full h-full transform -rotate-90"
          viewBox={`0 0 ${size} ${size}`}
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            opacity="0.15"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${pct * circ} ${circ}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold" style={{ color }}>
            {typeof value === "number"
              ? value % 1 === 0
                ? value
                : value.toFixed(1)
              : value}
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
// Expandable Section (consistent with project pattern)
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
            style={{ backgroundColor: badgeColor ?? "#888", color: "#fff" }}
            className="text-[10px]"
          >
            {badge}
          </Badge>
        )}
        {open ? (
          <ChevronUp className="h-3.5 w-3.5" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" />
        )}
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
// Floating Plot Pane (expandable to full screen)
// ---------------------------------------------------------------------------

function FloatingPlotPane({
  title,
  children,
  isOpen,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [isFullScreen, setIsFullScreen] = React.useState(false);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="floating-pane"
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
          className={
            isFullScreen
              ? "fixed inset-0 z-50 bg-background"
              : "fixed bottom-4 right-4 z-50 w-[700px] max-w-[90vw] max-h-[80vh] bg-background border border-border rounded-xl shadow-2xl"
          }
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30 rounded-t-xl">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold">{title}</h3>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setIsFullScreen(!isFullScreen)}
              >
                {isFullScreen ? (
                  <Minimize2 className="h-3.5 w-3.5" />
                ) : (
                  <Maximize2 className="h-3.5 w-3.5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={onClose}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          {/* Content */}
          <div
            className={
              isFullScreen
                ? "p-6 overflow-y-auto"
                : "p-4 overflow-y-auto max-h-[calc(80vh-48px)]"
            }
            style={isFullScreen ? { height: "calc(100vh - 48px)" } : undefined}
          >
            {children}
          </div>
        </motion.div>
      )}
      {/* Backdrop for fullscreen */}
      {isOpen && isFullScreen && (
        <motion.div
          key="backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 bg-black/50"
          onClick={() => setIsFullScreen(false)}
        />
      )}
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------------------
// ECharts: Energy Balance Breakdown Chart
// ---------------------------------------------------------------------------

function EnergyBreakdownChart({
  bmr,
  tee,
  activityLabel,
  coldLabel,
  altLabel,
}: {
  bmr: number;
  tee: number;
  activityLabel: string;
  coldLabel: string;
  altLabel: string;
}) {
  const totalAdded = Math.round(tee - bmr);
  // Split the non-BMR cost proportionally across activity, cold, altitude
  // for a more informative breakdown
  const activityPortion = Math.round(totalAdded * 0.65);
  const coldPortion = Math.round(totalAdded * 0.20);
  const altPortion = Math.max(0, totalAdded - activityPortion - coldPortion);

  const option = React.useMemo(
    () => ({
      title: {
        text: "Energy Expenditure Breakdown",
        left: "center" as const,
        textStyle: { color: "#1a1a1a", fontWeight: "bold" as const, fontSize: 14 },
      },
      tooltip: {
        trigger: "item" as const,
        formatter: "{b}: {c} kcal ({d}%)",
      },
      legend: {
        bottom: 5,
        textStyle: { color: "#1a1a1a", fontSize: 11 },
      },
      series: [
        {
          type: "pie" as const,
          radius: ["35%", "65%"],
          center: ["50%", "45%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: "#fff",
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: "{b}\n{c} kcal",
            color: "#1a1a1a",
            fontSize: 11,
          },
          data: [
            {
              value: Math.round(bmr),
              name: "Basal Metabolism",
              itemStyle: { color: "#3498db" },
            },
            {
              value: activityPortion > 0 ? activityPortion : 0,
              name: `Activity (${activityLabel})`,
              itemStyle: { color: "#27ae60" },
            },
            {
              value: coldPortion > 0 ? coldPortion : 0,
              name: `Cold (${coldLabel})`,
              itemStyle: { color: "#1abc9c" },
            },
            {
              value: altPortion > 0 ? altPortion : 0,
              name: `Altitude (${altLabel})`,
              itemStyle: { color: "#9b59b6" },
            },
          ],
        },
      ],
    }),
    [bmr, activityPortion, coldPortion, altPortion, activityLabel, coldLabel, altLabel],
  );

  return <EChartsWrapper option={option} height={320} showToolbox />;
}

// ---------------------------------------------------------------------------
// ECharts: Macronutrient Radar Chart
// ---------------------------------------------------------------------------

function MacroRadarChart({
  proteinG,
  carbG,
  fatG,
  tee,
}: {
  proteinG: number;
  carbG: number;
  fatG: number;
  tee: number;
}) {
  const option: any = React.useMemo(
    () => ({
      title: {
        text: "Macronutrient Profile",
        left: "center" as const,
        textStyle: { color: "#1a1a1a", fontWeight: "bold" as const, fontSize: 14 },
      },
      tooltip: { trigger: "item" },
      radar: {
        indicator: [
          { name: `Protein\n${proteinG}g`, max: Math.max(proteinG * 1.5, 200) },
          { name: `Carbs\n${carbG}g`, max: Math.max(carbG * 1.5, 500) },
          { name: `Fat\n${fatG}g`, max: Math.max(fatG * 1.5, 150) },
          { name: `Fiber\n30-38g`, max: 60 },
          { name: `Water\nSee Calc`, max: 100 },
        ],
        radius: "60%",
        name: { textStyle: { color: "#1a1a1a", fontSize: 10 } },
        splitArea: {
          areaStyle: {
            color: [
              "rgba(39,174,96,0.05)",
              "rgba(52,152,219,0.08)",
              "rgba(243,156,18,0.05)",
              "rgba(231,76,60,0.05)",
            ],
          },
        },
      },
      series: [
        {
          type: "radar" as const,
          data: [
            {
              value: [proteinG, carbG, fatG, 34, 80],
              name: "Current Target",
              lineStyle: { width: 2, color: "#3498db" },
              areaStyle: { opacity: 0.2, color: "#3498db" },
              itemStyle: { color: "#3498db" },
            },
            {
              value: [
                Math.round(tee * 0.15 / 4),
                Math.round(tee * 0.55 / 4),
                Math.round(tee * 0.35 / 9),
                38,
                100,
              ],
              name: "NASA Max Range",
              lineStyle: { width: 1, type: "dashed", color: "#e74c3c" },
              areaStyle: { opacity: 0.05, color: "#e74c3c" },
              itemStyle: { color: "#e74c3c" },
            },
          ],
        },
      ],
      legend: {
        bottom: 0,
        textStyle: { color: "#1a1a1a", fontSize: 10 },
      },
    }),
    [proteinG, carbG, fatG, tee],
  );

  return <EChartsWrapper option={option} height={340} showToolbox />;
}

// ---------------------------------------------------------------------------
// ECharts: Water Requirements Stacked Bar
// ---------------------------------------------------------------------------

function WaterRequirementChart({
  baseMl,
  activityMl,
  altitudeMl,
  coldMl,
  totalMl,
}: {
  baseMl: number;
  activityMl: number;
  altitudeMl: number;
  coldMl: number;
  totalMl: number;
}) {
  const option: any = React.useMemo(
    () => ({
      title: {
        text: "Daily Water Requirement Breakdown",
        left: "center" as const,
        textStyle: { color: "#1a1a1a", fontWeight: "bold" as const, fontSize: 14 },
      },
      tooltip: {
        trigger: "axis" as const,
        axisPointer: { type: "shadow" as const },
        formatter: (params: Array<{ seriesName: string; value: number; color: string }>) => {
          let html = "<b>Water Requirements</b><br/>";
          let total = 0;
          for (const p of params) {
            html += `<span style="color:${p.color}">\u25CF</span> ${p.seriesName}: ${p.value} mL<br/>`;
            total += p.value;
          }
          html += `<b>Total: ${total} mL (${(total / 1000).toFixed(1)} L)</b>`;
          return html;
        },
      },
      legend: {
        bottom: 5,
        textStyle: { color: "#1a1a1a", fontSize: 10 },
      },
      grid: {
        left: 60,
        right: 30,
        top: 50,
        bottom: 60,
        containLabel: true,
      },
      xAxis: {
        type: "category" as const,
        data: ["Daily Target"],
        axisLabel: { color: "#1a1a1a", fontSize: 12, fontWeight: "bold" as const },
      },
      yAxis: {
        type: "value" as const,
        name: "mL",
        nameTextStyle: { color: "#1a1a1a" },
        axisLabel: { color: "#1a1a1a" },
      },
      series: [
        {
          name: "Baseline (33 mL/kg)",
          type: "bar" as const,
          stack: "water",
          data: [baseMl],
          itemStyle: { color: "#3498db", borderRadius: [0, 0, 4, 4] },
          barWidth: 80,
        },
        {
          name: "Activity",
          type: "bar" as const,
          stack: "water",
          data: [activityMl],
          itemStyle: { color: "#27ae60" },
          barWidth: 80,
        },
        {
          name: "Altitude",
          type: "bar" as const,
          stack: "water",
          data: [altitudeMl],
          itemStyle: { color: "#9b59b6" },
          barWidth: 80,
        },
        {
          name: "Cold Exposure",
          type: "bar" as const,
          stack: "water",
          data: [coldMl],
          itemStyle: { color: "#1abc9c", borderRadius: [4, 4, 0, 0] },
          barWidth: 80,
        },
      ],
      graphic: [
        {
          type: "text" as const,
          left: "center" as const,
          top: 35,
          style: {
            text: `Total: ${(totalMl / 1000).toFixed(1)} L/day`,
            fill: "#1a1a1a",
            fontSize: 12,
            fontWeight: "bold" as const,
          },
        },
      ],
    }),
    [baseMl, activityMl, altitudeMl, coldMl, totalMl],
  );

  return <EChartsWrapper option={option} height={320} showToolbox />;
}

// ---------------------------------------------------------------------------
// ECharts: Altitude-SpO2-HR Physiology Plot
// ---------------------------------------------------------------------------

function AltitudePhysiologyChart({ restingHR }: { restingHR: number }) {
  const option: any = React.useMemo(() => {
    const altitudes = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000];
    const spo2Values = altitudes.map((a) => estimateSpO2(a));
    const hrValues = altitudes.map((a) => estimateAltitudeHR(restingHR, a));

    return {
      title: {
        text: "Altitude Physiology",
        left: "center" as const,
        textStyle: { color: "#1a1a1a", fontWeight: "bold" as const, fontSize: 14 },
      },
      tooltip: {
        trigger: "axis" as const,
        formatter: (params: Array<{ seriesName: string; value: number; axisValue: string }>) => {
          let html = `<b>Altitude: ${params[0].axisValue}m</b><br/>`;
          for (const p of params) {
            const unit = p.seriesName === "SpO2" ? "%" : " bpm";
            html += `${p.seriesName}: <b>${typeof p.value === "number" ? p.value.toFixed(1) : p.value}${unit}</b><br/>`;
          }
          return html;
        },
      },
      legend: {
        bottom: 5,
        textStyle: { color: "#1a1a1a", fontSize: 10 },
      },
      grid: {
        left: 60,
        right: 60,
        top: 50,
        bottom: 60,
        containLabel: true,
      },
      xAxis: {
        type: "category" as const,
        data: altitudes.map(String),
        name: "Altitude (m)",
        nameLocation: "center" as const,
        nameGap: 30,
        nameTextStyle: { color: "#1a1a1a", fontSize: 11 },
        axisLabel: { color: "#1a1a1a", fontSize: 10, interval: 1 },
      },
      yAxis: [
        {
          type: "value" as const,
          name: "SpO2 (%)",
          nameTextStyle: { color: "#e74c3c" },
          min: 60,
          max: 100,
          axisLabel: { color: "#1a1a1a" },
          axisLine: { lineStyle: { color: "#e74c3c" } },
        },
        {
          type: "value" as const,
          name: "HR (bpm)",
          nameTextStyle: { color: "#3498db" },
          axisLabel: { color: "#1a1a1a" },
          axisLine: { lineStyle: { color: "#3498db" } },
        },
      ],
      series: [
        {
          name: "SpO2",
          type: "line" as const,
          yAxisIndex: 0,
          data: spo2Values,
          smooth: true,
          lineStyle: { width: 3, color: "#e74c3c" },
          itemStyle: { color: "#e74c3c" },
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(231,76,60,0.3)" },
                { offset: 1, color: "rgba(231,76,60,0.02)" },
              ],
            },
          },
          markLine: {
            silent: true,
            data: [
              {
                yAxis: 90,
                label: { formatter: "Hypoxemia <90%", color: "#e74c3c", fontSize: 10 },
                lineStyle: { type: "dashed" as const, color: "#e74c3c" },
              },
            ],
          },
        },
        {
          name: "Resting HR",
          type: "line" as const,
          yAxisIndex: 1,
          data: hrValues,
          smooth: true,
          lineStyle: { width: 3, color: "#3498db" },
          itemStyle: { color: "#3498db" },
          areaStyle: {
            color: {
              type: "linear" as const,
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: "rgba(52,152,219,0.2)" },
                { offset: 1, color: "rgba(52,152,219,0.02)" },
              ],
            },
          },
        },
      ],
    };
  }, [restingHR]);

  return <EChartsWrapper option={option} height={360} showToolbox />;
}

// ---------------------------------------------------------------------------
// ECharts: Environmental Stress Heatmap
// ---------------------------------------------------------------------------

function EnvironmentalStressChart() {
  const option: any = React.useMemo(() => {
    const stressors = ["Cold", "Altitude", "Isolation", "Radiation", "Workload", "Sleep Disruption"];
    const phases = ["Pre-Mission", "Early (Wk 1-2)", "Mid (Wk 3-6)", "Late (Wk 7+)", "Post"];
    const data: Array<[number, number, number]> = [
      // [phase_idx, stressor_idx, severity 0-10]
      [0, 0, 2], [0, 1, 3], [0, 2, 1], [0, 3, 2], [0, 4, 5], [0, 5, 3],
      [1, 0, 7], [1, 1, 6], [1, 2, 5], [1, 3, 4], [1, 4, 7], [1, 5, 6],
      [2, 0, 6], [2, 1, 5], [2, 2, 8], [2, 3, 5], [2, 4, 6], [2, 5, 7],
      [3, 0, 5], [3, 1, 4], [3, 2, 9], [3, 3, 5], [3, 4, 5], [3, 5, 8],
      [4, 0, 1], [4, 1, 1], [4, 2, 3], [4, 3, 2], [4, 4, 3], [4, 5, 4],
    ];

    return {
      title: {
        text: "Analog Mission Stress Profile",
        left: "center" as const,
        textStyle: { color: "#1a1a1a", fontWeight: "bold" as const, fontSize: 14 },
      },
      tooltip: {
        position: "top" as const,
        formatter: (params: { value: [number, number, number] }) => {
          const [pIdx, sIdx, val] = params.value;
          return `<b>${phases[pIdx]}</b><br/>${stressors[sIdx]}: <b>${val}/10</b>`;
        },
      },
      grid: {
        left: 100,
        right: 60,
        top: 50,
        bottom: 60,
        containLabel: true,
      },
      xAxis: {
        type: "category" as const,
        data: phases,
        axisLabel: { color: "#1a1a1a", fontSize: 10 },
        splitArea: { show: true },
      },
      yAxis: {
        type: "category" as const,
        data: stressors,
        axisLabel: { color: "#1a1a1a", fontSize: 10 },
        splitArea: { show: true },
      },
      visualMap: {
        min: 0,
        max: 10,
        calculable: true,
        orient: "horizontal" as const,
        left: "center" as const,
        bottom: 5,
        textStyle: { color: "#1a1a1a" },
        inRange: {
          color: ["#ecf0f1", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"],
        },
      },
      series: [
        {
          type: "heatmap" as const,
          data,
          label: {
            show: true,
            color: "#1a1a1a",
            fontSize: 11,
            fontWeight: "bold" as const,
          },
          itemStyle: {
            borderColor: "#fff",
            borderWidth: 2,
            borderRadius: 3,
          },
        },
      ],
    };
  }, []);

  return <EChartsWrapper option={option} height={340} showToolbox />;
}

// ---------------------------------------------------------------------------
// Performance Bar Component
// ---------------------------------------------------------------------------

function MetricBar({
  label,
  value,
  max,
  unit,
  color,
}: {
  label: string;
  value: number;
  max: number;
  unit: string;
  color: string;
}) {
  const pct = clamp((value / max) * 100, 0, 100);
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold" style={{ color }}>
          {value} {unit}
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component: FlightSurgeonConsole
// ---------------------------------------------------------------------------

export function FlightSurgeonConsole() {
  // -- Crew Member Inputs --
  const [sex, setSex] = React.useState<"male" | "female">("male");
  const [age, setAge] = React.useState("35");
  const [weight, setWeight] = React.useState("75");
  const [height, setHeight] = React.useState("175");
  const [restingHR, setRestingHR] = React.useState("68");

  // -- Environment Inputs --
  const [activityLevel, setActivityLevel] = React.useState("moderate");
  const [coldExposure, setColdExposure] = React.useState("moderate_cold");
  const [altitude, setAltitude] = React.useState("high");
  const [exerciseHours, setExerciseHours] = React.useState("2");
  const [altitudeM, setAltitudeM] = React.useState("3000");

  // -- Floating Plot State --
  const [activePlot, setActivePlot] = React.useState<string | null>(null);

  // -- Parse Inputs --
  const ageYears = parseInt(age, 10) || 35;
  const weightKg = parseFloat(weight) || 75;
  const heightCm = parseFloat(height) || 175;
  const rhr = parseInt(restingHR, 10) || 68;
  const exHours = parseFloat(exerciseHours) || 2;
  const altM = parseInt(altitudeM, 10) || 3000;

  // -- Calculations --
  const bmr = computeBMR(weightKg, heightCm, ageYears, sex);
  const pal = ACTIVITY_FACTORS[activityLevel]?.factor ?? 1.55;
  const cf = COLD_FACTORS[coldExposure]?.factor ?? 1.15;
  const af = ALTITUDE_FACTORS[altitude]?.factor ?? 1.10;
  const tee = computeTEE(bmr, pal, cf, af);
  const macros = computeMacros(tee);
  const water = computeWaterRequirement(weightKg, activityLevel, altitude, coldExposure, exHours);
  const spo2 = estimateSpO2(altM);
  const altHR = estimateAltitudeHR(rhr, altM);

  // -- Color helpers --
  const teeColor = tee > 4000 ? "#e74c3c" : tee > 3000 ? "#f39c12" : "#27ae60";
  const waterColor = water.totalMl > 5000 ? "#e74c3c" : water.totalMl > 3500 ? "#f39c12" : "#3498db";
  const spo2Color = spo2 < 85 ? "#e74c3c" : spo2 < 90 ? "#f39c12" : "#27ae60";
  const hrColor = altHR > 100 ? "#e74c3c" : altHR > 85 ? "#f39c12" : "#27ae60";

  return (
    <>
      <Card className="border-2 border-primary/20">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Stethoscope className="h-5 w-5 text-primary" />
              Flight Surgeon Console
            </CardTitle>
            <Badge className="bg-primary/10 text-primary border-primary/30">
              NASA-STD-3001
            </Badge>
          </div>
          <CardDescription>
            Crew health monitoring, nutritional & water requirements for analog missions
            (Antarctica, high altitude, extreme environments). Based on NASA-STD-3001 Vol. 2,
            Lane & Schoeller (2000), Smith & Zwart (2008).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="nutrition" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="nutrition" className="text-xs">
                <Apple className="h-3.5 w-3.5 mr-1" />
                Nutrition
              </TabsTrigger>
              <TabsTrigger value="hydration" className="text-xs">
                <Droplets className="h-3.5 w-3.5 mr-1" />
                Water
              </TabsTrigger>
              <TabsTrigger value="altitude" className="text-xs">
                <Mountain className="h-3.5 w-3.5 mr-1" />
                Altitude
              </TabsTrigger>
              <TabsTrigger value="overview" className="text-xs">
                <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                Overview
              </TabsTrigger>
            </TabsList>

            {/* ============================================================
                TAB 1: NUTRITIONAL REQUIREMENTS
                ============================================================ */}
            <TabsContent value="nutrition" className="space-y-3 mt-3">
              {/* Inputs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div>
                  <Label className="text-[10px]">Sex</Label>
                  <Select value={sex} onValueChange={(v) => setSex(v as "male" | "female")}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male" className="text-xs">Male</SelectItem>
                      <SelectItem value="female" className="text-xs">Female</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[10px]">Age (years)</Label>
                  <Input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    className="h-8 text-sm"
                    min={18}
                    max={70}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Weight (kg)</Label>
                  <Input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    className="h-8 text-sm"
                    min={40}
                    max={150}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Height (cm)</Label>
                  <Input
                    type="number"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                    className="h-8 text-sm"
                    min={140}
                    max={210}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div>
                  <Label className="text-[10px]">Activity Level</Label>
                  <Select value={activityLevel} onValueChange={setActivityLevel}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(ACTIVITY_FACTORS).map(([key, v]) => (
                        <SelectItem key={key} value={key} className="text-xs">
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[10px]">Cold Exposure</Label>
                  <Select value={coldExposure} onValueChange={setColdExposure}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(COLD_FACTORS).map(([key, v]) => (
                        <SelectItem key={key} value={key} className="text-xs">
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[10px]">Altitude</Label>
                  <Select value={altitude} onValueChange={setAltitude}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(ALTITUDE_FACTORS).map(([key, v]) => (
                        <SelectItem key={key} value={key} className="text-xs">
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Gauges */}
              <div className="grid grid-cols-4 gap-2 py-2">
                <ConsoleRingGauge
                  value={Math.round(bmr)}
                  max={3000}
                  unit="kcal"
                  label="BMR"
                  color="#3498db"
                />
                <ConsoleRingGauge
                  value={Math.round(tee)}
                  max={5000}
                  unit="kcal"
                  label="TEE"
                  color={teeColor}
                />
                <ConsoleRingGauge
                  value={macros.proteinG}
                  max={250}
                  unit="g"
                  label="Protein"
                  color="#9b59b6"
                />
                <ConsoleRingGauge
                  value={macros.carbG}
                  max={700}
                  unit="g"
                  label="Carbs"
                  color="#27ae60"
                />
              </div>

              {/* Plot buttons */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setActivePlot("energy")}
                >
                  <TrendingUp className="h-3.5 w-3.5 mr-1" />
                  Energy Plot
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setActivePlot("macros")}
                >
                  <TrendingUp className="h-3.5 w-3.5 mr-1" />
                  Macro Radar
                </Button>
              </div>

              {/* Expandable Detail Sections */}
              <ExpandSection
                title="Energy Expenditure Breakdown"
                icon={<Flame className="h-3.5 w-3.5 text-orange-500" />}
                defaultOpen
                badge={`${Math.round(tee)} kcal`}
                badgeColor={teeColor}
              >
                <div className="space-y-2 text-xs">
                  <MetricBar
                    label="Basal Metabolic Rate"
                    value={Math.round(bmr)}
                    max={3000}
                    unit="kcal"
                    color="#3498db"
                  />
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Activity Multiplier (PAL)</span>
                    <span className="font-semibold">x{pal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Cold Exposure Factor</span>
                    <span className="font-semibold">x{cf.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Altitude Factor</span>
                    <span className="font-semibold">x{af.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t font-bold">
                    <span>Total Energy Expenditure</span>
                    <span style={{ color: teeColor }}>{Math.round(tee)} kcal/day</span>
                  </div>
                  <p className="text-[9px] text-muted-foreground mt-1">
                    BMR: Mifflin-St Jeor (Frankenfield et al., 2005). PAL: NASA JSC-63555.
                    Cold: Castellani & Young (2007). <i>J Appl Physiol</i>, 99(4).
                    Altitude: Butterfield et al. (1992). <i>J Appl Physiol</i>, 72(4).
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Macronutrient Requirements (NASA-STD-3001)"
                icon={<Apple className="h-3.5 w-3.5 text-green-500" />}
                defaultOpen={false}
              >
                <div className="space-y-2 text-xs">
                  <MetricBar
                    label={`Protein (${(MACRO_TARGETS.protein.min * 100).toFixed(0)}-${(MACRO_TARGETS.protein.max * 100).toFixed(0)}% TEE)`}
                    value={macros.proteinG}
                    max={250}
                    unit="g"
                    color="#9b59b6"
                  />
                  <MetricBar
                    label={`Carbohydrate (${(MACRO_TARGETS.carbohydrate.min * 100).toFixed(0)}-${(MACRO_TARGETS.carbohydrate.max * 100).toFixed(0)}% TEE)`}
                    value={macros.carbG}
                    max={600}
                    unit="g"
                    color="#27ae60"
                  />
                  <MetricBar
                    label={`Fat (${(MACRO_TARGETS.fat.min * 100).toFixed(0)}-${(MACRO_TARGETS.fat.max * 100).toFixed(0)}% TEE)`}
                    value={macros.fatG}
                    max={200}
                    unit="g"
                    color="#f39c12"
                  />
                  <div className="flex justify-between pt-1 border-t">
                    <span className="text-muted-foreground">Protein per kg body mass</span>
                    <span className="font-semibold">
                      {(macros.proteinG / weightKg).toFixed(2)} g/kg
                    </span>
                  </div>
                  <p className="text-[9px] text-muted-foreground mt-1">
                    NASA-STD-3001 Vol. 2, Rev B (2019). Smith, S.M. et al. (2005).
                    Nutritional requirements for spaceflight. <i>J Nutr</i>, 135(3), 437-443.
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Key Micronutrients for Analog Missions"
                icon={<Zap className="h-3.5 w-3.5 text-yellow-500" />}
                defaultOpen={false}
              >
                <div className="space-y-1">
                  {MICRONUTRIENT_TARGETS.map((mn) => (
                    <div
                      key={mn.name}
                      className="flex items-center justify-between text-xs py-1 border-b last:border-0"
                    >
                      <div>
                        <span className="font-semibold">{mn.name}</span>
                        <span className="text-[10px] text-muted-foreground ml-2">
                          {mn.note}
                        </span>
                      </div>
                      <Badge variant="outline" className="text-[10px] shrink-0">
                        {mn.amount}
                      </Badge>
                    </div>
                  ))}
                  <p className="text-[9px] text-muted-foreground mt-2">
                    Smith, S.M. & Zwart, S.R. (2008). Nutritional biochemistry of spaceflight.
                    <i> Adv Clin Chem</i>, 46, 87-130. Lane, H.W. et al. (2013).
                    NASA/TP-2013-217457.
                  </p>
                </div>
              </ExpandSection>
            </TabsContent>

            {/* ============================================================
                TAB 2: WATER REQUIREMENTS
                ============================================================ */}
            <TabsContent value="hydration" className="space-y-3 mt-3">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div>
                  <Label className="text-[10px]">Body Mass (kg)</Label>
                  <Input
                    type="number"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                    className="h-8 text-sm"
                    min={40}
                    max={150}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Exercise (h/day)</Label>
                  <Input
                    type="number"
                    value={exerciseHours}
                    onChange={(e) => setExerciseHours(e.target.value)}
                    className="h-8 text-sm"
                    min={0}
                    max={12}
                    step={0.5}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Activity Level</Label>
                  <Select value={activityLevel} onValueChange={setActivityLevel}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(ACTIVITY_FACTORS).map(([key, v]) => (
                        <SelectItem key={key} value={key} className="text-xs">
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Water Gauges */}
              <div className="grid grid-cols-4 gap-2 py-2">
                <ConsoleRingGauge
                  value={Math.round(water.baseMl / 100) / 10}
                  max={5}
                  unit="L"
                  label="Baseline"
                  color="#3498db"
                />
                <ConsoleRingGauge
                  value={Math.round(water.activityMl / 100) / 10}
                  max={4}
                  unit="L"
                  label="Activity"
                  color="#27ae60"
                />
                <ConsoleRingGauge
                  value={Math.round(water.altitudeMl / 100) / 10}
                  max={1.5}
                  unit="L"
                  label="Altitude"
                  color="#9b59b6"
                />
                <ConsoleRingGauge
                  value={Math.round(water.totalMl / 100) / 10}
                  max={8}
                  unit="L"
                  label="Total/Day"
                  color={waterColor}
                />
              </div>

              {/* Plot button */}
              <Button
                variant="outline"
                size="sm"
                className="text-xs"
                onClick={() => setActivePlot("water")}
              >
                <TrendingUp className="h-3.5 w-3.5 mr-1" />
                Water Breakdown Plot
              </Button>

              <ExpandSection
                title="Water Requirement Details"
                icon={<Droplets className="h-3.5 w-3.5 text-blue-500" />}
                defaultOpen
                badge={`${(water.totalMl / 1000).toFixed(1)} L/day`}
                badgeColor={waterColor}
              >
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Baseline (~33 mL/kg)</span>
                    <span className="font-semibold">{water.baseMl} mL</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Activity ({exHours}h exercise)</span>
                    <span className="font-semibold">{water.activityMl} mL</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Altitude ({ALTITUDE_FACTORS[altitude]?.altRange ?? ""} m)
                    </span>
                    <span className="font-semibold">{water.altitudeMl} mL</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      Cold Exposure ({COLD_FACTORS[coldExposure]?.tempRange ?? ""} C)
                    </span>
                    <span className="font-semibold">{water.coldMl} mL</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t font-bold">
                    <span>Total Daily Requirement</span>
                    <span style={{ color: waterColor }}>
                      {water.totalMl} mL ({(water.totalMl / 1000).toFixed(1)} L)
                    </span>
                  </div>
                  {water.totalMl > 5000 && (
                    <div className="flex items-start gap-1 mt-1 p-2 bg-orange-50 border border-orange-200 rounded">
                      <AlertTriangle className="h-3 w-3 mt-0.5 text-orange-500 shrink-0" />
                      <p className="text-[10px] text-orange-700">
                        High water demand ({(water.totalMl / 1000).toFixed(1)} L/day).
                        Plan water resupply logistics. Consider electrolyte supplementation
                        (0.5-0.7 g/L sodium) for intake above 4 L/day.
                      </p>
                    </div>
                  )}
                  <p className="text-[9px] text-muted-foreground mt-1">
                    IOM (2004). Dietary Reference Intakes for Water. Butterfield, G.E. (1999).
                    <i> Med Sci Sports Exerc</i>, 31(suppl). Freund, B.J. & Sawka, M.N. (1996).
                    <i> Arctic Med Res</i>, 55(suppl 1).
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Electrolyte Replacement Guide"
                icon={<Zap className="h-3.5 w-3.5 text-yellow-500" />}
                defaultOpen={false}
              >
                <div className="space-y-2 text-xs">
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <span className="text-muted-foreground">Sodium (Na+)</span>
                    <span className="font-semibold">500-700 mg/L water</span>
                    <span className="text-muted-foreground">Potassium (K+)</span>
                    <span className="font-semibold">200-300 mg/L water</span>
                    <span className="text-muted-foreground">Chloride (Cl-)</span>
                    <span className="font-semibold">750-1050 mg/L water</span>
                    <span className="text-muted-foreground">Magnesium (Mg2+)</span>
                    <span className="font-semibold">50-100 mg/day extra</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1">
                    For exercise &gt;60 min or ambient temp &gt;30 C, add electrolytes.
                    ACSM recommends carbohydrate-electrolyte drinks (6-8% CHO) during
                    exercise &gt;90 min (Sawka et al., 2007).
                  </p>
                </div>
              </ExpandSection>
            </TabsContent>

            {/* ============================================================
                TAB 3: ALTITUDE & ENVIRONMENTAL PHYSIOLOGY
                ============================================================ */}
            <TabsContent value="altitude" className="space-y-3 mt-3">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                <div>
                  <Label className="text-[10px]">Altitude (m)</Label>
                  <Input
                    type="number"
                    value={altitudeM}
                    onChange={(e) => setAltitudeM(e.target.value)}
                    className="h-8 text-sm"
                    min={0}
                    max={8848}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Resting HR (bpm)</Label>
                  <Input
                    type="number"
                    value={restingHR}
                    onChange={(e) => setRestingHR(e.target.value)}
                    className="h-8 text-sm"
                    min={40}
                    max={120}
                  />
                </div>
                <div>
                  <Label className="text-[10px]">Altitude Category</Label>
                  <Select value={altitude} onValueChange={setAltitude}>
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(ALTITUDE_FACTORS).map(([key, v]) => (
                        <SelectItem key={key} value={key} className="text-xs">
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Altitude Gauges */}
              <div className="grid grid-cols-4 gap-2 py-2">
                <ConsoleRingGauge
                  value={spo2}
                  max={100}
                  unit="%"
                  label="Est. SpO2"
                  color={spo2Color}
                />
                <ConsoleRingGauge
                  value={altHR}
                  max={180}
                  unit="bpm"
                  label="Est. Rest HR"
                  color={hrColor}
                />
                <ConsoleRingGauge
                  value={altM}
                  max={9000}
                  unit="m"
                  label="Altitude"
                  color={altM > 4000 ? "#e74c3c" : altM > 2500 ? "#f39c12" : "#27ae60"}
                />
                <ConsoleRingGauge
                  value={Math.round(af * 100 - 100)}
                  max={40}
                  unit="%"
                  label="Met. Increase"
                  color={af > 1.15 ? "#e74c3c" : af > 1.05 ? "#f39c12" : "#27ae60"}
                />
              </div>

              {/* Plot buttons */}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setActivePlot("altitude")}
                >
                  <TrendingUp className="h-3.5 w-3.5 mr-1" />
                  Altitude Physiology Plot
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => setActivePlot("stress")}
                >
                  <TrendingUp className="h-3.5 w-3.5 mr-1" />
                  Stress Heatmap
                </Button>
              </div>

              <ExpandSection
                title="Altitude Physiology (Bartsch & Saltin, 2008)"
                icon={<Mountain className="h-3.5 w-3.5 text-purple-500" />}
                defaultOpen
                badge={`${altM}m`}
                badgeColor={altM > 4000 ? "#e74c3c" : altM > 2500 ? "#f39c12" : "#27ae60"}
              >
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Estimated SpO2</span>
                    <span className="font-bold" style={{ color: spo2Color }}>
                      {spo2}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Resting HR at altitude</span>
                    <span className="font-bold" style={{ color: hrColor }}>
                      {altHR} bpm (base: {rhr} bpm)
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">VO2max reduction (est.)</span>
                    <span className="font-semibold">
                      {altM > 1500
                        ? `-${Math.round(Math.min(50, (altM - 1500) * 0.01))}%`
                        : "Minimal"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Acclimatization time</span>
                    <span className="font-semibold">
                      {altM > 4500
                        ? "2-4 weeks"
                        : altM > 2500
                          ? "1-2 weeks"
                          : "Minimal"}
                    </span>
                  </div>
                  {spo2 < 90 && (
                    <div className="flex items-start gap-1 mt-1 p-2 bg-red-50 border border-red-200 rounded">
                      <AlertTriangle className="h-3 w-3 mt-0.5 text-red-500 shrink-0" />
                      <p className="text-[10px] text-red-700">
                        SpO2 &lt;90%: Hypoxemia risk. Supplemental O2 may be required.
                        Monitor for AMS symptoms (headache, nausea, fatigue).
                      </p>
                    </div>
                  )}
                  <p className="text-[9px] text-muted-foreground mt-1">
                    Bartsch, P. & Saltin, B. (2008). General introduction to altitude adaptation
                    and mountain sickness. <i>Scand J Med Sci Sports</i>, 18(S1), 1-10.
                    DOI: 10.1111/j.1600-0838.2008.00827.x. West, J.B. (2004).
                    The physiologic basis of high-altitude diseases. <i>Ann Intern Med</i>,
                    141(10), 789-800.
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Acute Mountain Sickness (AMS) Checklist"
                icon={<Brain className="h-3.5 w-3.5 text-red-500" />}
                defaultOpen={altM > 2500}
              >
                <div className="space-y-1 text-xs">
                  {[
                    { symptom: "Headache", severity: "Cardinal symptom (Lake Louise Score)" },
                    { symptom: "Nausea / Vomiting", severity: "GI disturbance" },
                    { symptom: "Fatigue / Weakness", severity: "General malaise" },
                    { symptom: "Dizziness / Lightheadedness", severity: "Neurological" },
                    { symptom: "Difficulty sleeping", severity: "Periodic breathing at altitude" },
                  ].map((item) => (
                    <div
                      key={item.symptom}
                      className="flex items-center justify-between py-1.5 border-b last:border-0"
                    >
                      <div className="flex items-center gap-2">
                        <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />
                        <span className="font-medium">{item.symptom}</span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">{item.severity}</span>
                    </div>
                  ))}
                  <p className="text-[9px] text-muted-foreground mt-2">
                    Lake Louise AMS Score: Roach et al. (2018). <i>High Alt Med Biol</i>,
                    19(1), 4-6. Score &ge;3 with headache = AMS diagnosis.
                    Treatment: descent, O2, acetazolamide.
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Cold Injury Prevention"
                icon={<Thermometer className="h-3.5 w-3.5 text-cyan-500" />}
                defaultOpen={false}
              >
                <div className="space-y-2 text-xs">
                  <div className="p-2 bg-blue-50 border border-blue-200 rounded">
                    <p className="font-semibold text-blue-800 text-xs mb-1">
                      Hypothermia Stages (Wilderness Medical Society 2019)
                    </p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px] text-blue-700">
                      <span>Mild (32-35 C):</span>
                      <span>Shivering, impaired judgment</span>
                      <span>Moderate (28-32 C):</span>
                      <span>Shivering stops, confusion</span>
                      <span>Severe (&lt;28 C):</span>
                      <span>Unconscious, cardiac risk</span>
                    </div>
                  </div>
                  <div className="p-2 bg-cyan-50 border border-cyan-200 rounded">
                    <p className="font-semibold text-cyan-800 text-xs mb-1">
                      Frostbite Prevention
                    </p>
                    <p className="text-[10px] text-cyan-700">
                      Exposed skin: frostbite in 10-30 min at wind chill &lt;-28 C.
                      Rewarm with 37-39 C water (not dry heat). Do not rub.
                      Castellani et al. (2006). <i>Med Sci Sports Exerc</i>, 38(11).
                    </p>
                  </div>
                </div>
              </ExpandSection>
            </TabsContent>

            {/* ============================================================
                TAB 4: OVERVIEW / FLIGHT SURGEON SUMMARY
                ============================================================ */}
            <TabsContent value="overview" className="space-y-3 mt-3">
              {/* Summary Gauges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border bg-gradient-to-br from-blue-50 to-white">
                  <div className="flex items-center gap-2 mb-2">
                    <Flame className="h-4 w-4 text-orange-500" />
                    <span className="text-xs font-semibold">Energy</span>
                  </div>
                  <p className="text-lg font-bold" style={{ color: teeColor }}>
                    {Math.round(tee)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">kcal/day</p>
                </div>
                <div className="p-3 rounded-lg border bg-gradient-to-br from-blue-50 to-white">
                  <div className="flex items-center gap-2 mb-2">
                    <Droplets className="h-4 w-4 text-blue-500" />
                    <span className="text-xs font-semibold">Water</span>
                  </div>
                  <p className="text-lg font-bold" style={{ color: waterColor }}>
                    {(water.totalMl / 1000).toFixed(1)}
                  </p>
                  <p className="text-[10px] text-muted-foreground">L/day</p>
                </div>
                <div className="p-3 rounded-lg border bg-gradient-to-br from-blue-50 to-white">
                  <div className="flex items-center gap-2 mb-2">
                    <Heart className="h-4 w-4 text-red-500" />
                    <span className="text-xs font-semibold">SpO2</span>
                  </div>
                  <p className="text-lg font-bold" style={{ color: spo2Color }}>
                    {spo2}%
                  </p>
                  <p className="text-[10px] text-muted-foreground">at {altM}m</p>
                </div>
                <div className="p-3 rounded-lg border bg-gradient-to-br from-blue-50 to-white">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="h-4 w-4 text-primary" />
                    <span className="text-xs font-semibold">Rest HR</span>
                  </div>
                  <p className="text-lg font-bold" style={{ color: hrColor }}>
                    {altHR}
                  </p>
                  <p className="text-[10px] text-muted-foreground">bpm at altitude</p>
                </div>
              </div>

              {/* Flight Surgeon Assessment */}
              <div className="p-3 bg-gradient-to-br from-primary/5 to-primary/10 border border-primary/20 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Stethoscope className="h-4 w-4 text-primary" />
                  <span className="text-xs font-semibold text-primary">
                    Flight Surgeon Assessment Summary
                  </span>
                </div>
                <div className="grid gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{
                        backgroundColor:
                          tee > 4000
                            ? "#e74c3c"
                            : tee > 3000
                              ? "#f39c12"
                              : "#27ae60",
                      }}
                    />
                    <span className="text-muted-foreground">Metabolic Demand:</span>
                    <span className="font-semibold">
                      {tee > 4000
                        ? "Very High - Monitor weight and intake closely"
                        : tee > 3000
                          ? "Elevated - Ensure adequate nutrition"
                          : "Normal range"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{
                        backgroundColor:
                          water.totalMl > 5000 ? "#e74c3c" : water.totalMl > 3500 ? "#f39c12" : "#27ae60",
                      }}
                    />
                    <span className="text-muted-foreground">Hydration Status:</span>
                    <span className="font-semibold">
                      {water.totalMl > 5000
                        ? "Critical - Water resupply logistics required"
                        : water.totalMl > 3500
                          ? "Elevated - Enforce hydration schedule"
                          : "Manageable - Standard hydration protocol"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: spo2Color }}
                    />
                    <span className="text-muted-foreground">Altitude Risk:</span>
                    <span className="font-semibold">
                      {spo2 < 85
                        ? "HIGH - Supplemental O2 required, AMS monitoring"
                        : spo2 < 90
                          ? "MODERATE - Gradual ascent, AMS screening"
                          : altM > 2500
                            ? "LOW-MODERATE - Acclimatization recommended"
                            : "LOW - Standard monitoring"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Quick Reference */}
              <ExpandSection
                title="NASA Flight Surgeon Quick Reference"
                icon={<BookOpen className="h-3.5 w-3.5 text-primary" />}
                defaultOpen={false}
              >
                <div className="space-y-2 text-xs">
                  <div className="p-2 bg-muted/50 rounded">
                    <p className="font-semibold mb-1">Daily Monitoring Protocol</p>
                    <ol className="list-decimal list-inside space-y-0.5 text-muted-foreground text-[10px]">
                      <li>Body mass (AM, post-void, pre-breakfast)</li>
                      <li>Resting heart rate and blood pressure</li>
                      <li>SpO2 (at altitude: morning and evening)</li>
                      <li>Sleep quality assessment (Pittsburgh Sleep Quality Index)</li>
                      <li>Urine specific gravity (hydration marker)</li>
                      <li>Food intake log (calories, macros)</li>
                      <li>Fluid intake log (volume, timing)</li>
                      <li>Subjective wellness rating (1-10 scale)</li>
                      <li>AMS scoring if above 2500m (Lake Louise)</li>
                      <li>HRV recording (5-min morning supine)</li>
                    </ol>
                  </div>
                  <div className="p-2 bg-muted/50 rounded">
                    <p className="font-semibold mb-1">Crew-Care Thresholds</p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[10px] text-muted-foreground">
                      <span>Weight loss &gt;3% in 1 week:</span>
                      <span className="font-semibold text-red-600">Evaluate nutrition</span>
                      <span>Urine SG &gt;1.020:</span>
                      <span className="font-semibold text-orange-600">Increase fluids</span>
                      <span>SpO2 &lt;90% (at alt.):</span>
                      <span className="font-semibold text-red-600">Evaluate for AMS</span>
                      <span>Resting HR &gt;100 bpm:</span>
                      <span className="font-semibold text-orange-600">Evaluate dehydration</span>
                      <span>RMSSD &lt;20 ms:</span>
                      <span className="font-semibold text-orange-600">Recovery impaired</span>
                      <span>Sleep &lt;6 h/night:</span>
                      <span className="font-semibold text-orange-600">Adjust schedule</span>
                    </div>
                  </div>
                  <p className="text-[9px] text-muted-foreground">
                    Based on: NASA-STD-3001 Vol. 1 & 2 (2019); Wilderness Medical Society Practice
                    Guidelines (Luks et al., 2019); ACSM Position Stand (Sawka et al., 2007);
                    ESC/ESH Guidelines (Williams et al., 2018).
                  </p>
                </div>
              </ExpandSection>

              <ExpandSection
                title="Scientific References"
                icon={<BookOpen className="h-3.5 w-3.5 text-muted-foreground" />}
                defaultOpen={false}
              >
                <div className="space-y-1 text-[9px] text-muted-foreground">
                  <p>
                    1. NASA. (2019). <i>NASA-STD-3001, NASA Space Flight Human-System Standard
                    Volume 2: Human Factors, Habitability, and Environmental Health</i>, Rev B.
                  </p>
                  <p>
                    2. Lane, H.W. & Schoeller, D.A. (2000). Nutrition in spaceflight and
                    weightlessness models. <i>CRC Press</i>.
                  </p>
                  <p>
                    3. Smith, S.M. & Zwart, S.R. (2008). Nutritional biochemistry of spaceflight.
                    <i> Adv Clin Chem</i>, 46, 87-130.
                  </p>
                  <p>
                    4. Castellani, J.W. & Young, A.J. (2007). Human physiological responses to
                    cold exposure. <i>Auton Neurosci</i>, 196, 68-74.
                  </p>
                  <p>
                    5. Butterfield, G.E. et al. (1992). Increased energy intake minimizes weight
                    loss in men at high altitude. <i>J Appl Physiol</i>, 72(4), 1741-1748.
                  </p>
                  <p>
                    6. Bartsch, P. & Saltin, B. (2008). General introduction to altitude adaptation.
                    <i> Scand J Med Sci Sports</i>, 18(S1), 1-10.
                  </p>
                  <p>
                    7. Sawka, M.N. et al. (2007). Exercise and fluid replacement (ACSM Position
                    Stand). <i>Med Sci Sports Exerc</i>, 39(2), 377-390.
                  </p>
                  <p>
                    8. Mifflin, M.D. et al. (1990). A new predictive equation for resting energy
                    expenditure. <i>Am J Clin Nutr</i>, 51(2), 241-247.
                  </p>
                  <p>
                    9. Roach, R.C. et al. (2018). The 2018 Lake Louise Acute Mountain Sickness
                    Score. <i>High Alt Med Biol</i>, 19(1), 4-6.
                  </p>
                  <p>
                    10. Luks, A.M. et al. (2019). Wilderness Medical Society Clinical Practice
                    Guidelines for the Prevention and Treatment of Acute Altitude Illness.
                    <i> Wilderness Environ Med</i>, 30(4S), S4-S14.
                  </p>
                </div>
              </ExpandSection>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* ================================================================
          FLOATING PLOT PANES
          ================================================================ */}
      <FloatingPlotPane
        title="Energy Expenditure Breakdown"
        isOpen={activePlot === "energy"}
        onClose={() => setActivePlot(null)}
      >
        <EnergyBreakdownChart
          bmr={bmr}
          tee={tee}
          activityLabel={ACTIVITY_FACTORS[activityLevel]?.label ?? ""}
          coldLabel={COLD_FACTORS[coldExposure]?.label ?? ""}
          altLabel={ALTITUDE_FACTORS[altitude]?.label ?? ""}
        />
        <div className="mt-3 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">
          <p className="font-semibold mb-1">Interpretation</p>
          <p>
            Total Energy Expenditure (TEE) = BMR x Physical Activity Level (PAL)
            x Cold Factor x Altitude Factor. At extreme environments, TEE can
            reach 4000-5000+ kcal/day. Lane & Schoeller (2000) documented ISS
            crew energy requirements of 2800-3200 kcal/day; analog missions with
            physical fieldwork in cold/altitude environments may exceed this.
          </p>
        </div>
      </FloatingPlotPane>

      <FloatingPlotPane
        title="Macronutrient Profile"
        isOpen={activePlot === "macros"}
        onClose={() => setActivePlot(null)}
      >
        <MacroRadarChart
          proteinG={macros.proteinG}
          carbG={macros.carbG}
          fatG={macros.fatG}
          tee={tee}
        />
        <div className="mt-3 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">
          <p className="font-semibold mb-1">NASA Macronutrient Guidelines</p>
          <p>
            Protein: 12-15% of TEE (~0.8-1.2 g/kg/day, higher for active crew).
            Carbohydrate: 50-55% of TEE (primary fuel for exercise and brain).
            Fat: 25-35% of TEE (essential fatty acids, energy density for cold environments).
            Smith et al. (2005). <i>J Nutr</i>, 135(3), 437-443.
          </p>
        </div>
      </FloatingPlotPane>

      <FloatingPlotPane
        title="Water Requirement Breakdown"
        isOpen={activePlot === "water"}
        onClose={() => setActivePlot(null)}
      >
        <WaterRequirementChart
          baseMl={water.baseMl}
          activityMl={water.activityMl}
          altitudeMl={water.altitudeMl}
          coldMl={water.coldMl}
          totalMl={water.totalMl}
        />
        <div className="mt-3 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">
          <p className="font-semibold mb-1">Water Balance in Extreme Environments</p>
          <p>
            Baseline: ~33 mL/kg/day (IOM, 2004). At altitude, respiratory water
            losses increase 2-3x due to low humidity and increased ventilation
            (Butterfield, 1999). Cold-induced diuresis adds 200-800 mL/day
            (Freund & Sawka, 1996). Activity can add 0.5-1.5 L per hour of
            exercise depending on intensity (Sawka et al., 2007).
          </p>
        </div>
      </FloatingPlotPane>

      <FloatingPlotPane
        title="Altitude Physiology: SpO2 & Heart Rate"
        isOpen={activePlot === "altitude"}
        onClose={() => setActivePlot(null)}
      >
        <AltitudePhysiologyChart restingHR={rhr} />
        <div className="mt-3 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">
          <p className="font-semibold mb-1">Altitude Physiology</p>
          <p>
            SpO2 decreases with altitude due to reduced partial pressure of oxygen.
            Below 1500m, minimal effect. Above 2500m, SpO2 drops ~3% per 1000m.
            Resting HR increases ~10% per 1000m above 2500m as cardiac compensation
            for reduced O2 delivery. VO2max declines ~1% per 100m above 1500m.
            Bartsch & Saltin (2008); West (2004); Severinghaus (1979).
          </p>
        </div>
      </FloatingPlotPane>

      <FloatingPlotPane
        title="Analog Mission Environmental Stress Profile"
        isOpen={activePlot === "stress"}
        onClose={() => setActivePlot(null)}
      >
        <EnvironmentalStressChart />
        <div className="mt-3 p-3 bg-muted/30 rounded-lg text-xs text-muted-foreground">
          <p className="font-semibold mb-1">Stress Profile Interpretation</p>
          <p>
            Space analog missions (Antarctica, high-altitude stations) share key
            stressors with spaceflight: isolation, confinement, extreme environment,
            altered circadian rhythms, and workload. The heatmap shows typical
            stress evolution across mission phases. Isolation and sleep disruption
            tend to worsen in later phases (Palinkas & Suedfeld, 2008).
            Physical stressors (cold, altitude) peak during early adaptation.
          </p>
        </div>
      </FloatingPlotPane>
    </>
  );
}
