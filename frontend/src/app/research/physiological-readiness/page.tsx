// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  Heart,
  Shield,
  Thermometer,
  Zap,
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
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { submitVitalsAndAssess } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type {
  EnhancedReadinessResponse,
  SMSMatrixData,
} from "@/types/research";
import { SMS_RISK_COLORS, READINESS_LABEL_COLORS } from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

// ---------------------------------------------------------------------------
// SMS Heatmap Chart Builder
// ---------------------------------------------------------------------------

function buildSMSHeatmapOption(
  title: string,
  matrix: SMSMatrixData,
  posRow: number,
  posCol: number,
): Record<string, unknown> {
  return {
    title: {
      text: title,
      left: "center",
      textStyle: { color: "#1a1a1a", fontWeight: "bold", fontSize: 14 },
    },
    tooltip: {
      position: "top",
      formatter: (p: { data: number[] }) => {
        const [col, row, val] = p.data;
        const sev = matrix.severity_labels[row];
        const lik = matrix.likelihood_labels[col];
        const risk = matrix.risk_levels[val];
        return `<b>${sev}</b> x <b>${lik}</b><br/>Risk: <b>${risk}</b>`;
      },
    },
    grid: {
      left: "22%",
      right: "8%",
      top: 50,
      bottom: 60,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: matrix.likelihood_labels,
      name: "Likelihood",
      nameLocation: "middle",
      nameGap: 40,
      nameTextStyle: { color: "#1a1a1a", fontWeight: "bold" },
      axisLabel: { color: "#1a1a1a", fontSize: 10, rotate: 20 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: matrix.severity_labels,
      name: "Severity",
      nameLocation: "middle",
      nameGap: 80,
      nameTextStyle: { color: "#1a1a1a", fontWeight: "bold" },
      axisLabel: { color: "#1a1a1a", fontSize: 10 },
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
      textStyle: { color: "#1a1a1a" },
    },
    series: [
      {
        name: "Risk Matrix",
        type: "heatmap",
        data: matrix.data,
        label: {
          show: true,
          formatter: (p: { data: number[] }) => matrix.risk_levels[p.data[2]],
          color: "#1a1a1a",
          fontSize: 9,
          fontWeight: "bold",
        },
        itemStyle: { borderWidth: 1, borderColor: "#fff" },
      },
      {
        name: "Current Position",
        type: "scatter",
        data: [[posCol, posRow]],
        symbolSize: 22,
        itemStyle: {
          color: "#2c3e50",
          borderColor: "#fff",
          borderWidth: 3,
        },
        z: 10,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Modifier Waterfall Chart
// ---------------------------------------------------------------------------

function buildModifierWaterfallOption(
  baseScore: number,
  modifiers: { name: string; value: number }[],
  finalScore: number,
): Record<string, unknown> {
  const labels = ["Base", ...modifiers.map((m) => m.name), "Final"];
  const values = [baseScore, ...modifiers.map((m) => m.value), finalScore];
  const colors = values.map((v, i) => {
    if (i === 0 || i === values.length - 1) return SCIENTIFIC_COLORS.primary;
    return v >= 0 ? "#27ae60" : "#e74c3c";
  });

  return {
    title: {
      text: "Readiness Score Breakdown",
      left: "center",
      textStyle: { color: "#1a1a1a", fontWeight: "bold", fontSize: 14 },
    },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: { left: 60, right: 30, top: 50, bottom: 50, containLabel: true },
    xAxis: {
      type: "category",
      data: labels,
      axisLabel: { color: "#1a1a1a", fontSize: 11, rotate: 15 },
    },
    yAxis: {
      type: "value",
      name: "Score",
      min: 0,
      max: 100,
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    series: [
      {
        type: "bar",
        data: values.map((v, i) => ({
          value: i === 0 || i === values.length - 1 ? v : Math.abs(v),
          itemStyle: { color: colors[i] },
          label: {
            show: true,
            position: "top",
            formatter: i === 0 || i === values.length - 1 ? `${v.toFixed(0)}` : `${v >= 0 ? "+" : ""}${v.toFixed(1)}`,
            color: "#1a1a1a",
            fontWeight: "bold",
          },
        })),
        barWidth: "50%",
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function PhysiologicalReadinessPage() {
  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  // Vitals form state
  const [sbp, setSbp] = React.useState<string>("120");
  const [dbp, setDbp] = React.useState<string>("80");
  const [tempC, setTempC] = React.useState<string>("36.6");

  // Results state
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
      title="Physiological Readiness & SMS Risk Assessment"
      description="Blood pressure and body temperature integration with SMS-style risk matrices for EVA and military flight operations"
    >
      {/* Vitals Input Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-500" />
            Baseline Vitals Entry
          </CardTitle>
          <CardDescription>
            Enter resting blood pressure (mmHg) and oral/surface body temperature (C).
            These are integrated as bounded modifiers into the operational readiness model.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            <div>
              <Label htmlFor="sbp">Systolic BP (mmHg)</Label>
              <Input
                id="sbp"
                type="number"
                min={40}
                max={300}
                value={sbp}
                onChange={(e) => setSbp(e.target.value)}
                placeholder="120"
              />
            </div>
            <div>
              <Label htmlFor="dbp">Diastolic BP (mmHg)</Label>
              <Input
                id="dbp"
                type="number"
                min={20}
                max={200}
                value={dbp}
                onChange={(e) => setDbp(e.target.value)}
                placeholder="80"
              />
            </div>
            <div>
              <Label htmlFor="temp">Oral Temperature (C)</Label>
              <Input
                id="temp"
                type="number"
                min={25}
                max={45}
                step={0.1}
                value={tempC}
                onChange={(e) => setTempC(e.target.value)}
                placeholder="36.6"
              />
            </div>
            <Button onClick={handleAssess} disabled={loading} className="h-10">
              {loading ? "Assessing..." : "Assess Readiness"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <>
          {/* Readiness Score Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <Card>
              <CardContent className="pt-6 text-center">
                <div className="text-5xl font-bold" style={{ color: READINESS_LABEL_COLORS[result.readiness_label] || "#1a1a1a" }}>
                  {result.readiness_score.toFixed(0)}
                </div>
                <Badge
                  className="mt-2 text-lg px-4 py-1"
                  style={{
                    backgroundColor: READINESS_LABEL_COLORS[result.readiness_label] || "#888",
                    color: "#fff",
                  }}
                >
                  {result.readiness_label}
                </Badge>
                <p className="text-sm text-gray-600 mt-2">Fused Readiness Score</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-5 w-5 text-blue-500" />
                  <span className="font-semibold text-[#1a1a1a]">Blood Pressure</span>
                </div>
                <p className="text-lg font-bold text-[#1a1a1a]">{result.bp_classification ?? "N/A"}</p>
                <p className="text-sm text-[#2c3e50]">
                  Modifier: {result.bp_modifier != null ? `${result.bp_modifier >= 0 ? "+" : ""}${result.bp_modifier.toFixed(1)} pts` : "N/A"}
                </p>
                <p className="text-xs text-[#2c3e50] mt-1">{result.bp_rationale}</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 mb-2">
                  <Thermometer className="h-5 w-5 text-orange-500" />
                  <span className="font-semibold text-[#1a1a1a]">Body Temperature</span>
                </div>
                <p className="text-lg font-bold text-[#1a1a1a]">{result.temp_classification ?? "N/A"}</p>
                <p className="text-sm text-[#2c3e50]">
                  Modifier: {result.temp_modifier != null ? `${result.temp_modifier >= 0 ? "+" : ""}${result.temp_modifier.toFixed(1)} pts` : "N/A"}
                </p>
                <p className="text-xs text-[#2c3e50] mt-1">{result.temp_rationale}</p>
              </CardContent>
            </Card>
          </div>

          {/* Disqualifier Alerts */}
          {result.triggers.length > 0 && (
            <Card className="mt-6 border-red-300 bg-red-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <AlertTriangle className="h-5 w-5" />
                  Disqualifiers / Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {result.triggers.map((t, i) => (
                  <p key={i} className="text-red-700 font-medium mb-1">{t}</p>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Modifier Waterfall Chart */}
          <Card className="mt-6">
            <CardContent className="pt-6">
              <EChartsWrapper
                option={buildModifierWaterfallOption(
                  80,
                  result.modifiers.map((m) => ({ name: m.name, value: m.value })),
                  result.readiness_score,
                )}
                height={320}
              />
            </CardContent>
          </Card>

          {/* Dual SMS Matrices */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            {/* EVA SMS Matrix */}
            {result.eva_sms && result.eva_matrix && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-600" />
                    EVA Readiness SMS (ICAO Doc 9859)
                  </CardTitle>
                  <CardDescription>
                    Risk: <Badge style={{ backgroundColor: SMS_RISK_COLORS[result.eva_sms.risk_level] || "#888", color: "#fff" }}>
                      {result.eva_sms.risk_level}
                    </Badge>
                    {" "}{result.eva_sms.severity} / {result.eva_sms.likelihood}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <EChartsWrapper
                    option={buildSMSHeatmapOption(
                      "EVA Risk Matrix (ICAO Doc 9859)",
                      result.eva_matrix,
                      result.eva_matrix.severity_labels.indexOf(result.eva_sms.severity),
                      result.eva_matrix.likelihood_labels.indexOf(result.eva_sms.likelihood),
                    )}
                    height={380}
                  />
                  {result.eva_sms.disqualifiers.length > 0 && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                      <p className="font-semibold text-red-700 mb-1">EVA Disqualifiers:</p>
                      {result.eva_sms.disqualifiers.map((d, i) => (
                        <p key={i} className="text-sm text-red-600">{d}</p>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-[#2c3e50] mt-2">{result.eva_sms.rationale}</p>
                </CardContent>
              </Card>
            )}

            {/* Flight SMS Matrix */}
            {result.flight_sms && result.flight_matrix && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-amber-600" />
                    Military Flight SMS (MIL-STD-882E)
                  </CardTitle>
                  <CardDescription>
                    Risk: <Badge style={{ backgroundColor: SMS_RISK_COLORS[result.flight_sms.risk_level] || "#888", color: "#fff" }}>
                      {result.flight_sms.risk_level}
                    </Badge>
                    {" "}{result.flight_sms.severity} / {result.flight_sms.likelihood}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <EChartsWrapper
                    option={buildSMSHeatmapOption(
                      "Flight Risk Matrix (MIL-STD-882E)",
                      result.flight_matrix,
                      result.flight_matrix.severity_labels.indexOf(result.flight_sms.severity),
                      result.flight_matrix.likelihood_labels.indexOf(result.flight_sms.likelihood),
                    )}
                    height={380}
                  />
                  {result.flight_sms.disqualifiers.length > 0 && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
                      <p className="font-semibold text-red-700 mb-1">Flight Disqualifiers:</p>
                      {result.flight_sms.disqualifiers.map((d, i) => (
                        <p key={i} className="text-sm text-red-600">{d}</p>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-[#2c3e50] mt-2">{result.flight_sms.rationale}</p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Scientific References */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Scientific References
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-[#2c3e50] space-y-1">
              <p>Porta, A., et al. (2012). HP and SAP variability complexity provide complementary information. <i>J Appl Physiol, 113</i>(12). PMID: 23104699</p>
              <p>Lucini, D., Solaro, N., & Pagani, M. (2014). Autonomic indices help identify hypertension. <i>J Hypertens, 32</i>(2). PMID: 24232167</p>
              <p>Zhang, R., et al. (2020). Autonomic pattern in hypertension based on short-term HRV. <i>Biomed Tech, 65</i>(4). PMID: 32769220</p>
              <p>Crowe, M., et al. (2025). Resting HR and SBP predict heat tolerance in military. <i>Medicina, 61</i>(6). DOI: 10.3390/medicina61061111</p>
              <p>Kim, S., & Lee, J.-Y. (2017). Prediction of body core temperature with HRV. Semantic Scholar: 6f60ddec.</p>
              <p>Zhang, Z., et al. (2025). Physiological monitoring models in military domain. DOI: 10.1109/ICCNEA66167.2025.11211893</p>
              <p>ICAO. (2018). <i>Safety Management Manual</i> (Doc 9859, 4th ed.).</p>
              <p>US DoD. (2012). <i>MIL-STD-882E: Standard Practice for System Safety</i>.</p>
            </CardContent>
          </Card>
        </>
      )}
    </PageWrapper>
  );
}
