// Author: Dr Diego Malpica MD
"use client";

// ---------------------------------------------------------------------------
// PVT test component — actual administration UI.
//
// Uses performance.now() for sub-millisecond RT measurement. Reports RT from
// stimulus onset (as rendered on screen, post-rAF) to keydown / pointerdown
// event. Browser timing precision is bounded to ~5-10 ms per Anwyl-Irvine
// et al. (2020) robot-actuator benchmarking — adequate for operational use
// and for relative tracking across sessions, but not research-lab-grade
// (see docs/PVT.md for the timing disclosure).
//
// Canonical scoring is in app/pvt_core.py (server-side); this component
// also computes local metrics via frontend/src/lib/pvt-scoring.ts for
// immediate feedback and offline resilience.
// ---------------------------------------------------------------------------

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Play, RotateCcw, CheckCircle2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  FALSE_START_THRESHOLD_MS,
  PVT_VARIANT_DEFAULTS,
  type PVTMetrics,
  type PVTTrial,
  type PVTVariant,
  generateIsiSchedule,
  mulberry32,
  operationalGate,
  scoreTrials,
} from "@/lib/pvt-scoring";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PVTTestStage =
  | "idle"
  | "instructions"
  | "countdown"
  | "waiting"      // ISI before stimulus
  | "stimulus"    // stimulus visible, awaiting response
  | "feedback"    // transient between trials
  | "done";

export interface PVTTestProps {
  variant: PVTVariant;
  userId?: string | null;
  /** Called when the session completes with local metrics + raw trial list. */
  onComplete?: (metrics: PVTMetrics, trials: PVTTrial[]) => void;
  /** Optional deterministic RNG seed for reproducible ISI scheduling. */
  seed?: number;
  /** Label to include in metrics.device_label (e.g. 'web-research'). */
  deviceLabel?: string;
  /** Hide the stopwatch counter (shows only a red dot stimulus). */
  minimalStimulus?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PvtTest(props: PVTTestProps) {
  const {
    variant,
    userId = null,
    onComplete,
    seed,
    deviceLabel = "web",
    minimalStimulus = false,
  } = props;

  const variantDefaults = PVT_VARIANT_DEFAULTS[variant];

  const [stage, setStage] = React.useState<PVTTestStage>("idle");
  const [countdown, setCountdown] = React.useState<number>(3);
  const [elapsedMs, setElapsedMs] = React.useState<number>(0);
  const [progressPct, setProgressPct] = React.useState<number>(0);
  const [metrics, setMetrics] = React.useState<PVTMetrics | null>(null);

  // --- Trial orchestration (refs to avoid React re-renders inside the loop) --
  const trialsRef = React.useRef<PVTTrial[]>([]);
  const sessionStartRef = React.useRef<number>(0);
  const stimulusOnsetRef = React.useRef<number>(0);
  const scheduleRef = React.useRef<number[]>([]);
  const trialIndexRef = React.useRef<number>(0);
  const isiTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRafRef = React.useRef<number | null>(null);
  const responseAcceptedRef = React.useRef<boolean>(false);
  const anticipatoryRef = React.useRef<boolean>(false);

  const durationMs = variantDefaults.duration_min * 60 * 1000;

  // Generate a new session schedule every time we start
  const resetSchedule = React.useCallback(() => {
    const rng = seed !== undefined ? mulberry32(seed) : Math.random;
    scheduleRef.current = generateIsiSchedule(variant, rng);
  }, [seed, variant]);

  const stopAllTimers = React.useCallback(() => {
    if (isiTimeoutRef.current !== null) {
      clearTimeout(isiTimeoutRef.current);
      isiTimeoutRef.current = null;
    }
    if (progressRafRef.current !== null) {
      cancelAnimationFrame(progressRafRef.current);
      progressRafRef.current = null;
    }
  }, []);

  const finishSession = React.useCallback(() => {
    stopAllTimers();
    const endedAt = new Date().toISOString();
    const startedAt = new Date(
      Date.now() - (performance.now() - sessionStartRef.current),
    ).toISOString();
    const m = scoreTrials(trialsRef.current, {
      variant,
      user_id: userId,
      device_label: deviceLabel,
      software_version: "pvt-test v1",
      started_at: startedAt,
      ended_at: endedAt,
    });
    setMetrics(m);
    setStage("done");
    if (onComplete) onComplete(m, [...trialsRef.current]);
  }, [deviceLabel, onComplete, stopAllTimers, userId, variant]);

  // Schedule next trial
  const scheduleNextTrial = React.useCallback(() => {
    const elapsed = performance.now() - sessionStartRef.current;
    setElapsedMs(elapsed);
    if (elapsed >= durationMs) {
      finishSession();
      return;
    }

    const idx = trialIndexRef.current;
    const isiMs = scheduleRef.current[idx] ?? 2000;
    setStage("waiting");
    responseAcceptedRef.current = false;
    anticipatoryRef.current = false;

    isiTimeoutRef.current = setTimeout(() => {
      // Commit stimulus render; use rAF to capture the next paint timestamp
      requestAnimationFrame((ts) => {
        stimulusOnsetRef.current = ts;
        setStage("stimulus");
      });
    }, isiMs);
  }, [durationMs, finishSession]);

  // Response handling
  const handleResponse = React.useCallback(() => {
    if (stage === "waiting") {
      // Anticipatory response
      anticipatoryRef.current = true;
      const now = performance.now();
      const idx = trialIndexRef.current;
      const isiMs = scheduleRef.current[idx] ?? 0;
      trialsRef.current.push({
        index: idx,
        isi_ms: isiMs,
        stimulus_onset_ms: now - sessionStartRef.current,
        rt_ms: null,
        anticipatory: true,
      });
      trialIndexRef.current += 1;
      stopAllTimers();
      // Brief feedback, then next trial
      setStage("feedback");
      setTimeout(() => scheduleNextTrial(), 750);
      return;
    }
    if (stage !== "stimulus") return;

    if (responseAcceptedRef.current) return;
    responseAcceptedRef.current = true;

    const now = performance.now();
    const rtMs = now - stimulusOnsetRef.current;
    const idx = trialIndexRef.current;
    const isiMs = scheduleRef.current[idx] ?? 0;
    trialsRef.current.push({
      index: idx,
      isi_ms: isiMs,
      stimulus_onset_ms: stimulusOnsetRef.current - sessionStartRef.current,
      rt_ms: rtMs,
      anticipatory: false,
    });
    trialIndexRef.current += 1;
    stopAllTimers();
    setStage("feedback");
    setTimeout(() => scheduleNextTrial(), 400);
  }, [scheduleNextTrial, stage, stopAllTimers]);

  // Progress animation (elapsed vs duration)
  React.useEffect(() => {
    if (stage !== "waiting" && stage !== "stimulus" && stage !== "feedback") return;
    const tick = () => {
      const elapsed = performance.now() - sessionStartRef.current;
      setElapsedMs(elapsed);
      setProgressPct(Math.min(100, (elapsed / durationMs) * 100));
      progressRafRef.current = requestAnimationFrame(tick);
    };
    progressRafRef.current = requestAnimationFrame(tick);
    return () => {
      if (progressRafRef.current !== null) {
        cancelAnimationFrame(progressRafRef.current);
        progressRafRef.current = null;
      }
    };
  }, [durationMs, stage]);

  // Global response listeners (keyboard + click)
  React.useEffect(() => {
    if (stage !== "waiting" && stage !== "stimulus") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space" || e.key === "Enter") {
        e.preventDefault();
        handleResponse();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleResponse, stage]);

  // Cleanup on unmount
  React.useEffect(() => () => stopAllTimers(), [stopAllTimers]);

  // --- Countdown before first trial ---------------------------------------
  React.useEffect(() => {
    if (stage !== "countdown") return;
    if (countdown <= 0) {
      trialsRef.current = [];
      trialIndexRef.current = 0;
      sessionStartRef.current = performance.now();
      scheduleNextTrial();
      return;
    }
    const id = setTimeout(() => setCountdown((c: number) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [countdown, scheduleNextTrial, stage]);

  // --- Start / restart ----------------------------------------------------
  const startTest = React.useCallback(() => {
    resetSchedule();
    trialsRef.current = [];
    trialIndexRef.current = 0;
    setCountdown(3);
    setElapsedMs(0);
    setProgressPct(0);
    setMetrics(null);
    setStage("countdown");
  }, [resetSchedule]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {variant} — Psychomotor Vigilance Task
              <Badge variant="outline" className="ml-2">
                {variantDefaults.duration_min}-min
              </Badge>
            </CardTitle>
            <CardDescription>
              Press <kbd className="rounded border px-1.5 py-0.5 text-xs">Space</kbd>
              {" "}or tap as soon as the counter appears. Do not anticipate.
              Lapse threshold {variantDefaults.lapse_threshold_ms} ms.
            </CardDescription>
          </div>
          {stage !== "idle" && stage !== "instructions" && stage !== "done" && (
            <Badge className="whitespace-nowrap">{formatClock(elapsedMs, durationMs)}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {(stage === "idle" || stage === "instructions") && (
          <InstructionsPanel
            variant={variant}
            onStart={startTest}
          />
        )}

        {stage === "countdown" && (
          <CountdownPanel countdown={countdown} />
        )}

        {(stage === "waiting" || stage === "stimulus" || stage === "feedback") && (
          <StimulusPanel
            stage={stage}
            stimulusOnsetMs={stimulusOnsetRef.current}
            minimal={minimalStimulus}
            onClick={handleResponse}
            progressPct={progressPct}
            trialIndex={trialIndexRef.current}
            totalRough={Math.round(
              (durationMs /
                (((variantDefaults.isi_min_s + variantDefaults.isi_max_s) / 2) * 1000 + 500))
            )}
          />
        )}

        {stage === "done" && metrics && (
          <ResultsPanel metrics={metrics} onRestart={startTest} />
        )}
      </CardContent>
    </Card>
  );
}


// ---------------------------------------------------------------------------
// Sub-panels
// ---------------------------------------------------------------------------

function InstructionsPanel({ variant, onStart }: { variant: PVTVariant; onStart: () => void }) {
  const d = PVT_VARIANT_DEFAULTS[variant];
  return (
    <div className="space-y-4">
      <div className="rounded-md border bg-muted/50 p-4 text-sm leading-relaxed">
        <p className="mb-2 font-semibold">Instructions</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>The test runs for <strong>{d.duration_min} minutes</strong>.</li>
          <li>A millisecond counter will appear at random intervals
            ({d.isi_min_s}–{d.isi_max_s} s).</li>
          <li>When you see it, press <kbd>Space</kbd> (or tap) as fast as possible.</li>
          <li>Do not press before the counter appears — false starts are flagged.</li>
          <li>Responses ≥ {d.lapse_threshold_ms} ms count as <em>lapses</em>.</li>
          <li>Stay in a quiet place, with the browser window in focus, for the whole run.</li>
        </ul>
      </div>
      <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-50/60 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          <strong>Timing precision caveat.</strong> Browser-based PVT reaction-time
          measurement is precise to ≈ 5–10 ms (Anwyl-Irvine et al. 2020), adequate
          for operational and longitudinal tracking. For research-lab-grade timing,
          run the PsychoPy desktop variant — see <code>docs/PVT.md</code>.
        </span>
      </div>
      <Button size="lg" onClick={onStart} className="gap-2">
        <Play className="h-4 w-4" /> Start {variant}
      </Button>
    </div>
  );
}

function CountdownPanel({ countdown }: { countdown: number }) {
  return (
    <div className="flex h-64 items-center justify-center">
      <AnimatePresence mode="wait">
        <motion.div
          key={countdown}
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1.0, opacity: 1 }}
          exit={{ scale: 1.3, opacity: 0 }}
          transition={{ duration: 0.4 }}
          className="text-6xl font-bold tabular-nums"
        >
          {countdown > 0 ? countdown : "Go"}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function StimulusPanel(props: {
  stage: PVTTestStage;
  stimulusOnsetMs: number;
  minimal: boolean;
  onClick: () => void;
  progressPct: number;
  trialIndex: number;
  totalRough: number;
}) {
  const { stage, stimulusOnsetMs, minimal, onClick, progressPct, trialIndex, totalRough } = props;
  const [stimulusRtMs, setStimulusRtMs] = React.useState<number>(0);

  React.useEffect(() => {
    if (stage !== "stimulus") return;
    let raf = 0;
    const tick = () => {
      setStimulusRtMs(performance.now() - stimulusOnsetMs);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [stage, stimulusOnsetMs]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Trial {trialIndex + 1} / ~{totalRough}</span>
        <span>{Math.round(progressPct)}% complete</span>
      </div>
      <Progress value={progressPct} className="h-1" />
      <div
        onPointerDown={onClick}
        role="button"
        aria-label="Respond"
        tabIndex={0}
        className={
          "relative mx-auto flex h-72 w-full max-w-2xl cursor-pointer select-none items-center justify-center rounded-lg border-2 transition-colors " +
          (stage === "stimulus"
            ? "border-red-500 bg-red-50 dark:bg-red-950/30"
            : stage === "feedback"
              ? "border-emerald-500 bg-emerald-50/60 dark:bg-emerald-950/30"
              : "border-dashed border-muted-foreground/40 bg-muted/30")
        }
      >
        {stage === "waiting" && (
          <span className="text-sm text-muted-foreground">… wait …</span>
        )}
        {stage === "stimulus" && (
          minimal ? (
            <div className="h-24 w-24 rounded-full bg-red-500" />
          ) : (
            <div className="text-7xl font-bold tabular-nums text-red-600 dark:text-red-400">
              {Math.round(stimulusRtMs).toString().padStart(3, "0")}
            </div>
          )
        )}
        {stage === "feedback" && (
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="h-6 w-6" /> <span>Response recorded</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ResultsPanel({ metrics, onRestart }: { metrics: PVTMetrics; onRestart: () => void }) {
  const gate = operationalGate(metrics);
  const decisionColour: Record<string, string> = {
    GO: "text-emerald-600 dark:text-emerald-400",
    GO_MONITOR: "text-lime-600 dark:text-lime-400",
    CAUTION: "text-amber-600 dark:text-amber-400",
    NO_GO: "text-red-600 dark:text-red-400",
  };

  const fmtMs = (v: number | null) => (v === null ? "—" : `${v.toFixed(0)} ms`);
  const fmtNum = (v: number | null, digits = 2) =>
    v === null ? "—" : v.toFixed(digits);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Operational decision</p>
          <p className={"text-3xl font-bold " + (decisionColour[gate.decision] ?? "")}>
            {gate.decision.replace("_", " ")}
          </p>
        </div>
        <Badge variant="outline" className="text-base">
          pvt_lapses_3min = {metrics.pvt_lapses_3min}
        </Badge>
      </div>

      {gate.reasons.length > 0 && (
        <ul className="list-disc rounded-md bg-muted/50 p-3 pl-8 text-xs">
          {gate.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricTile label="Valid trials" value={metrics.n_valid_trials.toString()} />
        <MetricTile label="Lapses" value={metrics.n_lapses.toString()} />
        <MetricTile label="False starts" value={metrics.n_false_starts.toString()} />
        <MetricTile label="Major lapses" value={metrics.n_major_lapses.toString()} />
        <MetricTile label="Mean RT" value={fmtMs(metrics.mean_rt_ms)} />
        <MetricTile label="Median RT" value={fmtMs(metrics.median_rt_ms)} />
        <MetricTile label="Fastest-10% RT" value={fmtMs(metrics.fastest_10pct_mean_rt_ms)} />
        <MetricTile label="Slowest-10% RT" value={fmtMs(metrics.slowest_10pct_mean_rt_ms)} />
        <MetricTile label="SD RT" value={fmtMs(metrics.sd_rt_ms)} />
        <MetricTile label="CV RT" value={fmtNum(metrics.cv_rt, 3)} />
        <MetricTile label="Mean 1/RT (s⁻¹)" value={fmtNum(metrics.mean_response_speed_per_s, 3)} />
        <MetricTile label="Transformed lapses" value={fmtNum(metrics.transformed_lapses, 2)} />
      </div>

      <Button onClick={onRestart} variant="outline" className="gap-2">
        <RotateCcw className="h-4 w-4" /> Run again
      </Button>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-card p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatClock(elapsedMs: number, totalMs: number): string {
  const remain = Math.max(0, totalMs - elapsedMs);
  const s = Math.ceil(remain / 1000);
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${mm}:${ss.toString().padStart(2, "0")}`;
}
