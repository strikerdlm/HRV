// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Snowflake,
  Flame,
  Plane,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Droplets,
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
import { Switch } from "@/components/ui/switch";
import { RISK_LEVEL_COLORS } from "@/types/research";

// ---------------------------------------------------------------------------
// Client-side calculators (same formulas as Python backend)
// ---------------------------------------------------------------------------

function windChill(tempC: number, windKmh: number): number {
  if (tempC > 10 || windKmh < 4.8) return tempC;
  const vExp = Math.pow(windKmh, 0.16);
  return Math.round((13.12 + 0.6215 * tempC - 11.37 * vExp + 0.3965 * tempC * vExp) * 10) / 10;
}

function frostbiteMinutes(wc: number): number | null {
  if (wc > -18) return null;
  if (wc > -28) return 30;
  if (wc > -35) return 15;
  if (wc > -45) return 10;
  if (wc > -55) return 5;
  return 2;
}

function coldRisk(wc: number): string {
  if (wc > -10) return "Low";
  if (wc > -27) return "Moderate";
  if (wc > -39) return "High";
  if (wc > -54) return "Very High";
  return "Extreme";
}

function wbgtSimplified(tempC: number, rhPct: number): number {
  const eSat = 6.105 * Math.exp((17.27 * tempC) / (237.7 + tempC));
  const e = (eSat * rhPct) / 100;
  return Math.round((0.567 * tempC + 0.393 * e + 3.94) * 10) / 10;
}

function heatRisk(wbgt: number): string {
  if (wbgt < 25) return "Low";
  if (wbgt < 28) return "Moderate";
  if (wbgt < 30) return "High";
  if (wbgt < 33) return "Very High";
  return "Extreme";
}

function workRestGuidance(risk: string): string {
  const map: Record<string, string> = {
    Low: "Continuous work. Monitor hydration.",
    Moderate: "45 min work / 15 min rest per hour.",
    High: "30 min work / 30 min rest per hour.",
    "Very High": "15 min work / 45 min rest per hour.",
    Extreme: "Suspend work. Emergency cooling required.",
  };
  return map[risk] || "";
}

// FITS: Fighter Index of Thermal Stress (Stribley & Nunneley, 1978)
function psychWetBulb(tempC: number, rhPct: number): number {
  const t = tempC;
  const rh = Math.max(5, Math.min(99, rhPct));
  return (
    t * Math.atan(0.151977 * Math.pow(rh + 8.313659, 0.5)) +
    Math.atan(t + rh) -
    Math.atan(rh - 1.676331) +
    0.00391838 * Math.pow(rh, 1.5) * Math.atan(0.023101 * rh) -
    4.686035
  );
}

function computeFITS(tempC: number, rhPct: number, directSun: boolean): number {
  const twb = psychWetBulb(tempC, rhPct);
  const offset = directSun ? 5.08 : 2.23;
  return Math.round((0.8281 * twb + 0.3549 * tempC + offset) * 10) / 10;
}

function fitsZone(fits: number): string {
  if (fits >= 38) return "Danger";
  if (fits >= 32) return "Caution";
  return "Normal";
}

function fitsGuidance(zone: string): string {
  if (zone === "Danger")
    return "Cancel low-level flights (<915m AGL). Limit ground period to 45 min. 2-hr recovery required.";
  if (zone === "Caution")
    return "Limit ground ops to 90 min. 2-hr cool recovery between flights. Ensure fluid intake.";
  return "Normal precautions. Allow acclimatization. Maintain hydration.";
}

// Apparent Temperature (Steadman, 1984)
function apparentTemp(tempC: number, rhPct: number, windMs: number): number {
  const e = (rhPct / 100) * 6.105 * Math.exp((17.27 * tempC) / (237.7 + tempC));
  const at = tempC + 0.33 * e - 0.7 * windMs - 4.0;
  return Math.round(at * 10) / 10;
}

// ---------------------------------------------------------------------------
// SVG ring gauge for results
// ---------------------------------------------------------------------------

function ResultRing({
  value,
  label,
  unit,
  color,
  max,
}: {
  value: number;
  label: string;
  unit: string;
  color: string;
  max: number;
}) {
  const pct = Math.max(0, Math.min(1, Math.abs(value) / max));
  const circ = 2 * Math.PI * 28;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-16 h-16">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r="28" fill="none" stroke={color} strokeWidth="5" opacity="0.15" />
          <circle cx="36" cy="36" r="28" fill="none" stroke={color} strokeWidth="5"
            strokeDasharray={`${pct * circ} ${circ}`} strokeLinecap="round" />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs font-bold" style={{ color }}>{value}</span>
          <span className="text-[7px] text-muted-foreground">{unit}</span>
        </div>
      </div>
      <p className="text-[9px] text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expandable section
// ---------------------------------------------------------------------------

function ExpandSection({
  title,
  icon,
  defaultOpen,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen: boolean;
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
// Main Component
// ---------------------------------------------------------------------------

export function ExtremeWeatherCalc() {
  const [temp, setTemp] = React.useState("35");
  const [wind, setWind] = React.useState("20");
  const [rh, setRh] = React.useState("60");
  const [directSun, setDirectSun] = React.useState(true);

  const tempC = parseFloat(temp) || 0;
  const windKmh = parseFloat(wind) || 0;
  const rhPct = parseFloat(rh) || 50;
  const windMs = windKmh / 3.6;

  // Cold calculations
  const wc = windChill(tempC, windKmh);
  const fb = frostbiteMinutes(wc);
  const cr = coldRisk(wc);

  // Heat calculations
  const wbgt = wbgtSimplified(tempC, rhPct);
  const hr = heatRisk(wbgt);
  const wrg = workRestGuidance(hr);

  // FITS
  const fits = computeFITS(tempC, rhPct, directSun);
  const fz = fitsZone(fits);
  const fg = fitsGuidance(fz);

  // Apparent Temperature
  const at = apparentTemp(tempC, rhPct, windMs);

  const isCold = tempC < 10;
  const fitsColor = fz === "Danger" ? "#e74c3c" : fz === "Caution" ? "#f39c12" : "#27ae60";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          {isCold ? <Snowflake className="h-5 w-5 text-cyan-500" /> : <Flame className="h-5 w-5 text-orange-500" />}
          Extreme Environment Assessment
        </CardTitle>
        <CardDescription>NWS Wind Chill + ISO 7243 WBGT + USAF FITS</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Inputs */}
        <div className="grid grid-cols-3 gap-2">
          <div>
            <Label className="text-[10px]">Temp (C)</Label>
            <Input type="number" value={temp} onChange={(e) => setTemp(e.target.value)} className="h-8 text-sm" />
          </div>
          <div>
            <Label className="text-[10px]">Wind (km/h)</Label>
            <Input type="number" value={wind} onChange={(e) => setWind(e.target.value)} className="h-8 text-sm" />
          </div>
          <div>
            <Label className="text-[10px]">RH (%)</Label>
            <Input type="number" value={rh} onChange={(e) => setRh(e.target.value)} className="h-8 text-sm" />
          </div>
        </div>

        {/* Result rings */}
        <div className="grid grid-cols-4 gap-1 py-2">
          <ResultRing value={wc} label="Wind Chill" unit="C" color={RISK_LEVEL_COLORS[cr] || "#27ae60"} max={60} />
          <ResultRing value={wbgt} label="WBGT" unit="C" color={RISK_LEVEL_COLORS[hr] || "#27ae60"} max={45} />
          <ResultRing value={fits} label="FITS" unit="C" color={fitsColor} max={55} />
          <ResultRing value={at} label="Apparent" unit="C" color={at > 40 ? "#e74c3c" : at > 30 ? "#f39c12" : at < 0 ? "#3498db" : "#27ae60"} max={55} />
        </div>

        {/* Expandable sections */}
        <ExpandSection
          title="Cold Exposure (NWS Wind Chill 2001)"
          icon={<Snowflake className="h-3.5 w-3.5 text-cyan-500" />}
          defaultOpen={isCold}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs">Risk:</span>
            <Badge style={{ backgroundColor: RISK_LEVEL_COLORS[cr] || "#888", color: "#fff" }} className="text-xs">{cr}</Badge>
          </div>
          {fb != null && (
            <p className="text-xs flex items-center gap-1 text-red-600">
              <Clock className="h-3 w-3" /> Frostbite in ~{fb} min on exposed skin
            </p>
          )}
          <p className="text-[9px] text-muted-foreground mt-1">Osczevski & Bluestein (2005). BAMS, 86(10).</p>
        </ExpandSection>

        <ExpandSection
          title="Heat Stress (ISO 7243 WBGT)"
          icon={<Flame className="h-3.5 w-3.5 text-orange-500" />}
          defaultOpen={!isCold}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs">Risk:</span>
            <Badge style={{ backgroundColor: RISK_LEVEL_COLORS[hr] || "#888", color: "#fff" }} className="text-xs">{hr}</Badge>
          </div>
          <p className="text-xs">{wrg}</p>
          <p className="text-[9px] text-muted-foreground mt-1">ISO 7243:2017 | Steadman (1979).</p>
        </ExpandSection>

        <ExpandSection
          title="Fighter Index of Thermal Stress (USAF FITS)"
          icon={<Plane className="h-3.5 w-3.5 text-amber-600" />}
          defaultOpen={false}
        >
          <div className="flex items-center gap-2 mb-2">
            <Label className="text-xs">Direct Sun</Label>
            <Switch checked={directSun} onCheckedChange={setDirectSun} />
            <span className="text-[10px] text-muted-foreground">{directSun ? "Clear sky" : "Overcast"}</span>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs">FITS Zone:</span>
            <Badge style={{ backgroundColor: fitsColor, color: "#fff" }} className="text-xs">{fz}</Badge>
          </div>
          <p className="text-xs mb-1">{fg}</p>
          {fits >= 46 && (
            <div className="flex items-center gap-1 text-red-600 text-xs mt-1">
              <AlertTriangle className="h-3 w-3" />
              FITS &gt; 46 C: Cancel ALL nonessential flights
            </div>
          )}
          <p className="text-[9px] text-muted-foreground mt-1">
            Stribley & Nunneley (1978). SAM-TR-78-6. Brooks AFB.
          </p>
        </ExpandSection>

        <ExpandSection
          title="Apparent Temperature (Steadman 1984)"
          icon={<Droplets className="h-3.5 w-3.5 text-blue-500" />}
          defaultOpen={false}
        >
          <p className="text-xs">
            Feels like <span className="font-bold" style={{ color: at > 40 ? "#e74c3c" : at > 30 ? "#f39c12" : "#27ae60" }}>{at} C</span> accounting for humidity and wind.
          </p>
          <p className="text-[9px] text-muted-foreground mt-1">Steadman, R.G. (1984). JAM, 23, 1674-1687.</p>
        </ExpandSection>
      </CardContent>
    </Card>
  );
}
