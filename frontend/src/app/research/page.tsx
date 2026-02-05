// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Sun,
  Activity,
  GitCompare,
  Watch,
  Heart,
  Zap,
  TrendingUp,
  AlertTriangle,
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

const researchModules = [
  {
    id: "space-weather",
    title: "Space Weather Dashboard",
    description:
      "Real-time NOAA/NASA data with Kp, Dst, F10.7, solar wind, and impact predictions",
    icon: Sun,
    href: "/research/space-weather",
    color: "text-warning",
    bgColor: "bg-warning/10",
    features: ["Live Kp Index", "CME Arrivals", "Polar H10 Timing"],
  },
  {
    id: "hrv-analysis",
    title: "HRV Analysis",
    description:
      "Comprehensive time, frequency, nonlinear, and HRF domain analysis",
    icon: Activity,
    href: "/research/hrv-analysis",
    color: "text-danger",
    bgColor: "bg-danger/10",
    features: ["SDNN/RMSSD", "LF/HF Power", "DFA α1", "Fragmentation"],
  },
  {
    id: "vt-estimation",
    title: "Ventilatory Threshold",
    description:
      "DFA-α1 based aerobic/anaerobic threshold estimation — experimental multi-parameter detection",
    icon: TrendingUp,
    href: "/research/ventilatory-threshold",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10",
    features: ["DFA-α1", "VT1/VT2", "Intensity Zones", "Multi-Parameter"],
  },
  {
    id: "correlations",
    title: "Solar-HRV Correlations",
    description:
      "Analyze relationships between space weather and physiological parameters",
    icon: GitCompare,
    href: "/research/correlations",
    color: "text-primary",
    bgColor: "bg-primary/10",
    features: ["Lag Analysis", "Significance Testing", "ML Patterns"],
  },
  {
    id: "garmin",
    title: "Garmin Integration",
    description:
      "SpO2, respiration, VO2max, sleep architecture, body battery analysis",
    icon: Watch,
    href: "/research/garmin",
    color: "text-success",
    bgColor: "bg-success/10",
    features: ["Sleep Metrics", "SpO2 Trends", "Stress Analysis"],
  },
];

const scientificHighlights = [
  {
    title: "Geomagnetic Activity & HRV",
    citation: "Alabdulgader et al., 2018",
    finding:
      "Long-term HRV responses to solar activity show correlations with Kp index.",
  },
  {
    title: "Solar Wind & Cardiovascular",
    citation: "Stoupel et al., 2008",
    finding:
      "Space proton flux correlates with temporal distribution of cardiovascular events.",
  },
  {
    title: "Heart Rate Fragmentation",
    citation: "PROOF-AF Study, 2025",
    finding:
      "HRF metrics (PIP, IALS) predict atrial fibrillation independently of traditional HRV.",
  },
  {
    title: "DFA-α1 Ventilatory Thresholds",
    citation: "Eronen et al., 2024",
    finding:
      "Multi-parameter HRV algorithm achieves VT2 correlation r=0.93 vs CPET gold standard (n=64).",
  },
];

function ModuleCard({
  module,
  index,
}: {
  module: (typeof researchModules)[0];
  index: number;
}) {
  const Icon = module.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Link href={module.href}>
        <Card className="h-full hover:shadow-lg transition-all cursor-pointer group">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className={`p-3 rounded-xl ${module.bgColor}`}>
                <Icon className={`h-6 w-6 ${module.color}`} />
              </div>
              <Badge variant="outline" className="group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                Explore →
              </Badge>
            </div>
            <CardTitle className="mt-4">{module.title}</CardTitle>
            <CardDescription>{module.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {module.features.map((feature) => (
                <Badge key={feature} variant="secondary" className="text-xs">
                  {feature}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
}

export default function ResearchPage() {
  return (
    <PageWrapper
      title="Research Dashboard"
      description="Solar-Physiological Analytics"
    >
      <div className="space-y-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary/10 via-background to-warning/10 p-8"
        >
          <div className="relative z-10">
            <h2 className="text-2xl font-bold mb-2">
              Space Weather & Human Physiology
            </h2>
            <p className="text-muted-foreground max-w-2xl">
              Explore the scientific relationship between solar activity and
              cardiovascular function. Analyze HRV correlations with
              geomagnetic storms, solar wind, and cosmic radiation using
              evidence-based methods.
            </p>
            <div className="flex gap-3 mt-4">
              <Button asChild>
                <Link href="/research/space-weather">
                  <Sun className="h-4 w-4 mr-2" />
                  View Space Weather
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/research/correlations">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  Run Correlation Analysis
                </Link>
              </Button>
            </div>
          </div>
          <div className="absolute top-0 right-0 opacity-10">
            <Sun className="h-64 w-64 -mr-16 -mt-16" />
          </div>
        </motion.div>

        {/* Module Cards */}
        <div className="grid gap-6 md:grid-cols-2">
          {researchModules.map((module, index) => (
            <ModuleCard key={module.id} module={module} index={index} />
          ))}
        </div>

        {/* Scientific Background */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-warning" />
                Scientific Background
              </CardTitle>
              <CardDescription>
                Evidence-based foundations for solar-physiological research
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {scientificHighlights.map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + index * 0.1 }}
                    className="p-4 rounded-lg bg-muted/50"
                  >
                    <h4 className="font-medium text-sm">{item.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      {item.finding}
                    </p>
                    <Badge variant="outline" className="mt-2 text-xs">
                      {item.citation}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          {[
            { label: "NOAA Sources", value: "8+", icon: Sun },
            { label: "HRV Metrics", value: "40+", icon: Heart },
            { label: "Lag Analysis", value: "0-72h", icon: TrendingUp },
            { label: "Garmin Params", value: "20+", icon: Watch },
          ].map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.7 + index * 0.05 }}
            >
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <stat.icon className="h-5 w-5 text-muted-foreground" />
                    <div>
                      <p className="text-2xl font-bold">{stat.value}</p>
                      <p className="text-xs text-muted-foreground">
                        {stat.label}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </PageWrapper>
  );
}
