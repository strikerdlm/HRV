// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle,
  Droplets,
  Heart,
  Plane,
  Shield,
  Thermometer,
  XCircle,
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EChartsWrapper } from "@/components/charts";
import { submitVitalsAndAssess } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type {
  EnhancedReadinessResponse,
  SMSMatrixData,
} from "@/types/research";
import { SMS_RISK_COLORS, READINESS_LABEL_COLORS } from "@/types/research";
import {
  HydrationDashboardGauges,
  computeHydrationReadinessModifier,
} from "@/components/hydration-thermoregulation";

const DEFAULT_USER_ID = "demo-user";

// ---------------------------------------------------------------------------
// Compact SMS Heatmap for Operational View
// ---------------------------------------------------------------------------

function buildOperationalHeatmap(
  title: string,
  matrix: SMSMatrixData,
  posRow: number,
  posCol: number,
): Record<string, unknown> {
  return {
    title: {
      text: title,
      left: "center",
      textStyle: { color: "#1a1a1a", fontWeight: "bold", fontSize: 13 },
    },
    tooltip: {
      position: "top",
      formatter: (p: { data: number[] }) => {
        const [col, row, val] = p.data;
        return `${matrix.severity_labels[row]} x ${matrix.likelihood_labels[col]}: ${matrix.risk_levels[val]}`;
      },
    },
    grid: { left: "20%", right: "6%", top: 40, bottom: 55, containLabel: true },
    xAxis: {
      type: "category",
      data: matrix.likelihood_labels,
      axisLabel: { color: "#1a1a1a", fontSize: 9, rotate: 20 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: matrix.severity_labels,
      axisLabel: { color: "#1a1a1a", fontSize: 9 },
      splitArea: { show: true },
    },
    visualMap: {
      type: "piecewise",
      min: 0,
      max: matrix.risk_levels.length - 1,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      pieces: matrix.risk_levels.map((label, i) => ({
        value: i,
        label,
        color: matrix.risk_colors[i],
      })),
      textStyle: { color: "#1a1a1a", fontSize: 9 },
      itemWidth: 12,
      itemHeight: 12,
    },
    series: [
      {
        type: "heatmap",
        data: matrix.data,
        label: {
          show: true,
          formatter: (p: { data: number[] }) => matrix.risk_levels[p.data[2]],
          color: "#1a1a1a",
          fontSize: 8,
        },
        itemStyle: { borderWidth: 1, borderColor: "#fff" },
      },
      {
        type: "scatter",
        data: [[posCol, posRow]],
        symbolSize: 20,
        itemStyle: { color: "#2c3e50", borderColor: "#fff", borderWidth: 3 },
        z: 10,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Go/No-Go Decision Component
// ---------------------------------------------------------------------------

function GoNoGoPanel({
  activity,
  icon,
  riskLevel,
  disqualifiers,
  rationale,
}: {
  activity: string;
  icon: React.ReactNode;
  riskLevel: string;
  disqualifiers: string[];
  rationale: string;
}) {
  const isGo = disqualifiers.length === 0 && !["Intolerable", "High"].includes(riskLevel);
  const isCaution = !isGo && !["Intolerable", "High"].includes(riskLevel);

  let bgColor = "#dcfce7"; // green
  let borderColor = "#16a34a";
  let textColor = "#15803d";
  let label = "GO";
  let DecisionIcon = CheckCircle;

  if (!isGo && !isCaution) {
    bgColor = "#fee2e2";
    borderColor = "#dc2626";
    textColor = "#dc2626";
    label = "NO-GO";
    DecisionIcon = XCircle;
  } else if (isCaution) {
    bgColor = "#fef9c3";
    borderColor = "#ca8a04";
    textColor = "#a16207";
    label = "CAUTION";
    DecisionIcon = AlertTriangle;
  }

  return (
    <Card style={{ borderColor, borderWidth: 2 }}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">{icon} {activity}</span>
          <Badge
            className="text-xl px-4 py-2"
            style={{ backgroundColor: borderColor, color: "#fff" }}
          >
            {label}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="flex items-center gap-3 p-4 rounded-lg mb-3"
          style={{ backgroundColor: bgColor }}
        >
          <DecisionIcon className="h-8 w-8" style={{ color: textColor }} />
          <div>
            <p className="text-lg font-bold" style={{ color: textColor }}>{label} for {activity}</p>
            <p className="text-sm" style={{ color: textColor }}>
              Risk Level: {riskLevel}
            </p>
          </div>
        </div>
        {disqualifiers.length > 0 && (
          <div className="p-3 bg-red-50 border border-red-200 rounded mb-2">
            <p className="font-semibold text-red-700 text-sm mb-1">Disqualifiers:</p>
            {disqualifiers.map((d, i) => (
              <p key={i} className="text-xs text-red-600 mb-0.5">{d}</p>
            ))}
          </div>
        )}
        <p className="text-xs text-[#2c3e50]">{rationale}</p>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Operational Readiness Page
// ---------------------------------------------------------------------------

export default function OperationalReadinessPage() {
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const [sbp, setSbp] = React.useState<string>("120");
  const [dbp, setDbp] = React.useState<string>("80");
  const [tempC, setTempC] = React.useState<string>("36.6");

  const [result, setResult] = React.useState<EnhancedReadinessResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const handleAssess = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await submitVitalsAndAssess(userId, {
        sbp_mmhg: sbp ? parseFloat(sbp) : null,
        dbp_mmhg: dbp ? parseFloat(dbp) : null,
        temperature_c: tempC ? parseFloat(tempC) : null,
      });
      setResult(data);
    } catch (err) {
      console.error("Assessment failed:", err);
    } finally {
      setLoading(false);
    }
  }, [userId, sbp, dbp, tempC]);

  return (
    <PageWrapper
      title="Operational Readiness Assessment"
      description="Go/No-Go decision support for EVA and military flight operations"
    >
      {/* Quick Vitals Entry */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-500" />
            Pre-Activity Vitals Check
          </CardTitle>
          <CardDescription>
            Enter crew member vitals for Go/No-Go determination.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 items-end">
            <div>
              <Label htmlFor="op-sbp" className="text-sm font-semibold">SBP (mmHg)</Label>
              <Input
                id="op-sbp"
                type="number"
                min={40}
                max={300}
                value={sbp}
                onChange={(e) => setSbp(e.target.value)}
                className="text-lg font-bold text-center h-12"
              />
            </div>
            <div>
              <Label htmlFor="op-dbp" className="text-sm font-semibold">DBP (mmHg)</Label>
              <Input
                id="op-dbp"
                type="number"
                min={20}
                max={200}
                value={dbp}
                onChange={(e) => setDbp(e.target.value)}
                className="text-lg font-bold text-center h-12"
              />
            </div>
            <div>
              <Label htmlFor="op-temp" className="text-sm font-semibold">Temp (C)</Label>
              <Input
                id="op-temp"
                type="number"
                min={25}
                max={45}
                step={0.1}
                value={tempC}
                onChange={(e) => setTempC(e.target.value)}
                className="text-lg font-bold text-center h-12"
              />
            </div>
            <Button
              onClick={handleAssess}
              disabled={loading}
              className="h-12 text-lg font-bold"
            >
              {loading ? "Checking..." : "ASSESS"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          {/* Readiness Score Banner */}
          <div
            className="mt-6 p-6 rounded-lg text-center"
            style={{
              backgroundColor: READINESS_LABEL_COLORS[result.readiness_label] || "#888",
            }}
          >
            <div className="text-6xl font-bold text-white">
              {result.readiness_score.toFixed(0)}
            </div>
            <div className="text-2xl font-bold text-white mt-1">
              {result.readiness_label}
            </div>
            <div className="flex justify-center gap-6 mt-3 text-white/90 text-sm">
              <span>BP: {result.bp_classification ?? "N/A"} ({result.bp_modifier != null ? `${result.bp_modifier >= 0 ? "+" : ""}${result.bp_modifier}` : "0"} pts)</span>
              <span>Temp: {result.temp_classification ?? "N/A"} ({result.temp_modifier != null ? `${result.temp_modifier >= 0 ? "+" : ""}${result.temp_modifier}` : "0"} pts)</span>
            </div>
          </div>

          {/* Go/No-Go Decision Panels */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            {result.eva_sms && (
              <GoNoGoPanel
                activity="Extravehicular Activity (EVA)"
                icon={<Shield className="h-5 w-5 text-blue-600" />}
                riskLevel={result.eva_sms.risk_level}
                disqualifiers={result.eva_sms.disqualifiers}
                rationale={result.eva_sms.rationale}
              />
            )}
            {result.flight_sms && (
              <GoNoGoPanel
                activity="High-Performance Flight"
                icon={<Plane className="h-5 w-5 text-amber-600" />}
                riskLevel={result.flight_sms.risk_level}
                disqualifiers={result.flight_sms.disqualifiers}
                rationale={result.flight_sms.rationale}
              />
            )}
          </div>

          {/* Hydration & Thermoregulation Impact on Readiness */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Droplets className="h-5 w-5 text-blue-500" />
                Hydration & Thermoregulation Readiness Impact
              </CardTitle>
              <CardDescription>
                Estimated dehydration, core temperature, and performance decrement
                as modifiers for the fused readiness score.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <HydrationDashboardGauges />
              <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded">
                <p className="text-xs text-blue-800">
                  <strong>Integration:</strong> Hydration-thermoregulation modifier
                  (bounded -10 to 0 pts) is applied to the fused readiness score.
                  A dehydration &ge;2% body mass loss with WBGT &ge;28 C triggers
                  a &ldquo;Caution&rdquo; flag on EVA and flight readiness. Core temperature
                  &ge;39 C or PhSI &ge;7 applies additional penalization.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* SMS Matrix Visualizations */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            {result.eva_sms && result.eva_matrix && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">EVA SMS Matrix (ICAO Doc 9859)</CardTitle>
                </CardHeader>
                <CardContent>
                  <EChartsWrapper
                    option={buildOperationalHeatmap(
                      "EVA Risk Matrix",
                      result.eva_matrix,
                      result.eva_matrix.severity_labels.indexOf(result.eva_sms.severity),
                      result.eva_matrix.likelihood_labels.indexOf(result.eva_sms.likelihood),
                    )}
                    height={320}
                  />
                </CardContent>
              </Card>
            )}
            {result.flight_sms && result.flight_matrix && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Flight SMS Matrix (MIL-STD-882E)</CardTitle>
                </CardHeader>
                <CardContent>
                  <EChartsWrapper
                    option={buildOperationalHeatmap(
                      "Flight Risk Matrix",
                      result.flight_matrix,
                      result.flight_matrix.severity_labels.indexOf(result.flight_sms.severity),
                      result.flight_matrix.likelihood_labels.indexOf(result.flight_sms.likelihood),
                    )}
                    height={320}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}
    </PageWrapper>
  );
}
