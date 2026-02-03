// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Heart,
  Wind,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  XCircle,
  Info,
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
import { EChartsWrapper, SCIENTIFIC_COLORS } from "@/components/charts";

interface ANSTestResult {
  name: string;
  value: number | null;
  normalRange: [number, number];
  unit: string;
  status: "normal" | "borderline" | "abnormal";
  description: string;
  interpretation: string;
}

// Demo test results
const demoTests: ANSTestResult[] = [
  {
    name: "30:15 Ratio",
    value: 1.18,
    normalRange: [1.04, 1.5],
    unit: "",
    status: "normal",
    description: "Ratio of longest RR around beat 30 to shortest RR around beat 15 after standing",
    interpretation: "Normal vagal response to orthostatic challenge",
  },
  {
    name: "Valsalva Ratio",
    value: 1.42,
    normalRange: [1.21, 2.0],
    unit: "",
    status: "normal",
    description: "Ratio of max HR during strain to min HR after release",
    interpretation: "Normal baroreceptor-mediated response",
  },
  {
    name: "E:I Ratio (Deep Breathing)",
    value: 1.28,
    normalRange: [1.2, 1.8],
    unit: "",
    status: "normal",
    description: "Ratio of longest to shortest RR during paced deep breathing (6 breaths/min)",
    interpretation: "Normal respiratory sinus arrhythmia",
  },
];

// Test Result Gauge - Clean minimal design following plot rules
function TestGauge({ test }: { test: ANSTestResult }) {
  const value = test.value ?? 0;
  const hasData = test.value !== null;
  const [min, max] = test.normalRange;
  const gaugeMax = max * 1.5;

  const getColor = () => {
    switch (test.status) {
      case "normal":
        return SCIENTIFIC_COLORS.success;
      case "borderline":
        return SCIENTIFIC_COLORS.warning;
      case "abnormal":
        return SCIENTIFIC_COLORS.danger;
      default:
        return "#94a3b8";
    }
  };

  const option: Record<string, unknown> = {
    series: [
      {
        type: "gauge",
        center: ["50%", "68%"],
        radius: "95%",
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: gaugeMax,
        axisLine: {
          lineStyle: {
            width: 16,
            color: [
              [min / gaugeMax, SCIENTIFIC_COLORS.danger],
              [max / gaugeMax, SCIENTIFIC_COLORS.success],
              [1, SCIENTIFIC_COLORS.warning],
            ],
          },
        },
        pointer: {
          length: "68%",
          width: 5,
          offsetCenter: [0, "5%"],
          itemStyle: {
            color: hasData ? getColor() : "#94a3b8",
            shadowColor: "rgba(0, 0, 0, 0.25)",
            shadowBlur: 6,
            shadowOffsetY: 2,
          },
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 14,
          itemStyle: {
            borderWidth: 3,
            borderColor: hasData ? getColor() : "#94a3b8",
            color: "#fff",
            shadowColor: "rgba(0, 0, 0, 0.15)",
            shadowBlur: 4,
          },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          show: true,
          distance: -28,
          color: "#1a1a1a",
          fontSize: 10,
          fontWeight: "600",
          formatter: (v: number) => {
            // Only show min, normal range boundaries, and max
            const tolerance = gaugeMax * 0.05;
            if (Math.abs(v) < tolerance) return "0";
            if (Math.abs(v - min) < tolerance) return min.toFixed(1);
            if (Math.abs(v - max) < tolerance) return max.toFixed(1);
            if (Math.abs(v - gaugeMax) < tolerance) return gaugeMax.toFixed(1);
            return "";
          },
        },
        progress: {
          show: true,
          overlap: false,
          roundCap: true,
          clip: false,
        },
        detail: {
          valueAnimation: true,
          formatter: () => (hasData ? value.toFixed(2) : "—"),
          fontSize: 26,
          fontWeight: "bold",
          fontFamily: "system-ui, -apple-system, sans-serif",
          color: hasData ? getColor() : "#94a3b8",
          offsetCenter: [0, "32%"],
        },
        data: [{ value }],
      },
    ],
  };

  return <EChartsWrapper option={option} height={180} showToolbox={false} />;
}

// Status Icon
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "normal":
      return <CheckCircle className="h-5 w-5 text-success" />;
    case "borderline":
      return <AlertCircle className="h-5 w-5 text-warning" />;
    case "abnormal":
      return <XCircle className="h-5 w-5 text-danger" />;
    default:
      return null;
  }
}

// Test Card
function TestCard({ test }: { test: ANSTestResult }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            {test.name === "30:15 Ratio" && <Activity className="h-5 w-5 text-primary" />}
            {test.name === "Valsalva Ratio" && <Wind className="h-5 w-5 text-info" />}
            {test.name === "E:I Ratio (Deep Breathing)" && <Heart className="h-5 w-5 text-success" />}
            {test.name}
          </CardTitle>
          <Badge
            variant={test.status === "normal" ? "success" : test.status === "borderline" ? "warning" : "destructive"}
            className="flex items-center gap-1"
          >
            <StatusIcon status={test.status} />
            {test.status.charAt(0).toUpperCase() + test.status.slice(1)}
          </Badge>
        </div>
        <CardDescription>{test.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <TestGauge test={test} />
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Normal Range:</span>
            <span className="font-medium">{test.normalRange[0]} – {test.normalRange[1]} {test.unit}</span>
          </div>
          <div className="p-3 rounded-lg bg-muted/50">
            <p className="text-sm text-muted-foreground">{test.interpretation}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// Overall Summary
function OverallSummary({ tests }: { tests: ANSTestResult[] }) {
  const normalCount = tests.filter((t) => t.status === "normal").length;
  const borderlineCount = tests.filter((t) => t.status === "borderline").length;
  const abnormalCount = tests.filter((t) => t.status === "abnormal").length;

  const overall =
    abnormalCount > 0 ? "abnormal" : borderlineCount > 1 ? "borderline" : normalCount === tests.length ? "normal" : "borderline";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Overall Autonomic Function
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <div
            className={`p-4 rounded-full ${
              overall === "normal" ? "bg-success/10" : overall === "borderline" ? "bg-warning/10" : "bg-danger/10"
            }`}
          >
            <StatusIcon status={overall} />
          </div>
          <div>
            <p className="text-lg font-bold">
              {overall === "normal" ? "Normal Autonomic Function" : overall === "borderline" ? "Borderline Findings" : "Abnormal Findings"}
            </p>
            <p className="text-sm text-muted-foreground">
              {normalCount}/{tests.length} tests normal
            </p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div className="text-center p-3 rounded-lg border border-success/30 bg-success/5">
            <p className="text-2xl font-bold text-success">{normalCount}</p>
            <p className="text-xs text-muted-foreground">Normal</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-warning/30 bg-warning/5">
            <p className="text-2xl font-bold text-warning">{borderlineCount}</p>
            <p className="text-xs text-muted-foreground">Borderline</p>
          </div>
          <div className="text-center p-3 rounded-lg border border-danger/30 bg-danger/5">
            <p className="text-2xl font-bold text-danger">{abnormalCount}</p>
            <p className="text-xs text-muted-foreground">Abnormal</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ANSTestsPage() {
  const [tests, setTests] = React.useState<ANSTestResult[]>(demoTests);
  const [loading, setLoading] = React.useState(false);

  return (
    <PageWrapper
      title="ANS Function Tests"
      description="Autonomic Nervous System Reflex Testing"
    >
      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between flex-wrap gap-4"
        >
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="flex items-center gap-1">
              <Activity className="h-3 w-3" />
              {tests.length} Tests
            </Badge>
          </div>
          <Button disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Run Tests
          </Button>
        </motion.div>

        {/* Overall Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <OverallSummary tests={tests} />
        </motion.div>

        {/* Individual Tests */}
        <div className="grid gap-6 lg:grid-cols-3">
          {tests.map((test, idx) => (
            <motion.div
              key={test.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + idx * 0.1 }}
            >
              <TestCard test={test} />
            </motion.div>
          ))}
        </div>

        {/* Protocol Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5 text-info" />
                Test Protocols
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-4">
              <div>
                <p className="font-medium text-foreground">30:15 Ratio (Lying-to-Standing)</p>
                <p>After 5 min supine rest, patient stands quickly. Compare RR interval at beat 30 (longest, vagal overshoot) to beat 15 (shortest, initial response).</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Valsalva Maneuver</p>
                <p>Forced expiration against closed glottis (40 mmHg, 15 sec). Measures baroreflex sensitivity via HR changes during and after strain.</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Deep Breathing E:I Ratio</p>
                <p>Paced breathing at 6 breaths/min (5s in, 5s out) for 1 minute. Maximum HR-minimum HR difference reflects respiratory sinus arrhythmia.</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* References */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Scientific References</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
              <p>
                • Ewing DJ et al. (1985). The value of cardiovascular autonomic function tests: 10 years
                experience in diabetes.
                <span className="ml-1 text-primary">Diabetes Care, 8(5), 491-8.</span>
              </p>
              <p>
                • Low PA (1993). Composite autonomic scoring scale for laboratory quantification of
                generalized autonomic failure.
                <span className="ml-1 text-primary">Mayo Clin Proc, 68(8), 748-52.</span>
              </p>
              <p>
                • Freeman R et al. (2011). Consensus statement on the definition of orthostatic hypotension,
                neurally mediated syncope and the postural tachycardia syndrome.
                <span className="ml-1 text-primary">Clin Auton Res, 21(2), 69-72.</span>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
