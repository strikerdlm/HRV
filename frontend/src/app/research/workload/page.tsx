// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Brain, Download, RefreshCw } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";
import { QualityPanel } from "@/components/research/quality-panel";
import {
  computeWorkloadFeatures,
  getHRVTimeSeries,
} from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { WorkloadResponse, WorkloadSegment } from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

interface SegmentBounds {
  start: number;
  end: number;
}

function rrChartOption(
  rrValues: number[],
  baseline: SegmentBounds,
  task: SegmentBounds,
  recovery: SegmentBounds,
): Record<string, unknown> {
  return {
    grid: { left: 55, right: 20, top: 35, bottom: 50, containLabel: true },
    xAxis: {
      type: "category",
      data: rrValues.map((_, idx) => idx),
      axisLabel: { color: "#1a1a1a" },
      name: "Beat index",
      nameTextStyle: { color: "#1a1a1a" },
    },
    yAxis: {
      type: "value",
      name: "RR (ms)",
      axisLabel: { color: "#1a1a1a" },
      nameTextStyle: { color: "#1a1a1a" },
    },
    tooltip: { trigger: "axis" },
    dataZoom: [{ type: "inside" }, { type: "slider", height: 18, bottom: 8 }],
    series: [
      {
        type: "line",
        data: rrValues,
        symbol: "none",
        lineStyle: { color: SCIENTIFIC_COLORS.primary, width: 1.5 },
        markArea: {
          silent: true,
          data: [
            [
              {
                xAxis: baseline.start,
                itemStyle: { color: "rgba(39, 174, 96, 0.15)" },
                label: { show: true, formatter: "Baseline" },
              },
              { xAxis: baseline.end },
            ],
            [
              {
                xAxis: task.start,
                itemStyle: { color: "rgba(243, 156, 18, 0.2)" },
                label: { show: true, formatter: "Task" },
              },
              { xAxis: task.end },
            ],
            [
              {
                xAxis: recovery.start,
                itemStyle: { color: "rgba(52, 152, 219, 0.15)" },
                label: { show: true, formatter: "Recovery" },
              },
              { xAxis: recovery.end },
            ],
          ],
        },
      },
    ],
  };
}

export default function WorkloadPage() {
  const [rrValues, setRrValues] = React.useState<number[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<WorkloadResponse | null>(null);

  const [baseline, setBaseline] = React.useState<SegmentBounds>({ start: 0, end: 120 });
  const [task, setTask] = React.useState<SegmentBounds>({ start: 121, end: 280 });
  const [recovery, setRecovery] = React.useState<SegmentBounds>({ start: 281, end: 420 });

  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchRR = React.useCallback(async () => {
    setLoading(true);
    try {
      const ts = await getHRVTimeSeries(userId, 2000);
      setRrValues(ts.rr_ms);
      const n = ts.rr_ms.length;
      if (n > 30) {
        const third = Math.floor(n / 3);
        setBaseline({ start: 0, end: Math.max(10, third - 1) });
        setTask({ start: third, end: Math.max(third + 10, 2 * third - 1) });
        setRecovery({ start: 2 * third, end: n - 1 });
      }
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    void fetchRR();
  }, [fetchRR]);

  const buildSegments = React.useCallback((): WorkloadSegment[] => {
    return [
      { label: "baseline", start_idx: baseline.start, end_idx: baseline.end, task_name: "Baseline" },
      { label: "task", start_idx: task.start, end_idx: task.end, task_name: "Task" },
      { label: "recovery", start_idx: recovery.start, end_idx: recovery.end, task_name: "Recovery" },
    ];
  }, [baseline, task, recovery]);

  const runWorkload = React.useCallback(async () => {
    if (rrValues.length < 30) return;
    setLoading(true);
    try {
      const payload = {
        rr_intervals_ms: rrValues,
        segments: buildSegments(),
        task_name: "User-annotated task",
      };
      const out = await computeWorkloadFeatures(payload);
      setResult(out);
    } finally {
      setLoading(false);
    }
  }, [rrValues, buildSegments]);

  const exportAnnotated = React.useCallback(() => {
    const payload = {
      exported_at: new Date().toISOString(),
      user_id: userId,
      segments: buildSegments(),
      workload_result: result,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `workload-annotations-${userId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [userId, buildSegments, result]);

  const maxIndex = Math.max(0, rrValues.length - 1);

  return (
    <PageWrapper
      title="Cognitive Workload"
      description="Baseline to Task to Recovery annotation and reactivity metrics"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-3"
        >
          <div className="flex items-center gap-2">
            <Badge variant="outline">RR samples: {rrValues.length}</Badge>
            {result && (
              <Badge variant={result.confidence === "good" ? "success" : result.confidence === "moderate" ? "warning" : "destructive"}>
                Confidence: {result.confidence}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => void fetchRR()} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
              Reload RR
            </Button>
            <Button onClick={() => void runWorkload()} disabled={loading || rrValues.length < 30}>
              <Brain className="h-4 w-4 mr-2" />
              Compute Workload
            </Button>
            <Button variant="outline" onClick={exportAnnotated} disabled={!result}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </div>
        </motion.div>

        {result && <QualityPanel context={result.context} />}

        <Card>
          <CardHeader>
            <CardTitle>Segment Annotation</CardTitle>
            <CardDescription>
              Define baseline/task/recovery beat ranges, then compute ΔlnRMSSD, ΔHF, ΔLF/HF and recovery slope.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            {[
              ["Baseline", baseline, setBaseline],
              ["Task", task, setTask],
              ["Recovery", recovery, setRecovery],
            ].map(([label, bounds, setBounds]) => (
              <div key={label as string} className="space-y-2 rounded-lg border p-3">
                <p className="text-sm font-semibold">{label as string}</p>
                <div className="space-y-1">
                  <Label htmlFor={`${label}-start`}>Start index</Label>
                  <Input
                    id={`${label}-start`}
                    type="number"
                    min={0}
                    max={maxIndex}
                    value={(bounds as SegmentBounds).start}
                    onChange={(e) =>
                      (setBounds as React.Dispatch<React.SetStateAction<SegmentBounds>>)({
                        ...(bounds as SegmentBounds),
                        start: Math.max(0, Math.min(maxIndex, Number(e.target.value))),
                      })
                    }
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor={`${label}-end`}>End index</Label>
                  <Input
                    id={`${label}-end`}
                    type="number"
                    min={0}
                    max={maxIndex}
                    value={(bounds as SegmentBounds).end}
                    onChange={(e) =>
                      (setBounds as React.Dispatch<React.SetStateAction<SegmentBounds>>)({
                        ...(bounds as SegmentBounds),
                        end: Math.max(0, Math.min(maxIndex, Number(e.target.value))),
                      })
                    }
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>RR Trace with Segment Labels</CardTitle>
          </CardHeader>
          <CardContent>
            <EChartsWrapper
              option={rrChartOption(rrValues, baseline, task, recovery)}
              height={320}
            />
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>Workload Outputs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-4">
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xs text-muted-foreground">ΔlnRMSSD</p>
                  <p className="text-xl font-bold">{result.delta_lnrmssd?.toFixed(3) ?? "—"}</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xs text-muted-foreground">ΔHF</p>
                  <p className="text-xl font-bold">{result.delta_hf?.toFixed(2) ?? "—"}</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xs text-muted-foreground">ΔLF/HF</p>
                  <p className="text-xl font-bold">{result.delta_lf_hf?.toFixed(2) ?? "—"}</p>
                </div>
                <div className="rounded-lg border p-3 text-center">
                  <p className="text-xs text-muted-foreground">High-workload probability</p>
                  <p className="text-xl font-bold">{(result.high_workload_probability * 100).toFixed(0)}%</p>
                </div>
              </div>
              {result.threshold_flags.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {result.threshold_flags.map((flag) => (
                    <Badge key={flag} variant="warning">{flag}</Badge>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No threshold flags triggered for the current annotations.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}

