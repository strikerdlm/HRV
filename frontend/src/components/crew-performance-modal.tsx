// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Heart,
  Info,
  Layers,
  Plane,
  Shield,
  Thermometer,
  Zap,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { EChartsWrapper } from "@/components/charts";
import { submitVitalsAndAssess } from "@/lib/research-api";
import type {
  EnhancedReadinessResponse,
  SMSMatrixData,
} from "@/types/research";
import { SMS_RISK_COLORS, READINESS_LABEL_COLORS } from "@/types/research";

// ---------------------------------------------------------------------------
// Activity-Severity Mapping
// ---------------------------------------------------------------------------

const ACTIVITY_SEVERITY_BUMP: Record<string, number> = {
  emergency: 20,
  medical: 10,
  exercise: 10,
  experiment: 0,
  maintenance: 0,
  work: 0,
  communication: 0,
  meal: -5,
  personal: -5,
  sleep: -5,
};

const ACTIVITY_RISK_EXPLANATION: Record<string, string> = {
  emergency: "Life-critical activity with zero margin for error. Highest scrutiny applied.",
  medical: "Physical exertion or precision required. Elevated physiological demand.",
  exercise: "Cardiovascular stress during exercise increases vulnerability to underlying issues.",
  experiment: "Standard operational risk. Normal scrutiny level.",
  maintenance: "Standard operational risk. Normal scrutiny level.",
  work: "Low physical risk. Routine desk/planning work.",
  communication: "Low physical risk. Communication tasks.",
  meal: "Low-risk rest activity. Reduced scrutiny appropriate.",
  personal: "Low-risk personal time. Reduced scrutiny appropriate.",
  sleep: "Rest period. Reduced scrutiny appropriate.",
};

// ---------------------------------------------------------------------------
// Full-Size Interactive SMS Heatmap (NO title per project plot rules)
// ---------------------------------------------------------------------------

function buildFullHeatmap(
  matrix: SMSMatrixData,
  posRow: number,
  posCol: number,
  xLabel: string,
  yLabel: string,
): Record<string, unknown> {
  return {
    tooltip: {
      position: "top",
      formatter: (p: { data: number[] }) => {
        const [col, row, val] = p.data;
        const sev = matrix.severity_labels[row];
        const lik = matrix.likelihood_labels[col];
        const risk = matrix.risk_levels[val];
        const isPosition = row === posRow && col === posCol;
        return `<div style="padding:4px 8px">
          <b style="font-size:13px">${sev}</b> x <b>${lik}</b><br/>
          <span style="font-size:14px;font-weight:bold;color:${matrix.risk_colors[val]}">${risk}</span>
          ${isPosition ? '<br/><b style="color:#2c3e50">Current crew position</b>' : ''}
        </div>`;
      },
    },
    grid: { left: 90, right: 20, top: 15, bottom: 65, containLabel: true },
    xAxis: {
      type: "category",
      data: matrix.likelihood_labels,
      name: xLabel,
      nameLocation: "middle",
      nameGap: 42,
      nameTextStyle: { color: "#1a1a1a", fontWeight: "bold", fontSize: 11 },
      axisLabel: { color: "#1a1a1a", fontSize: 10, rotate: 15 },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: matrix.severity_labels,
      name: yLabel,
      nameLocation: "middle",
      nameGap: 72,
      nameTextStyle: { color: "#1a1a1a", fontWeight: "bold", fontSize: 11 },
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
      textStyle: { color: "#1a1a1a", fontSize: 10 },
      itemWidth: 16,
      itemHeight: 16,
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
          fontSize: 10,
          fontWeight: "bold",
        },
        itemStyle: { borderWidth: 2, borderColor: "#fff" },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)" },
        },
      },
      {
        name: "Crew Position",
        type: "scatter",
        data: [[posCol, posRow]],
        symbolSize: 26,
        symbol: "circle",
        itemStyle: {
          color: "#2c3e50",
          borderColor: "#fff",
          borderWidth: 4,
          shadowBlur: 8,
          shadowColor: "rgba(0,0,0,0.4)",
        },
        z: 10,
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Collapsible Section
// ---------------------------------------------------------------------------

function CollapsibleSection({
  title,
  icon,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(defaultOpen);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-2 p-3 hover:bg-muted/50 transition-colors text-left"
        onClick={() => setOpen(!open)}
        type="button"
      >
        {icon}
        <span className="text-sm font-semibold flex-1">{title}</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
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
            <div className="p-4 pt-0 border-t">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Model Explainer — plain-English explanation of how the decision is made
// ---------------------------------------------------------------------------

function ModelExplainer({
  member,
  assessment,
  actBump,
  adjustedReadiness,
  readinessLabel,
}: {
  member: CrewMemberForModal;
  assessment: EnhancedReadinessResponse | null;
  actBump: number;
  adjustedReadiness: number;
  readinessLabel: string;
}) {
  const steps = [
    {
      label: "Step 1: Base Score",
      value: "80 / 100",
      explanation:
        "We start with a base readiness score of 80. This is the default when the SAFTE fatigue model and HRV recovery scores have not been computed yet. In production, this combines 65% sleep/fatigue (SAFTE model) and 35% HRV recovery.",
    },
    {
      label: "Step 2: Blood Pressure Check",
      value: assessment
        ? `${assessment.bp_classification ?? "Unknown"} (${assessment.bp_modifier != null ? `${assessment.bp_modifier >= 0 ? "+" : ""}${assessment.bp_modifier.toFixed(1)}` : "0"} pts)`
        : "Awaiting data...",
      explanation:
        "We classify resting blood pressure using ACC/AHA 2017 guidelines. Optimal BP (90-120/60-80) earns +2 points. Stage 2 hypertension (>140/90) costs -4 points and is a hard disqualifier for EVA and flight. Hypotension (<90/60) flags G-LOC risk for pilots.",
    },
    {
      label: "Step 3: Temperature Check",
      value: assessment
        ? `${assessment.temp_classification ?? "Unknown"} (${assessment.temp_modifier != null ? `${assessment.temp_modifier >= 0 ? "+" : ""}${assessment.temp_modifier.toFixed(1)}` : "0"} pts)`
        : "Awaiting data...",
      explanation:
        "Oral body temperature is checked against clinical ranges. Normal (36.1-37.2 C) = no change. Fever (>38.3 C) costs -3 points and disqualifies for EVA/flight. Even a low-grade elevation (37.3-37.7 C) earns a small -1 penalty as a caution flag.",
    },
    {
      label: "Step 4: Activity Adjustment",
      value: actBump !== 0
        ? `${actBump > 0 ? "-" : "+"}${Math.abs(actBump)} pts (${member.activityCategory ?? "work"})`
        : "No adjustment (standard activity)",
      explanation:
        `The planned activity type changes how strict the assessment is. Emergency tasks add a -20 point penalty because any impairment during a crisis is catastrophic. Exercise/medical tasks add -10 (higher physical demand). Rest activities like meals or sleep reduce severity by +5 (lower risk). Current: "${member.activityCategory ?? "work"}" = ${actBump === 0 ? "no" : actBump > 0 ? "stricter" : "relaxed"} scrutiny.`,
    },
    {
      label: "Step 5: Final Decision",
      value: `${adjustedReadiness.toFixed(0)} / 100 = ${readinessLabel}`,
      explanation:
        readinessLabel === "GO"
          ? "Score >= 85: Crew member is cleared for the planned activity. All vital signs within acceptable ranges and no disqualifying flags."
          : readinessLabel === "CAUTION"
          ? "Score 70-84: Crew member may proceed with heightened monitoring. Some risk factors are present but not disqualifying. Flight surgeon should review."
          : readinessLabel === "MARGINAL"
          ? "Score 50-69: Significant risk factors detected. Activity should be reconsidered or postponed. Medical review strongly recommended."
          : "Score < 50: Crew member is NOT cleared for this activity. One or more hard disqualifiers are present, or cumulative risk is too high.",
    },
  ];

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        The readiness score is built step-by-step. Each factor is a bounded modifier, meaning no single factor can dominate the outcome. The final score is always between 0 and 100.
      </p>

      {steps.map((step, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          className="flex gap-3"
        >
          <div className="flex flex-col items-center">
            <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold text-white ${
              i === steps.length - 1
                ? readinessLabel === "GO" ? "bg-green-500"
                  : readinessLabel === "CAUTION" ? "bg-yellow-500"
                  : readinessLabel === "MARGINAL" ? "bg-orange-500"
                  : "bg-red-500"
                : "bg-primary"
            }`}>
              {i + 1}
            </div>
            {i < steps.length - 1 && <div className="w-0.5 h-full bg-border mt-1" />}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{step.label}</p>
              <Badge variant="outline" className="text-xs">{step.value}</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{step.explanation}</p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface CrewMemberForModal {
  id: string;
  name: string;
  role: string;
  status: string;
  ihpiScore: number;
  fatigueLevel: number;
  sleepDebt: number;
  readinessScore: number;
  sbp?: number;
  dbp?: number;
  tempC?: number;
  currentActivity?: string;
  activityCategory?: string;
}

interface CrewPerformanceModalProps {
  member: CrewMemberForModal | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CrewPerformanceModal({
  member,
  open,
  onOpenChange,
}: CrewPerformanceModalProps) {
  const [assessment, setAssessment] = React.useState<EnhancedReadinessResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!open || !member) {
      setAssessment(null);
      return;
    }

    const fetchAssessment = async () => {
      setLoading(true);
      try {
        const data = await submitVitalsAndAssess(member.id, {
          sbp_mmhg: member.sbp ?? 120,
          dbp_mmhg: member.dbp ?? 80,
          temperature_c: member.tempC ?? 36.6,
        });
        setAssessment(data);
      } catch (err) {
        console.error("Failed to fetch assessment:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAssessment();
  }, [open, member]);

  if (!member) return null;

  const actBump = ACTIVITY_SEVERITY_BUMP[member.activityCategory ?? "work"] ?? 0;
  const adjustedReadiness = Math.max(0, Math.min(100, member.readinessScore - actBump));
  const readinessLabel =
    adjustedReadiness >= 85 ? "GO"
    : adjustedReadiness >= 70 ? "CAUTION"
    : adjustedReadiness >= 50 ? "MARGINAL"
    : "NO-GO";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[95vh] overflow-y-auto p-0">
        {/* Header Banner */}
        <div
          className="p-6 rounded-t-lg"
          style={{ backgroundColor: READINESS_LABEL_COLORS[readinessLabel] || "#888" }}
        >
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-white">
              <div className="h-12 w-12 rounded-full bg-white/20 flex items-center justify-center backdrop-blur">
                <span className="text-lg font-bold text-white">{member.role}</span>
              </div>
              <div>
                <span className="text-xl">{member.name}</span>
                <Badge className="ml-2 bg-white/20 text-white border-white/30 capitalize">
                  {member.status.replace("_", " ")}
                </Badge>
              </div>
              <div className="ml-auto text-right">
                <div className="text-5xl font-bold text-white">{adjustedReadiness.toFixed(0)}</div>
                <div className="text-lg font-bold text-white/90">{readinessLabel}</div>
              </div>
            </DialogTitle>
            <DialogDescription className="text-white/80">
              Human Performance Assessment
              {member.currentActivity && (
                <> | Activity: <strong className="text-white">{member.currentActivity}</strong></>
              )}
              {actBump !== 0 && (
                <> | Severity adjustment: {actBump > 0 ? `-${actBump}` : `+${Math.abs(actBump)}`} pts</>
              )}
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="p-6 space-y-5">
          {/* Performance Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Activity, label: "IHPI Score", value: `${member.ihpiScore}%`, color: "text-blue-500", pct: member.ihpiScore },
              { icon: Zap, label: "Fatigue Level", value: `${member.fatigueLevel}%`, color: "text-yellow-500", pct: 100 - member.fatigueLevel },
              { icon: Heart, label: "Sleep Debt", value: `${member.sleepDebt}h`, color: "text-red-500", pct: Math.max(0, 100 - member.sleepDebt * 20) },
              { icon: Shield, label: "Readiness", value: `${member.readinessScore}%`, color: "text-green-500", pct: member.readinessScore },
            ].map(({ icon: Icon, label, value, color, pct }) => (
              <div key={label} className="p-4 rounded-lg border text-center">
                <Icon className={`h-5 w-5 mx-auto mb-2 ${color}`} />
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-xl font-bold mt-1">{value}</p>
                <Progress value={pct} className="h-1.5 mt-2" />
              </div>
            ))}
          </div>

          {/* Vitals Modifiers */}
          {assessment && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg border bg-blue-50/50">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="h-5 w-5 text-blue-500" />
                  <span className="font-semibold">Blood Pressure</span>
                  <Badge variant="outline" className="ml-auto">
                    {assessment.bp_modifier != null
                      ? `${assessment.bp_modifier >= 0 ? "+" : ""}${assessment.bp_modifier.toFixed(1)} pts`
                      : "0 pts"}
                  </Badge>
                </div>
                <p className="text-lg font-bold">{assessment.bp_classification ?? "N/A"}</p>
                <p className="text-xs text-muted-foreground mt-1">{assessment.bp_rationale}</p>
              </div>
              <div className="p-4 rounded-lg border bg-orange-50/50">
                <div className="flex items-center gap-2 mb-2">
                  <Thermometer className="h-5 w-5 text-orange-500" />
                  <span className="font-semibold">Body Temperature</span>
                  <Badge variant="outline" className="ml-auto">
                    {assessment.temp_modifier != null
                      ? `${assessment.temp_modifier >= 0 ? "+" : ""}${assessment.temp_modifier.toFixed(1)} pts`
                      : "0 pts"}
                  </Badge>
                </div>
                <p className="text-lg font-bold">{assessment.temp_classification ?? "N/A"}</p>
                <p className="text-xs text-muted-foreground mt-1">{assessment.temp_rationale}</p>
              </div>
            </div>
          )}

          {/* Disqualifier Alerts */}
          {assessment && assessment.triggers.length > 0 && (
            <div className="p-4 bg-red-50 border-2 border-red-300 rounded-lg">
              <p className="font-bold text-red-700 flex items-center gap-2 mb-2">
                <AlertTriangle className="h-5 w-5" />
                Hard Disqualifiers Detected
              </p>
              <p className="text-xs text-red-600 mb-2">
                The following conditions automatically set the risk level to the highest category, regardless of other factors.
              </p>
              {assessment.triggers.map((t, i) => (
                <div key={i} className="flex items-start gap-2 mt-1">
                  <ArrowRight className="h-3 w-3 mt-0.5 text-red-500 shrink-0" />
                  <p className="text-sm text-red-700">{t}</p>
                </div>
              ))}
            </div>
          )}

          <Separator />

          {/* SMS Risk Matrices — Interactive, Full Size, NO titles on plots */}
          <CollapsibleSection
            title="Safety Risk Assessment — ICAO Doc 9859 (EVA)"
            icon={<Shield className="h-5 w-5 text-blue-600" />}
            defaultOpen={true}
          >
            {assessment?.eva_sms && assessment?.eva_matrix ? (
              <>
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  <span className="text-sm">Risk Index:</span>
                  <Badge
                    className="text-sm px-3 py-1"
                    style={{
                      backgroundColor: SMS_RISK_COLORS[assessment.eva_sms.risk_level] || "#888",
                      color: "#fff",
                    }}
                  >
                    {assessment.eva_sms.risk_level}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Severity: {assessment.eva_sms.severity} | Probability: {assessment.eva_sms.likelihood}
                  </span>
                </div>
                <EChartsWrapper
                  option={buildFullHeatmap(
                    assessment.eva_matrix,
                    assessment.eva_matrix.severity_labels.indexOf(assessment.eva_sms.severity),
                    assessment.eva_matrix.likelihood_labels.indexOf(assessment.eva_sms.likelihood),
                    "Safety Risk Probability",
                    "Severity of Occurrence",
                  )}
                  height={380}
                />
                {assessment.eva_sms.disqualifiers.length > 0 && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                    <p className="text-xs font-semibold text-red-700 mb-1">Disqualifiers:</p>
                    {assessment.eva_sms.disqualifiers.map((d, i) => (
                      <p key={i} className="text-xs text-red-600">{d}</p>
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-muted-foreground mt-2">
                  Ref: ICAO. (2018). Safety Management Manual (Doc 9859, 4th ed.), Table 2-13.
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">Loading...</p>
            )}
          </CollapsibleSection>

          <CollapsibleSection
            title="Mishap Risk Assessment — MIL-STD-882E (Flight)"
            icon={<Plane className="h-5 w-5 text-amber-600" />}
            defaultOpen={true}
          >
            {assessment?.flight_sms && assessment?.flight_matrix ? (
              <>
                <div className="flex items-center gap-2 mb-3 flex-wrap">
                  <span className="text-sm">Risk Assessment Code:</span>
                  <Badge
                    className="text-sm px-3 py-1"
                    style={{
                      backgroundColor: SMS_RISK_COLORS[assessment.flight_sms.risk_level] || "#888",
                      color: "#fff",
                    }}
                  >
                    {assessment.flight_sms.risk_level}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    Severity: {assessment.flight_sms.severity} | Probability: {assessment.flight_sms.likelihood}
                  </span>
                </div>
                <EChartsWrapper
                  option={buildFullHeatmap(
                    assessment.flight_matrix,
                    assessment.flight_matrix.severity_labels.indexOf(assessment.flight_sms.severity),
                    assessment.flight_matrix.likelihood_labels.indexOf(assessment.flight_sms.likelihood),
                    "Mishap Probability Level",
                    "Mishap Severity Category",
                  )}
                  height={350}
                />
                {assessment.flight_sms.disqualifiers.length > 0 && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                    <p className="text-xs font-semibold text-red-700 mb-1">Disqualifiers:</p>
                    {assessment.flight_sms.disqualifiers.map((d, i) => (
                      <p key={i} className="text-xs text-red-600">{d}</p>
                    ))}
                  </div>
                )}
                <p className="text-[10px] text-muted-foreground mt-2">
                  Ref: US DoD. (2012). MIL-STD-882E, Tables I-III.
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">Loading...</p>
            )}
          </CollapsibleSection>

          <CollapsibleSection
            title="Human System Risk — NASA HRP LxC (Exploration)"
            icon={<Zap className="h-5 w-5 text-purple-600" />}
            defaultOpen={false}
          >
            {assessment?.nasa_hrp_matrix ? (
              <>
                <p className="text-xs text-muted-foreground mb-3">
                  The NASA Human Research Program manages risks to crew health and performance
                  during exploration missions using a 5x5 Likelihood x Consequence (LxC)
                  framework. Risks are classified as Accepted, Controlled, Watched, or
                  Uncontrolled based on current mitigation effectiveness.
                </p>
                <EChartsWrapper
                  option={buildFullHeatmap(
                    assessment.nasa_hrp_matrix,
                    2, // default center position
                    2,
                    "Likelihood",
                    "Consequence",
                  )}
                  height={380}
                />
                <p className="text-[10px] text-muted-foreground mt-2">
                  Ref: Antonsen, E. L., et al. (2022). Updates to the NASA Human System Risk Board Process. <i>NPJ Microgravity, 8</i>, 27. DOI: 10.1038/s41526-022-00213-2 | NASA Human Research Roadmap: humanresearchroadmap.nasa.gov
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground py-4 text-center">Loading...</p>
            )}
          </CollapsibleSection>

          <Separator />

          {/* How the Model Works — plain-English step-by-step */}
          <CollapsibleSection
            title="How This Decision Is Made (Model Explained)"
            icon={<BookOpen className="h-5 w-5 text-primary" />}
            defaultOpen={false}
          >
            <ModelExplainer
              member={member}
              assessment={assessment}
              actBump={actBump}
              adjustedReadiness={adjustedReadiness}
              readinessLabel={readinessLabel}
            />
          </CollapsibleSection>

          {/* Activity Risk Context */}
          <CollapsibleSection
            title="Activity Risk Context"
            icon={<Layers className="h-5 w-5 text-purple-500" />}
            defaultOpen={false}
          >
            <p className="text-sm text-muted-foreground mb-3">
              Different activities carry different inherent risk levels. The model adjusts the readiness threshold
              based on what the crew member is scheduled to do. Higher-risk activities demand a higher readiness score to pass.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(ACTIVITY_SEVERITY_BUMP).map(([category, bump]) => {
                const isActive = category === (member.activityCategory ?? "work");
                return (
                  <div
                    key={category}
                    className={`flex items-center gap-2 p-2 rounded text-sm ${
                      isActive ? "bg-primary/10 border border-primary/30 font-semibold" : "bg-muted/30"
                    }`}
                  >
                    <span className="capitalize flex-1">{category}</span>
                    <Badge variant={bump > 0 ? "destructive" : bump < 0 ? "secondary" : "outline"} className="text-xs">
                      {bump > 0 ? `-${bump}` : bump < 0 ? `+${Math.abs(bump)}` : "0"} pts
                    </Badge>
                    {isActive && <ArrowRight className="h-3 w-3 text-primary" />}
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              {ACTIVITY_RISK_EXPLANATION[member.activityCategory ?? "work"]}
            </p>
          </CollapsibleSection>

          {/* Decision Scale Legend */}
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: "GO", range: "85-100", color: "#27ae60", desc: "Cleared for activity" },
              { label: "CAUTION", range: "70-84", color: "#f39c12", desc: "Proceed with monitoring" },
              { label: "MARGINAL", range: "50-69", color: "#e67e22", desc: "Reconsider activity" },
              { label: "NO-GO", range: "0-49", color: "#e74c3c", desc: "Not cleared" },
            ].map((item) => (
              <div key={item.label} className="text-center p-2 rounded-lg border">
                <div
                  className="text-sm font-bold mb-1"
                  style={{ color: item.color }}
                >
                  {item.label}
                </div>
                <p className="text-xs text-muted-foreground">{item.range}</p>
                <p className="text-[10px] text-muted-foreground">{item.desc}</p>
              </div>
            ))}
          </div>

          {/* References */}
          <div className="text-[10px] text-muted-foreground border-t pt-3 space-y-0.5">
            <p>ICAO. (2018). Safety Management Manual (Doc 9859, 4th ed.). | US DoD. (2012). MIL-STD-882E.</p>
            <p>Porta et al. (2012). PMID: 23104699 | Crowe et al. (2025). DOI: 10.3390/medicina61061111</p>
            <p>Kim & Lee (2017). Core temp + HRV | Zhang et al. (2025). DOI: 10.1109/ICCNEA66167.2025.11211893</p>
          </div>
        </div>

        {loading && (
          <div className="absolute inset-0 bg-background/80 flex items-center justify-center z-50 rounded-lg">
            <div className="text-center">
              <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-sm text-muted-foreground mt-2">Loading SMS assessment...</p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
