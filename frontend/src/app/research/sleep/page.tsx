// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { Activity, AlertTriangle, Moon, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
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
import {
  SleepDurationTrend,
  SleepDebtCurve,
  StageBalanceStackedBar,
  StageBalancePie,
  CorrelationMatrix,
  CorrelationScatter,
  RegularityStrip,
  type DurationPoint,
  type RegularityPoint,
  type ScatterPoint,
  type StagePerNight,
} from "@/components/sleep/sleep-charts";
import {
  SLEEP_THRESHOLDS,
  decisionColour,
  formatHours,
  formatMinutes,
  formatP,
  formatPercent,
  formatSpO2,
  metricLabel,
  screeningColour,
  type SleepCorrelation,
  type SleepCorrelationsResponse,
  type SleepDebtTrendResponse,
  type SleepSummary,
} from "@/lib/sleep-metrics";
import { useAppStore } from "@/lib/store";

const DEFAULT_USER_ID = "demo-user";

interface RawGarminRow {
  date?: string;
  metric_date?: string;
  sleep_duration_hours?: number | null;
  sleep_deep_minutes?: number | null;
  sleep_rem_minutes?: number | null;
  sleep_light_minutes?: number | null;
  sleep_awake_minutes?: number | null;
  hrv_rmssd_ms?: number | null;
  hrv_overnight?: number | null;
  avg_spo2?: number | null;
  spo2_avg?: number | null;
  resting_hr_bpm?: number | null;
  resting_hr?: number | null;
  sleep_score?: number | null;
  sleep_efficiency?: number | null;
  avg_respiration_sleep?: number | null;
  respiration_sleep?: number | null;
  sleep_start_utc?: string | null;
  sleep_end_utc?: string | null;
}

export default function ResearchSleepPage() {
  const userId = useAppStore((s: { userId?: string | null }) => s.userId ?? DEFAULT_USER_ID);
  const [summary, setSummary] = React.useState<SleepSummary | null>(null);
  const [correlations, setCorrelations] = React.useState<SleepCorrelationsResponse | null>(null);
  const [debtTrend, setDebtTrend] = React.useState<SleepDebtTrendResponse | null>(null);
  const [rawHistory, setRawHistory] = React.useState<RawGarminRow[]>([]);
  const [loading, setLoading] = React.useState<boolean>(true);
  const [error, setError] = React.useState<string | null>(null);
  const [days, setDays] = React.useState<number>(60);

  const apiBase = React.useMemo(() => {
    if (typeof window === "undefined") return "";
    return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8180";
  }, []);

  const loadAll = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const uid = encodeURIComponent(userId);
      const [rsum, rcorr, rdebt, rhist] = await Promise.all([
        fetch(`${apiBase}/api/research/garmin/sleep-summary/${uid}?days=${days}`),
        fetch(`${apiBase}/api/research/garmin/sleep-correlations/${uid}?days=${days}`),
        fetch(`${apiBase}/api/research/garmin/sleep-debt-trend/${uid}?days=${Math.min(days, 60)}`),
        fetch(`${apiBase}/api/research/garmin/history/${uid}?days=${days}`),
      ]);
      if (!rsum.ok) throw new Error(`summary: HTTP ${rsum.status}`);
      if (!rcorr.ok) throw new Error(`correlations: HTTP ${rcorr.status}`);
      if (!rdebt.ok) throw new Error(`debt: HTTP ${rdebt.status}`);
      if (!rhist.ok) throw new Error(`history: HTTP ${rhist.status}`);
      setSummary(await rsum.json());
      setCorrelations(await rcorr.json());
      setDebtTrend(await rdebt.json());
      setRawHistory(await rhist.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sleep data");
    } finally {
      setLoading(false);
    }
  }, [apiBase, days, userId]);

  React.useEffect(() => {
    loadAll();
  }, [loadAll]);

  // ----- derive plot inputs ------------------------------------------------
  const durationSeries: DurationPoint[] = React.useMemo(() => {
    // history arrives newest-first; reverse for chronological plots
    return [...rawHistory].reverse().map((r) => ({
      date: r.metric_date ?? r.date ?? "",
      hours: (r.sleep_duration_hours ?? null) as number | null,
    }));
  }, [rawHistory]);

  const stageSeries: StagePerNight[] = React.useMemo(() => {
    return [...rawHistory].reverse().map((r) => ({
      date: r.metric_date ?? r.date ?? "",
      deep: r.sleep_deep_minutes ?? null,
      rem: r.sleep_rem_minutes ?? null,
      light: r.sleep_light_minutes ?? null,
      awake: r.sleep_awake_minutes ?? null,
    }));
  }, [rawHistory]);

  const regularitySeries: RegularityPoint[] = React.useMemo(() => {
    return [...rawHistory].reverse().map((r) => {
      const parseHour = (iso: string | null | undefined): number | null => {
        if (!iso) return null;
        try {
          const d = new Date(iso);
          return d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600;
        } catch {
          return null;
        }
      };
      const bed = parseHour(r.sleep_start_utc ?? null);
      let wake = parseHour(r.sleep_end_utc ?? null);
      // Extend wake onto the following day if bedtime is late evening
      if (bed != null && wake != null && wake <= bed) wake += 24;
      return {
        date: r.metric_date ?? r.date ?? "",
        bedtime_hour_of_day: bed,
        waketime_hour_of_day: wake,
      };
    });
  }, [rawHistory]);

  const scatterFor = React.useCallback(
    (keyX: keyof RawGarminRow): ScatterPoint[] => {
      return rawHistory
        .map((r) => {
          const x = (r[keyX] as number | null | undefined) ?? null;
          const y = (r.hrv_rmssd_ms ?? r.hrv_overnight ?? null) as number | null;
          if (x == null || y == null || !Number.isFinite(x) || !Number.isFinite(y)) return null;
          return { x: x as number, y: y as number, date: r.metric_date ?? r.date };
        })
        .filter((p): p is ScatterPoint => p !== null);
    },
    [rawHistory],
  );

  const corrFor = React.useCallback(
    (metricX: string): SleepCorrelation | null => {
      if (!correlations) return null;
      return correlations.results.find((r) => r.metric_x === metricX) ?? null;
    },
    [correlations],
  );

  // ----- latest-night summary cards ----------------------------------------
  const latest = summary?.stage_balance_latest;
  const debt = summary?.debt_7d;
  const reg = summary?.regularity_14d;
  const spo2 = summary?.spo2_screen_7d;
  const readiness = summary?.readiness;

  // ----- render ------------------------------------------------------------
  return (
    <PageWrapper
      title="Sleep Research Dashboard"
      description={
        "Garmin-backed sleep architecture, regularity, and autonomic correlations. " +
        "All visuals are exploratory; wellness device (not PSG) per Lee 2025 / Schyvens 2024."
      }
    >
      <div className="space-y-4">
        {/* ------------------------------------------------------- controls */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base">Window</CardTitle>
                <CardDescription>
                  Data volume vs statistical power — Pending.md §5 recommends n ≥ 14 nights per
                  correlation pair for meaningful inference.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {[30, 60, 90, 180].map((d) => (
                  <Button
                    key={d}
                    size="sm"
                    variant={d === days ? "default" : "outline"}
                    onClick={() => setDays(d)}
                  >
                    {d} d
                  </Button>
                ))}
                <Button size="sm" variant="outline" onClick={loadAll} disabled={loading}>
                  <RefreshCw className={"h-4 w-4 " + (loading ? "animate-spin" : "")} />
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        {error && (
          <Card className="border-red-500">
            <CardContent className="flex items-center gap-2 py-3 text-sm text-red-700">
              <AlertTriangle className="h-4 w-4" /> {error}
            </CardContent>
          </Card>
        )}

        {/* ----------------------------------------------- headline KPIs */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <KPI
            label="30-day mean duration"
            value={formatHours(summary?.mean_sleep_duration_hours_30d ?? null)}
            hint={`Target ${SLEEP_THRESHOLDS.typicalTargetHours} h`}
          />
          <KPI
            label="7-night sleep debt"
            value={formatHours(debt?.cumulative_debt_hours ?? null)}
            hint={`CAUTION ≥${SLEEP_THRESHOLDS.debtCautionHours7d}h · NO-GO ≥${SLEEP_THRESHOLDS.debtNoGoHours7d}h`}
          />
          <KPI
            label="Sleep Regularity Index"
            value={reg?.sri_percent != null ? `${reg.sri_percent.toFixed(0)}%` : "—"}
            hint="Lunsford-Avery 2018"
          />
          <KPI
            label="Low-SpO₂ nights (7d)"
            value={spo2?.low_spo2_nights_7d != null ? `${spo2.low_spo2_nights_7d} / 7` : "—"}
            hint={`Screening only · <${SLEEP_THRESHOLDS.spo2LowThreshold}%`}
            colour={spo2 ? screeningColour(spo2.band) : undefined}
          />
        </div>

        {/* ------------------------------------------- readiness banner */}
        {readiness && (
          <Card style={{ borderColor: decisionColour(readiness.decision) }} className="border-2">
            <CardContent className="flex flex-col gap-2 py-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  Operational sleep readiness
                </p>
                <p
                  className="text-2xl font-bold"
                  style={{ color: decisionColour(readiness.decision) }}
                >
                  {readiness.decision.replace("_", " ")}
                </p>
              </div>
              <ul className="list-disc space-y-0.5 pl-5 text-xs text-muted-foreground">
                {readiness.reasons.length > 0 ? (
                  readiness.reasons.map((r, i) => <li key={i}>{r}</li>)
                ) : (
                  <li>No flags on last night, 7-night debt, SRI, or SpO₂ screen.</li>
                )}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* --------------------------------------------- duration & debt */}
        <div className="grid gap-3 lg:grid-cols-2">
          <Card>
            <CardContent className="pt-4">
              <SleepDurationTrend data={durationSeries} />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              {debtTrend ? (
                <SleepDebtCurve series={debtTrend.series} />
              ) : (
                <PlaceholderBox label="Loading debt trend…" />
              )}
            </CardContent>
          </Card>
        </div>

        {/* --------------------------------------------- stage balance */}
        <div className="grid gap-3 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardContent className="pt-4">
              <StageBalanceStackedBar data={stageSeries} />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              {latest?.total_minutes ? (
                <StageBalancePie balance={latest} />
              ) : (
                <PlaceholderBox label="No stage data on latest night" />
              )}
              {latest?.total_minutes && (
                <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                  <div>
                    Deep: {formatMinutes((latest.deep_pct ?? 0) * (latest.total_minutes ?? 0))} (
                    {formatPercent(latest.deep_pct)})
                  </div>
                  <div>
                    REM: {formatMinutes((latest.rem_pct ?? 0) * (latest.total_minutes ?? 0))} (
                    {formatPercent(latest.rem_pct)})
                  </div>
                  <div>
                    Deep + REM: {formatMinutes(latest.deep_plus_rem_minutes)} (
                    {formatPercent(latest.deep_plus_rem_pct)})
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* --------------------------------------------- regularity */}
        <Card>
          <CardContent className="pt-4">
            <RegularityStrip data={regularitySeries} />
            {reg && (
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted-foreground md:grid-cols-4">
                <RegStat label="SRI" value={reg.sri_percent != null ? `${reg.sri_percent.toFixed(0)}%` : "—"} />
                <RegStat
                  label="Bedtime SD"
                  value={reg.bedtime_sd_minutes != null ? `${reg.bedtime_sd_minutes.toFixed(0)} min` : "—"}
                />
                <RegStat
                  label="Waketime SD"
                  value={reg.waketime_sd_minutes != null ? `${reg.waketime_sd_minutes.toFixed(0)} min` : "—"}
                />
                <RegStat
                  label="Midpoint SD"
                  value={reg.midpoint_sd_minutes != null ? `${reg.midpoint_sd_minutes.toFixed(0)} min` : "—"}
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* --------------------------------------------- correlation matrix */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Tier A correlations × overnight HRV</CardTitle>
            <CardDescription>
              Pairwise Pearson with two-sided p and Benjamini-Hochberg FDR-adjusted q across the eight
              pairs. Interpret as <em>within-cohort concordance</em> — not validation of Garmin sleep
              against PSG.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {correlations ? (
              <CorrelationMatrix results={correlations.results} />
            ) : (
              <PlaceholderBox label="Loading correlations…" />
            )}
            {correlations && (
              <div className="mt-2 text-xs text-muted-foreground">
                Window: {correlations.n_nights_window} nights · method: {correlations.method}
                {correlations.n_nights_window < correlations.min_nights_for_stats && (
                  <span className="ml-2 inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-amber-900">
                    <AlertTriangle className="h-3 w-3" /> Underpowered — n &lt;{" "}
                    {correlations.min_nights_for_stats}.
                  </span>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* --------------------------------------------- scatter grid */}
        <div className="grid gap-3 lg:grid-cols-2">
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("sleep_duration_hours")}
                xLabel="Sleep duration (h)"
                yLabel="Overnight HRV RMSSD (ms)"
                title="Duration × HRV"
                corr={corrFor("sleep_duration_hours")}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("sleep_score")}
                xLabel="Sleep score"
                yLabel="Overnight HRV RMSSD (ms)"
                title="Score × HRV"
                corr={corrFor("sleep_score")}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("sleep_deep_minutes")}
                xLabel="Deep sleep (min)"
                yLabel="Overnight HRV RMSSD (ms)"
                title="Deep sleep × HRV"
                corr={corrFor("sleep_deep_minutes")}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("sleep_rem_minutes")}
                xLabel="REM sleep (min)"
                yLabel="Overnight HRV RMSSD (ms)"
                title="REM sleep × HRV"
                corr={corrFor("sleep_rem_minutes")}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("avg_spo2")}
                xLabel="Avg overnight SpO₂ (%)"
                yLabel="Overnight HRV RMSSD (ms)"
                title="SpO₂ × HRV"
                corr={corrFor("avg_spo2")}
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <CorrelationScatter
                points={scatterFor("avg_respiration_sleep")}
                xLabel="Sleep respiration (bpm)"
                yLabel="Overnight HRV RMSSD (ms)"
                title="Respiration × HRV"
                corr={corrFor("avg_respiration_sleep")}
              />
            </CardContent>
          </Card>
        </div>

        {/* --------------------------------------------- evidence card */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Evidence map (Pending.md §2)</CardTitle>
            <CardDescription>
              Direction and caveats from peer-reviewed literature applicable to the visualisations
              above. <strong>All charts are exploratory; Garmin accuracy bounded by Lee 2025 /
              Schyvens 2024 vs PSG.</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground">
            <EvidenceLine
              theme="Sleep stages × HRV"
              finding="RMSSD / HF rises from wake → NREM (incl. SWS); partial reversal toward REM. Moderate SDB amplifies HF/RMSSD drops SWS → REM."
              refs={[
                { label: "Liao 2010", pmid: "20337904" },
                { label: "Kesek 2009", pmid: "19453563" },
              ]}
            />
            <EvidenceLine
              theme="Sleep deprivation / fragmentation × ANS"
              finding="Fragmentation and deprivation associated with autonomic imbalance (HF ↓, sympathovagal shift). Heterogeneity across protocols."
              refs={[
                { label: "Zhang 2023 meta-analysis", pmid: "40895095" },
                { label: "Zhu 2023 circadian types", pmid: "40768960" },
              ]}
            />
            <EvidenceLine
              theme="Wake HRV × SpO₂ / apnea proxies"
              finding="Wake RMSSD has been linked to AHI and mean nocturnal SpO₂ in clinical/altitude cohorts. Do not over-claim apnea from consumer aggregates — SpO₂ here is screening only."
              refs={[{ label: "Balali 2025 altitude cohort", pmid: "41953462" }]}
            />
            <EvidenceLine
              theme="Sleep regularity × cardiometabolic risk"
              finding="Lower SRI associated with elevated 10-y CVD risk, obesity, hypertension, glucose, and HbA1c independent of sleep duration."
              refs={[{ label: "Lunsford-Avery 2018", doi: "10.1038/s41598-018-32402-5" }]}
            />
            <EvidenceLine
              theme="Consumer wearable vs PSG"
              finding="Garmin, Fitbit, WHOOP differ from PSG on total sleep time, efficiency, latency, and WASO by clinically meaningful margins. Interpret patterns, not absolute minutes."
              refs={[
                { label: "Lee 2025 meta-analysis", doi: "10.5664/jcsm.11460" },
                { label: "Schyvens 2024 systematic review", doi: "10.2196/52192" },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

function RegStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/30 p-2">
      <p className="text-[10px] uppercase tracking-wide">{label}</p>
      <p className="mt-0.5 text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function PlaceholderBox({ label }: { label: string }) {
  return (
    <div className="flex h-48 items-center justify-center rounded border border-dashed text-xs text-muted-foreground">
      {label}
    </div>
  );
}

function EvidenceLine({
  theme,
  finding,
  refs,
}: {
  theme: string;
  finding: string;
  refs: Array<{ label: string; pmid?: string; doi?: string }>;
}) {
  return (
    <div className="rounded border bg-card p-2">
      <p className="text-[12px] font-semibold text-foreground">{theme}</p>
      <p className="text-[12px]">{finding}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {refs.map((r, i) => {
          const url = r.pmid
            ? `https://pubmed.ncbi.nlm.nih.gov/${r.pmid}/`
            : r.doi
              ? `https://doi.org/${r.doi}`
              : "#";
          return (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noreferrer"
              className="rounded border px-1.5 py-0.5 text-[11px] hover:bg-muted"
            >
              {r.label}
            </a>
          );
        })}
      </div>
    </div>
  );
}
