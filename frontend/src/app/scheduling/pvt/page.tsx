// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { Plane, CheckCircle2, AlertTriangle, Brain } from "lucide-react";
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
import { PvtTest } from "@/components/pvt/pvt-test";
import type { PVTMetrics, PVTTrial } from "@/lib/pvt-scoring";
import { useAppStore } from "@/lib/store";

const DEFAULT_USER_ID = "demo-user";

interface OperationalResult {
  metrics: PVTMetrics;
  decision: string;
  saved: boolean;
  savedId?: number;
  error?: string;
}

export default function OperationalPvtPage() {
  const userId = useAppStore((s: { userId?: string | null }) => s.userId ?? DEFAULT_USER_ID);
  const [result, setResult] = React.useState<OperationalResult | null>(null);
  const [saving, setSaving] = React.useState<boolean>(false);

  const apiBase = React.useMemo(() => {
    if (typeof window === "undefined") return "";
    return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8180";
  }, []);

  const handleComplete = React.useCallback(
    async (metrics: PVTMetrics, trials: PVTTrial[]) => {
      setSaving(true);
      setResult(null);
      try {
        const body = {
          variant: metrics.variant,
          duration_min: metrics.duration_min,
          lapse_threshold_ms: metrics.lapse_threshold_ms,
          user_id: userId,
          device_label: "web-operational",
          software_version: metrics.software_version ?? "pvt-test v1",
          started_at: metrics.started_at,
          ended_at: metrics.ended_at,
          trials: trials.map((t) => ({
            index: t.index,
            isi_ms: t.isi_ms,
            stimulus_onset_ms: t.stimulus_onset_ms,
            rt_ms: t.rt_ms,
            anticipatory: t.anticipatory ?? false,
          })),
        };
        const r = await fetch(`${apiBase}/api/pvt/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const saved = await r.json();
        setResult({
          metrics,
          decision: saved.decision ?? "GO",
          saved: true,
          savedId: saved.id,
        });
      } catch (err) {
        console.error("Operational PVT save failed", err);
        // Still surface local decision using local metrics
        setResult({
          metrics,
          decision:
            metrics.pvt_lapses_3min >= 20
              ? "NO_GO"
              : metrics.pvt_lapses_3min >= 10
                ? "CAUTION"
                : metrics.pvt_lapses_3min >= 5
                  ? "GO_MONITOR"
                  : "GO",
          saved: false,
          error: err instanceof Error ? err.message : "save failed",
        });
      } finally {
        setSaving(false);
      }
    },
    [apiBase, userId],
  );

  const gateBanner = result ? renderGateBanner(result.decision) : null;

  return (
    <PageWrapper
      title="Pre-flight PVT (Operational)"
      description="3-minute PVT-B for pre-flight / shift-check alertness gating. Lapse threshold 355 ms (Basner & Dinges 2011). Feeds pvt_lapses_3min into the scheduling/readiness pipeline."
    >
      <div className="space-y-4">
        {!result && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plane className="h-4 w-4" /> Pre-flight readiness gate
              </CardTitle>
              <CardDescription>
                Complete the 3-minute PVT-B before mission start. Result feeds the hard gate
                at ≥20 lapses (low-performance) via{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs">pvt_lapses_3min</code>
                {" "}in app.scheduling_core. Run in a quiet area with the screen in focus.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {!result && (
          <PvtTest
            variant="PVT-B"
            userId={userId}
            deviceLabel="web-operational"
            onComplete={handleComplete}
          />
        )}

        {saving && (
          <Card>
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              Submitting result to scheduling/readiness pipeline…
            </CardContent>
          </Card>
        )}

        {result && (
          <>
            {gateBanner}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Session result</span>
                  {result.saved ? (
                    <Badge className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      pushed to readiness pipeline (#{result.savedId})
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      not saved: {result.error}
                    </Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <KV label="Decision" value={result.decision.replace("_", " ")} />
                  <KV
                    label="pvt_lapses_3min"
                    value={result.metrics.pvt_lapses_3min.toString()}
                  />
                  <KV label="Lapses (≥355 ms)" value={result.metrics.n_lapses.toString()} />
                  <KV label="Major lapses" value={result.metrics.n_major_lapses.toString()} />
                  <KV label="False starts" value={result.metrics.n_false_starts.toString()} />
                  <KV label="Valid trials" value={result.metrics.n_valid_trials.toString()} />
                  <KV
                    label="Mean RT (ms)"
                    value={result.metrics.mean_rt_ms?.toFixed(0) ?? "—"}
                  />
                  <KV
                    label="Mean 1/RT (s⁻¹)"
                    value={
                      result.metrics.mean_response_speed_per_s
                        ? result.metrics.mean_response_speed_per_s.toFixed(3)
                        : "—"
                    }
                  />
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="outline" onClick={() => setResult(null)}>
                    Run again
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </PageWrapper>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderGateBanner(decision: string) {
  const cfg: Record<string, { label: string; body: string; colour: string; icon: React.ReactNode }> = {
    GO: {
      label: "GO",
      body: "Alertness within acceptable operational bounds. Cleared for task.",
      colour: "border-emerald-500 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200",
      icon: <CheckCircle2 className="h-5 w-5" />,
    },
    GO_MONITOR: {
      label: "GO (MONITOR)",
      body: "Mild attentional degradation. Proceed with enhanced crew-resource-management awareness and scheduled reassessment.",
      colour: "border-lime-500 bg-lime-50 text-lime-900 dark:bg-lime-950/30 dark:text-lime-200",
      icon: <Brain className="h-5 w-5" />,
    },
    CAUTION: {
      label: "CAUTION",
      body: "Moderate PVT lapse rate (10–19 lapses / 3 min equivalent). Consider mission modification, task-swap, or supervised operation.",
      colour: "border-amber-500 bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200",
      icon: <AlertTriangle className="h-5 w-5" />,
    },
    NO_GO: {
      label: "NO-GO",
      body: "Low-performance gate triggered (≥20 lapses / 3 min equivalent). Do not proceed with the mission. Rest or consult the flight surgeon.",
      colour: "border-red-500 bg-red-50 text-red-900 dark:bg-red-950/30 dark:text-red-200",
      icon: <AlertTriangle className="h-5 w-5" />,
    },
  };
  const c = cfg[decision] ?? cfg.GO;
  return (
    <div className={`flex items-start gap-3 rounded-md border-2 p-4 ${c.colour}`}>
      <div className="mt-0.5">{c.icon}</div>
      <div>
        <p className="text-lg font-bold">{c.label}</p>
        <p className="text-sm">{c.body}</p>
      </div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
