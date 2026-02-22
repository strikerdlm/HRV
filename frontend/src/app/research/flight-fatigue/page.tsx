// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Plane, RefreshCw } from "lucide-react";
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
import { QualityPanel } from "@/components/research/quality-panel";
import { getFlightFatigueClassification } from "@/lib/research-api";
import { useAppStore } from "@/lib/store";
import type { FlightFatigueResponse } from "@/types/research";

const DEFAULT_USER_ID = "demo-user";

function probabilityOption(data: FlightFatigueResponse): Record<string, unknown> {
  const labels: Array<"low" | "moderate" | "high"> = ["low", "moderate", "high"];
  return {
    grid: { left: 50, right: 20, top: 30, bottom: 40, containLabel: true },
    xAxis: {
      type: "category",
      data: labels.map((k) => k.toUpperCase()),
      axisLabel: { color: "#1a1a1a" },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: 1,
      axisLabel: { color: "#1a1a1a", formatter: (v: number) => `${Math.round(v * 100)}%` },
    },
    tooltip: { trigger: "axis" },
    series: [
      {
        type: "bar",
        barWidth: "50%",
        data: labels.map((k) => ({
          value: data.probabilities[k] ?? 0,
          itemStyle: {
            color:
              k === "low"
                ? SCIENTIFIC_COLORS.success
                : k === "moderate"
                  ? SCIENTIFIC_COLORS.warning
                  : SCIENTIFIC_COLORS.danger,
          },
        })),
        label: {
          show: true,
          position: "top",
          color: "#1a1a1a",
          formatter: (p: { value: number }) => `${Math.round(p.value * 100)}%`,
        },
      },
    ],
  };
}

export default function FlightFatiguePage() {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState<FlightFatigueResponse | null>(null);

  const activeUserId = useAppStore((state) => state.activeUserId);
  const userId = activeUserId ?? DEFAULT_USER_ID;

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const out = await getFlightFatigueClassification(userId);
      setData(out);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  React.useEffect(() => {
    void fetchData();
  }, [fetchData]);

  return (
    <PageWrapper
      title="Flight Fatigue Classifier"
      description="Three-level fatigue band for flight operations with feature transparency"
    >
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-3"
        >
          <div className="flex items-center gap-2">
            {data && (
              <>
                <Badge
                  variant={
                    data.risk_band === "low"
                      ? "success"
                      : data.risk_band === "moderate"
                        ? "warning"
                        : "destructive"
                  }
                  title="Top-probability class from calibrated multifeature fatigue scoring"
                >
                  Risk band: {data.risk_band.toUpperCase()}
                </Badge>
                <Badge
                  variant="outline"
                  title="Current backend classifier version"
                >
                  Model: {data.model_version}
                </Badge>
              </>
            )}
          </div>
          <Button onClick={() => void fetchData()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </motion.div>

        {data && (
          <QualityPanel
            context={data.context}
            showFrequencyDetails={false}
            extraCaveats={[
              "Flight-fatigue output uses calibrated proxy scoring; external retraining on mission-specific cohorts is still pending.",
            ]}
          />
        )}

        {data && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plane className="h-5 w-5 text-primary" />
                Classifier Probabilities
              </CardTitle>
              <CardDescription>
                Distribution across low/moderate/high fatigue classes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EChartsWrapper option={probabilityOption(data)} height={300} />
            </CardContent>
          </Card>
        )}

        {data && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Model Rationale</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.rationale.map((item) => (
                  <p key={item} className="text-sm text-muted-foreground">
                    - {item}
                  </p>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Feature Availability</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-xs text-muted-foreground">Required features</p>
                <div className="flex flex-wrap gap-2">
                  {data.required_features.map((feature) => (
                    <Badge key={feature} variant="outline">{feature}</Badge>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-3">Missing features</p>
                {data.missing_features.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {data.missing_features.map((feature) => (
                      <Badge key={feature} variant="warning">{feature}</Badge>
                    ))}
                  </div>
                ) : (
                  <Badge variant="success">All required features present</Badge>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {data && (
          <Card>
            <CardHeader>
              <CardTitle>How to Interpret the Classifier</CardTitle>
              <CardDescription>
                Use this output as operational decision support with explicit feature-coverage checks.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                - <strong>Class probabilities</strong> represent relative support for low/moderate/high fatigue in the current input context.
              </p>
              <p>
                - <strong>Risk band</strong> is the top class, but confidence is stronger when probability separation is wide.
              </p>
              <p>
                - <strong>Missing features</strong> trigger neutralization behavior; treat outputs as conservative fallback when coverage is incomplete.
              </p>
              <p>
                - <strong>Proxy model notice</strong>: current version remains a transparent proxy (`lightgbm_proxy_v1`) while full calibrated feature sets are phased in.
              </p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Scientific References</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground space-y-2">
            <p>
              - Guo D et al. (2025). Three-level flight fatigue classification from HRV and respiratory features.
              <span className="ml-1 text-primary">doi:10.3389/fnins.2025.1621638</span>
            </p>
            <p>
              - Yuan Y et al. (2025). Pilot workload feature selection and model performance in A320 traffic patterns.
              <span className="ml-1 text-primary">doi:10.3389/fnrgo.2025.1672492</span>
            </p>
            <p>
              - Task Force of ESC/NASPE (1996). HRV acquisition and interpretation standards.
              <span className="ml-1 text-primary">doi:10.1161/01.CIR.93.5.1043</span>
            </p>
          </CardContent>
        </Card>
      </div>
    </PageWrapper>
  );
}

