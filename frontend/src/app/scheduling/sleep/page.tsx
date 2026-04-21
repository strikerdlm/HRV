// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { AlertTriangle, Bed, CheckCircle2, Moon, RefreshCw, ShieldAlert } from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { SleepDebtCurve } from "@/components/sleep/sleep-charts";
import {
  SLEEP_THRESHOLDS,
  decisionColour,
  formatHours,
  formatSpO2,
  screeningColour,
  type SleepDebtTrendResponse,
  type SleepSummary,
} from "@/lib/sleep-metrics";
import { useAppStore } from "@/lib/store";

const DEFAULT_USER_ID = "demo-user";

export default function OperationalSleepPage() {
  const userId = useAppStore((s: { userId?: string | null }) => s.userId ?? DEFAULT_USER_ID);
  const [summary, setSummary] = React.useState<SleepSummary | null>(null);
  const [debtTrend, setDebtTrend] = React.useState<SleepDebtTrendResponse | null>(null);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);

  const apiBase = React.useMemo(() => {
    if (typeof window === "undefined") return "";
    return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8180";
  }, []);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const uid = encodeURIComponent(userId);
      const [rsum, rdebt] = await Promise.all([
        fetch(`${apiBase}/api/research/garmin/sleep-summary/${uid}?days=30`),
        fetch(`${apiBase}/api/research/garmin/sleep-debt-trend/${uid}?days=30`),
      ]);
      if (!rsum.ok) throw new Error(`summary HTTP ${rsum.status}`);
      if (!rdebt.ok) throw new Error(`debt HTTP ${rdebt.status}`);
      setSummary(await rsum.json());
      setDebtTrend(await rdebt.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sleep gate data");
    } finally {
      setLoading(false);
    }
  }, [apiBase, userId]);

  React.useEffect(() => {
    load();
  }, [load]);

  const readiness = summary?.readiness;
  const debt7d = summary?.debt_7d;
  const spo2 = summary?.spo2_screen_7d;
  const reg = summary?.regularity_14d;
  const lastDur = readiness?.inputs?.last_sleep_hours as number | null | undefined;

  const debtGauge = React.useMemo(
    () => buildDebtGauge(debt7d?.cumulative_debt_hours ?? null),
    [debt7d],
  );
  const last7Bar = React.useMemo(
    () => buildLast7DurationBar(debtTrend?.series ?? []),
    [debtTrend],
  );
  const spo2Bar = React.useMemo(
    () => buildSpO2Bar(debtTrend?.series ?? [], summary),
    [debtTrend, summary],
  );

  return (
    <PageWrapper
      title="Pre-flight Sleep Gate (Operational)"
      description={
        "Last-night duration, 7-night sleep debt, Sleep Regularity Index, and a SpO₂ screening " +
        "proxy feed the operational decision. Screening only — never apnea diagnosis."
      }
    >
      <div className="space-y-4">
        {/* ------------------------------------------------------- banner */}
        {readiness && (
          <GateBanner decision={readiness.decision} reasons={readiness.reasons} />
        )}

        {/* ------------------------------------------------------- refresh */}
        <Card>
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-2 text-sm">
              <Moon className="h-4 w-4" />
              <span className="font-medium">Gate inputs refresh from latest Garmin sync</span>
            </div>
            <Button size="sm" variant="outline" onClick={load} disabled={loading}>
              <RefreshCw className={"h-4 w-4 " + (loading ? "animate-spin" : "")} />
            </Button>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-red-500">
            <CardContent className="flex items-center gap-2 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4" /> {error}
            </CardContent>
          </Card>
        )}

        {/* ------------------------------------------------------- KPIs */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KPI
            label="Last night"
            value={formatHours(lastDur ?? null)}
            hint={`Hard floor ${SLEEP_THRESHOLDS.hardFloorHours} h · accept ≥${SLEEP_THRESHOLDS.minAcceptableHours} h`}
            colour={
              lastDur == null
                ? undefined
                : lastDur < SLEEP_THRESHOLDS.hardFloorHours
                  ? SCIENTIFIC_COLORS.danger
                  : lastDur < SLEEP_THRESHOLDS.minAcceptableHours
                    ? SCIENTIFIC_COLORS.warning
                    : SCIENTIFIC_COLORS.success
            }
          />
          <KPI
            label="7-night debt"
            value={formatHours(debt7d?.cumulative_debt_hours ?? null)}
            hint={`CAUTION ≥${SLEEP_THRESHOLDS.debtCautionHours7d}h · NO-GO ≥${SLEEP_THRESHOLDS.debtNoGoHours7d}h`}
          />
          <KPI
            label="Sleep Regularity Idx"
            value={reg?.sri_percent != null ? `${reg.sri_percent.toFixed(0)}%` : "—"}
            hint={`CAUTION < ${SLEEP_THRESHOLDS.sriIrregularCaution}%`}
            colour={
              reg?.sri_percent == null
                ? undefined
                : reg.sri_percent < SLEEP_THRESHOLDS.sriIrregularCaution
                  ? SCIENTIFIC_COLORS.warning
                  : reg.sri_percent < SLEEP_THRESHOLDS.sriModerateRegularity
                    ? SCIENTIFIC_COLORS.primary
                    : SCIENTIFIC_COLORS.success
            }
          />
          <KPI
            label="Low-SpO₂ nights (7d)"
            value={spo2?.low_spo2_nights_7d != null ? `${spo2.low_spo2_nights_7d} / 7` : "—"}
            hint={`<${SLEEP_THRESHOLDS.spo2LowThreshold}% — screening only`}
            colour={spo2 ? screeningColour(spo2.band) : undefined}
          />
        </div>

        {/* ------------------------------------------------------- charts */}
        <div className="grid gap-3 lg:grid-cols-3">
          <Card>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">Cumulative sleep debt (7-night)</CardTitle>
              <CardDescription className="text-xs">
                Cumulative deficit vs {SLEEP_THRESHOLDS.typicalTargetHours} h target over the last 7
                nights. Gauge bands match the operational gate thresholds.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EChartsWrapper option={debtGauge} height={260} showToolbox={false} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">Last 7 nights — duration</CardTitle>
              <CardDescription className="text-xs">
                Bars = nightly hours; dashed lines = acceptable floor (
                {SLEEP_THRESHOLDS.minAcceptableHours} h) and hard gate (
                {SLEEP_THRESHOLDS.hardFloorHours} h).
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EChartsWrapper option={last7Bar} height={260} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">SpO₂ screening (last 7 nights)</CardTitle>
              <CardDescription className="text-xs">
                Bars = nightly average SpO₂; red highlight if below{" "}
                {SLEEP_THRESHOLDS.spo2LowThreshold}%. <strong>Screening only — not apnea
                diagnosis.</strong>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EChartsWrapper option={spo2Bar} height={260} />
            </CardContent>
          </Card>
        </div>

        {/* ------------------------------------------------------- debt curve */}
        {debtTrend && (
          <Card>
            <CardContent className="pt-4">
              <SleepDebtCurve series={debtTrend.series} />
            </CardContent>
          </Card>
        )}

        {/* ------------------------------------------------------- readiness details */}
        {readiness && (
          <Card>
            <CardHeader className="pb-1">
              <CardTitle className="text-sm">Readiness evaluation detail</CardTitle>
            </CardHeader>
            <CardContent>
              <DecisionTable readiness={readiness} />
            </CardContent>
          </Card>
        )}

        {/* ------------------------------------------------------- disclosure */}
        <Card className="border-amber-500/40 bg-amber-50/60">
          <CardContent className="flex items-start gap-2 py-3 text-xs text-amber-900">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              Garmin-derived sleep metrics differ from polysomnography by clinically meaningful
              margins (Lee et al. 2025, DOI 10.5664/jcsm.11460; Schyvens et al. 2024, DOI
              10.2196/52192). This gate is designed for <strong>operational tracking</strong>, not
              diagnosis. Sleep apnea, AHI, RDI, or any clinical sleep-disorder classification are
              out of scope. Any concerning pattern should be escalated to a flight surgeon and, if
              warranted, a clinical polysomnogram.
            </span>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

// ---------------------------------------------------------------------------
// Chart builders
// ---------------------------------------------------------------------------

function buildDebtGauge(debt: number | null): Record<string, unknown> {
  const value = debt != null && Number.isFinite(debt) ? Math.min(debt, 12) : 0;
  return {
    tooltip: { formatter: "{b}: {c} h" },
    series: [
      {
        type: "gauge",
        min: 0,
        max: 12,
        startAngle: 210,
        endAngle: -30,
        center: ["50%", "62%"],
        radius: "80%",
        progress: { show: true, width: 16 },
        pointer: { length: "65%", width: 5 },
        axisLine: {
          lineStyle: {
            width: 16,
            color: [
              [SLEEP_THRESHOLDS.debtCautionHours7d / 12, SCIENTIFIC_COLORS.success],
              [SLEEP_THRESHOLDS.debtNoGoHours7d / 12, SCIENTIFIC_COLORS.warning],
              [1, SCIENTIFIC_COLORS.danger],
            ],
          },
        },
        axisTick: { show: false },
        splitLine: { length: 8, lineStyle: { width: 2, color: "#ffffff" } },
        axisLabel: { color: "#7f8c8d", fontSize: 9, distance: -22 },
        detail: {
          valueAnimation: true,
          formatter: (v: number) => (debt == null ? "—" : `${v.toFixed(1)} h`),
          fontSize: 22,
          offsetCenter: [0, "30%"],
          color: SCIENTIFIC_COLORS.trend,
        },
        title: { show: false },
        data: [{ value, name: "Debt" }],
      },
    ],
  };
}

function buildLast7DurationBar(
  series: Array<{ metric_date: string; sleep_duration_hours: number | null }>,
): Record<string, unknown> {
  const last7 = series.slice(-7);
  const xs = last7.map((p) => p.metric_date.slice(5));
  const ys = last7.map((p) => p.sleep_duration_hours);
  const colours = ys.map((v) => {
    if (v == null) return "#bdc3c7";
    if (v < SLEEP_THRESHOLDS.hardFloorHours) return SCIENTIFIC_COLORS.danger;
    if (v < SLEEP_THRESHOLDS.minAcceptableHours) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.success;
  });

  return {
    grid: { left: 50, right: 25, top: 30, bottom: 40, containLabel: true },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : `${v.toFixed(1)} h`),
    },
    xAxis: {
      type: "category",
      data: xs,
      axisLabel: { fontSize: 9 },
    },
    yAxis: {
      type: "value",
      name: "Hours",
      min: 0,
      max: 11,
      axisLabel: { fontSize: 9 },
    },
    series: [
      {
        type: "bar",
        data: ys.map((v, i) => ({ value: v, itemStyle: { color: colours[i] } })),
        barMaxWidth: 32,
        markLine: {
          silent: true,
          symbol: "none",
          data: [
            {
              yAxis: SLEEP_THRESHOLDS.minAcceptableHours,
              lineStyle: { color: SCIENTIFIC_COLORS.warning, type: "dashed" },
              label: { formatter: "Accept 6 h", position: "insideEndTop", fontSize: 9 },
            },
            {
              yAxis: SLEEP_THRESHOLDS.hardFloorHours,
              lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dashed" },
              label: { formatter: "Floor 5 h", position: "insideEndTop", fontSize: 9 },
            },
          ],
        },
      },
    ],
  };
}

function buildSpO2Bar(
  series: Array<{ metric_date: string }>,
  summary: SleepSummary | null,
): Record<string, unknown> {
  const last7 = series.slice(-7);
  // SpO2 comes from summary (we don't have trend data in that endpoint);
  // show the mean as an indicator band plus the low-night count as a callout.
  const mean = summary?.spo2_screen_7d?.mean_spo2 ?? null;
  const low = summary?.spo2_screen_7d?.low_spo2_nights_7d ?? 0;

  return {
    grid: { left: 50, right: 25, top: 30, bottom: 40, containLabel: true },
    title: {
      text: `${low} low night${low === 1 ? "" : "s"} · mean ${formatSpO2(mean)}`,
      left: "center",
      top: 4,
      textStyle: { fontSize: 11 },
    },
    tooltip: { show: false },
    xAxis: {
      type: "category",
      data: last7.map((p) => p.metric_date.slice(5)),
      axisLabel: { fontSize: 9 },
    },
    yAxis: {
      type: "value",
      name: "SpO₂ (%)",
      min: 85,
      max: 100,
      axisLabel: { fontSize: 9 },
    },
    series: [
      {
        type: "bar",
        data: last7.map(() => mean ?? 0),
        itemStyle: {
          color: mean != null && mean < SLEEP_THRESHOLDS.spo2LowThreshold
            ? SCIENTIFIC_COLORS.danger
            : SCIENTIFIC_COLORS.primary,
          opacity: 0.5,
        },
        barMaxWidth: 32,
        silent: true,
        markLine: {
          silent: true,
          symbol: "none",
          data: [
            {
              yAxis: SLEEP_THRESHOLDS.spo2LowThreshold,
              lineStyle: { color: SCIENTIFIC_COLORS.danger, type: "dashed" },
              label: { formatter: "Low <92%", position: "insideEndTop", fontSize: 9 },
            },
          ],
        },
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Inline components
// ---------------------------------------------------------------------------

function GateBanner({
  decision,
  reasons,
}: {
  decision: "GO" | "GO_MONITOR" | "CAUTION" | "NO_GO";
  reasons: string[];
}) {
  const cfg: Record<
    string,
    { label: string; icon: React.ReactNode; body: string; bg: string; fg: string; border: string }
  > = {
    GO: {
      label: "GO",
      icon: <CheckCircle2 className="h-5 w-5" />,
      body: "Sleep inputs support mission continuation. No gate flags on duration, debt, SRI, or SpO₂ screen.",
      bg: "bg-emerald-50 dark:bg-emerald-950/30",
      fg: "text-emerald-900 dark:text-emerald-100",
      border: "border-emerald-500",
    },
    GO_MONITOR: {
      label: "GO (MONITOR)",
      icon: <Bed className="h-5 w-5" />,
      body: "Mild deficits — proceed with CRM awareness and reassess after next sleep opportunity.",
      bg: "bg-lime-50 dark:bg-lime-950/30",
      fg: "text-lime-900 dark:text-lime-100",
      border: "border-lime-500",
    },
    CAUTION: {
      label: "CAUTION",
      icon: <AlertTriangle className="h-5 w-5" />,
      body: "Meaningful sleep deficit or schedule irregularity. Consider task swap, mission modification, or recovery window.",
      bg: "bg-amber-50 dark:bg-amber-950/30",
      fg: "text-amber-900 dark:text-amber-100",
      border: "border-amber-500",
    },
    NO_GO: {
      label: "NO-GO",
      icon: <ShieldAlert className="h-5 w-5" />,
      body: "Hard gate triggered — do not fly / operate. Schedule a recovery window and consult the flight surgeon.",
      bg: "bg-red-50 dark:bg-red-950/30",
      fg: "text-red-900 dark:text-red-100",
      border: "border-red-500",
    },
  };
  const c = cfg[decision];
  return (
    <div className={`flex items-start gap-3 rounded-md border-2 p-4 ${c.bg} ${c.fg} ${c.border}`}>
      <div className="mt-0.5">{c.icon}</div>
      <div className="flex-1 space-y-1">
        <p className="text-xl font-bold">{c.label}</p>
        <p className="text-sm">{c.body}</p>
        {reasons.length > 0 && (
          <ul className="list-disc space-y-0.5 pl-5 text-xs">
            {reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function KPI({
  label,
  value,
  hint,
  colour,
}: {
  label: string;
  value: string;
  hint?: string;
  colour?: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-1 py-3">
        <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
        <p
          className="text-2xl font-bold tabular-nums"
          style={colour ? { color: colour } : undefined}
        >
          {value}
        </p>
        {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}

function DecisionTable({
  readiness,
}: {
  readiness: { decision: string; reasons: string[]; inputs: Record<string, unknown> };
}) {
  const rows: Array<[string, string]> = [];
  const i = readiness.inputs;
  const fmt = (v: unknown, unit = "", digits = 1): string => {
    if (v == null) return "—";
    if (typeof v === "number") return `${v.toFixed(digits)}${unit}`;
    return String(v);
  };
  rows.push(["Last-night sleep", fmt(i["last_sleep_hours"], " h", 1)]);
  rows.push(["7-night cumulative debt", fmt(i["cumulative_debt_hours_7d"], " h", 1)]);
  rows.push(["Sleep Regularity Index", fmt(i["sleep_regularity_index"], " %", 0)]);
  rows.push(["Bedtime SD", fmt(i["bedtime_sd_minutes"], " min", 0)]);
  rows.push(["Low-SpO₂ nights (7d)", fmt(i["low_spo2_nights_7d"], "", 0)]);
  rows.push(["Mean SpO₂ (7d)", fmt(i["mean_spo2_7d"], " %", 1)]);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label} className="border-b">
              <td className="py-1.5 pr-3 text-muted-foreground">{label}</td>
              <td className="py-1.5 font-semibold tabular-nums">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
