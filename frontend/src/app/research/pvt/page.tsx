// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { History, AlertTriangle } from "lucide-react";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PvtTest } from "@/components/pvt/pvt-test";
import type { PVTMetrics, PVTTrial, PVTVariant } from "@/lib/pvt-scoring";
import { useAppStore } from "@/lib/store";

const DEFAULT_USER_ID = "demo-user";

interface SavedSession {
  id: number;
  user_id: string | null;
  variant: string;
  created_at: string;
  n_lapses: number;
  n_valid_trials: number;
  mean_rt_ms: number | null;
  mean_response_speed_per_s: number | null;
  pvt_lapses_3min: number;
  decision: string | null;
}

export default function ResearchPvtPage() {
  const userId = useAppStore((s: { userId?: string | null }) => s.userId ?? DEFAULT_USER_ID);
  const [variant, setVariant] = React.useState<PVTVariant>("PVT-5");
  const [saveStatus, setSaveStatus] = React.useState<"idle" | "saving" | "saved" | "error">("idle");
  const [history, setHistory] = React.useState<SavedSession[]>([]);
  const [historyLoading, setHistoryLoading] = React.useState<boolean>(false);

  const apiBase = React.useMemo(() => {
    if (typeof window === "undefined") return "";
    return process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8180";
  }, []);

  const loadHistory = React.useCallback(async () => {
    if (!userId) return;
    setHistoryLoading(true);
    try {
      const r = await fetch(`${apiBase}/api/pvt/sessions/${encodeURIComponent(userId)}?limit=20`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as SavedSession[];
      setHistory(data);
    } catch (err) {
      // swallow; history is informational
      console.warn("PVT history load failed", err);
    } finally {
      setHistoryLoading(false);
    }
  }, [apiBase, userId]);

  React.useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleComplete = React.useCallback(
    async (metrics: PVTMetrics, trials: PVTTrial[]) => {
      setSaveStatus("saving");
      try {
        const body = {
          variant: metrics.variant,
          duration_min: metrics.duration_min,
          lapse_threshold_ms: metrics.lapse_threshold_ms,
          user_id: userId,
          device_label: "web-research",
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
        setSaveStatus("saved");
        loadHistory();
      } catch (err) {
        console.error("PVT session save failed", err);
        setSaveStatus("error");
      }
    },
    [apiBase, loadHistory, userId],
  );

  return (
    <PageWrapper
      title="Psychomotor Vigilance Task (Research)"
      description="5-minute PVT for longitudinal alertness tracking. Saves to session history for trend analysis."
    >
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Session configuration</CardTitle>
                <CardDescription>
                  Research sessions persist to the backend via POST /api/pvt/sessions and feed
                  the operator-readiness history. Use PVT-5 for routine longitudinal tracking;
                  PVT-B (3-min) is available for time-constrained sessions; PVT-10 is the
                  full Dinges 1997 reference duration.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-muted-foreground">Variant</label>
                <Select value={variant} onValueChange={(v: string) => setVariant(v as PVTVariant)}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PVT-B">PVT-B (3 min)</SelectItem>
                    <SelectItem value="PVT-5">PVT-5 (5 min)</SelectItem>
                    <SelectItem value="PVT-10">PVT-10 (10 min)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
        </Card>

        <PvtTest
          variant={variant}
          userId={userId}
          deviceLabel="web-research"
          onComplete={handleComplete}
        />

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <History className="h-4 w-4" /> Session history
              </CardTitle>
              <div className="flex items-center gap-2">
                {saveStatus === "saving" && <Badge variant="outline">saving…</Badge>}
                {saveStatus === "saved" && <Badge>saved</Badge>}
                {saveStatus === "error" && (
                  <Badge variant="destructive" className="gap-1">
                    <AlertTriangle className="h-3 w-3" /> save failed
                  </Badge>
                )}
                <Button variant="outline" size="sm" onClick={loadHistory} disabled={historyLoading}>
                  Refresh
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {historyLoading ? "Loading history…" : "No saved sessions yet."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="border-b">
                    <tr className="text-left text-xs text-muted-foreground">
                      <th className="py-2 pr-3">Date</th>
                      <th className="py-2 pr-3">Variant</th>
                      <th className="py-2 pr-3">Valid</th>
                      <th className="py-2 pr-3">Lapses</th>
                      <th className="py-2 pr-3">Mean RT (ms)</th>
                      <th className="py-2 pr-3">1/RT (s⁻¹)</th>
                      <th className="py-2 pr-3">lapses_3min</th>
                      <th className="py-2">Decision</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((s) => (
                      <tr key={s.id} className="border-b">
                        <td className="py-2 pr-3 tabular-nums">
                          {new Date(s.created_at).toLocaleString()}
                        </td>
                        <td className="py-2 pr-3">{s.variant}</td>
                        <td className="py-2 pr-3 tabular-nums">{s.n_valid_trials}</td>
                        <td className="py-2 pr-3 tabular-nums">{s.n_lapses}</td>
                        <td className="py-2 pr-3 tabular-nums">
                          {s.mean_rt_ms != null ? s.mean_rt_ms.toFixed(0) : "—"}
                        </td>
                        <td className="py-2 pr-3 tabular-nums">
                          {s.mean_response_speed_per_s != null
                            ? s.mean_response_speed_per_s.toFixed(3)
                            : "—"}
                        </td>
                        <td className="py-2 pr-3 tabular-nums">{s.pvt_lapses_3min}</td>
                        <td className="py-2">
                          <Badge
                            variant="outline"
                            className={
                              s.decision === "NO_GO"
                                ? "border-red-500 text-red-600"
                                : s.decision === "CAUTION"
                                  ? "border-amber-500 text-amber-600"
                                  : s.decision === "GO_MONITOR"
                                    ? "border-lime-500 text-lime-600"
                                    : "border-emerald-500 text-emerald-600"
                            }
                          >
                            {s.decision?.replace("_", " ") ?? "—"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}
