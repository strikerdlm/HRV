// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AnalysisContext } from "@/types/research";

interface QualityPanelProps {
  context?: AnalysisContext;
  showFrequencyDetails?: boolean;
  extraCaveats?: string[];
}

function confidenceVariant(
  confidence: AnalysisContext["confidence"] | undefined,
): "success" | "warning" | "destructive" | "outline" {
  if (confidence === "good") return "success";
  if (confidence === "moderate") return "warning";
  if (confidence === "poor") return "destructive";
  return "outline";
}

export function QualityPanel({
  context,
  showFrequencyDetails = true,
  extraCaveats = [],
}: QualityPanelProps) {
  const caveats = React.useMemo(() => {
    const base = [
      "HF power is unreliable under motion or irregular respiration.",
      "Frequency-domain inference assumes local stationarity; invalid windows should be gated.",
      "LF/HF is confounded by respiration and exertion; interpret as heuristic rather than direct sympathovagal balance.",
    ];
    return [...base, ...extraCaveats];
  }, [extraCaveats]);

  if (!context) {
    return (
      <Card className="border-dashed">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Info className="h-4 w-4 text-muted-foreground" />
            Quality & Protocol Context
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No context metadata received from backend yet. Interpret outputs cautiously.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="text-sm flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-primary" />
            Quality & Protocol Context
          </CardTitle>
          <Badge variant={confidenceVariant(context.confidence)}>
            Confidence: {context.confidence}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm">
          {context.stationarity.passed ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-red-600" />
          )}
          <span>
            Stationarity:{" "}
            <strong>{context.stationarity.passed ? "pass" : "fail"}</strong>{" "}
            ({context.stationarity.reason})
          </span>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="outline">Device: {context.device_type}</Badge>
          <Badge variant="outline">Posture: {context.posture}</Badge>
          <Badge variant="outline">
            Artifacts flagged: {context.preprocessing.pct_flagged.toFixed(1)}%
          </Badge>
          <Badge variant="outline">
            Recording: {context.recording_window_sec ?? "—"}s
          </Badge>
        </div>

        {showFrequencyDetails && context.frequency_validity.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-foreground">
              Frequency Method Validity
            </p>
            <div className="flex flex-wrap gap-2">
              {context.frequency_validity.map((item) => (
                <Badge
                  key={`${item.method}-${item.valid}`}
                  variant={item.valid ? "success" : "warning"}
                  className="text-[11px]"
                >
                  {item.method.toUpperCase()} {item.valid ? "valid" : "gated"} ·{" "}
                  {(item.score * 100).toFixed(0)}%
                </Badge>
              ))}
            </div>
          </div>
        )}

        {context.confidence_reasons.length > 0 && (
          <ul className="space-y-1 text-xs text-muted-foreground">
            {context.confidence_reasons.map((reason) => (
              <li key={reason}>- {reason}</li>
            ))}
          </ul>
        )}

        <div className="pt-2 border-t">
          <p className="text-xs font-semibold text-foreground mb-1">Interpretation caveats</p>
          <ul className="space-y-1 text-xs text-muted-foreground">
            {caveats.map((c) => (
              <li key={c}>- {c}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

