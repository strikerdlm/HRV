// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity,
  Calendar,
  Database,
  Gauge,
  Globe,
  Info,
  Github,
  Layers,
  LineChart,
  Microscope,
  Radar,
  Stethoscope,
  Workflow,
  Shield,
  BookOpen,
  ExternalLink,
  ArrowRight,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
import {
  APP_VERSION,
  APP_VERSION_DATE,
  PYTHON_VERSION,
  FRONTEND_FRAMEWORK,
  API_PORT,
  FRONTEND_PORT,
} from "@/lib/version";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const operationalCapabilities = [
  {
    title: "Crew Readiness Console",
    description:
      "Mission-level readiness scoring with physiological, fatigue, and environmental context for operational decision support.",
    icon: Gauge,
    href: "/scheduling/readiness",
  },
  {
    title: "Scheduling and Risk Control",
    description:
      "FRMS-oriented crew scheduling with fatigue-aware planning, conflict checks, and shift-level safety framing.",
    icon: Shield,
    href: "/scheduling",
  },
  {
    title: "Space Weather and Environment",
    description:
      "Operational monitoring using NOAA/NASA context to support timing and interpretation under geomagnetic and atmospheric stressors.",
    icon: Globe,
    href: "/",
  },
  {
    title: "Scientific Analytics Layer",
    description:
      "Deep research modules remain directly available for advanced review, model interpretation, and publication workflows.",
    icon: Microscope,
    href: "/research",
  },
];

const technologies = [
  { name: "Next.js 16", category: "Frontend" },
  { name: "TypeScript", category: "Language" },
  { name: "Tailwind CSS", category: "Styling" },
  { name: "shadcn/ui", category: "Components" },
  { name: "Framer Motion", category: "Animation" },
  { name: "Apache ECharts", category: "Visualization" },
  { name: "FastAPI", category: "Backend" },
  { name: "Python 3.12", category: "Runtime" },
  { name: "SQLite", category: "Database" },
  { name: "Zustand", category: "State" },
];

const operationalWorkflow = [
  {
    title: "Ingest",
    description:
      "Collect user, wearable, RR, and environment signals into a unified operational context.",
    icon: Database,
  },
  {
    title: "Analyze",
    description:
      "Compute readiness, trend trajectories, and risk indicators with bounded deterministic pipelines.",
    icon: LineChart,
  },
  {
    title: "Decide",
    description:
      "Support mission planning with scheduling constraints, fatigue controls, and safety thresholds.",
    icon: Workflow,
  },
  {
    title: "Monitor",
    description:
      "Track response over time and update decisions as crew physiology and environment evolve.",
    icon: Radar,
  },
];

const integrations = [
  {
    name: "Physiological Data",
    detail: "HRV streams, RR tracing ingestion, Garmin-linked context, and readiness modifiers.",
  },
  {
    name: "Environmental Signals",
    detail: "NOAA and NASA space weather feeds, plus local weather overlays for operational interpretation.",
  },
  {
    name: "Scheduling Context",
    detail: "Crew workload blocks, duty-cycle planning, and risk-aware activity timing.",
  },
];

const references = [
  {
    title: "Task Force HRV Standards",
    citation:
      "Task Force of ESC/NASPE. (1996). Heart rate variability standards. Circulation, 93(5), 1043-1065.",
    pmid: "8598068",
  },
  {
    title: "HRV Overview & Norms",
    citation:
      "Shaffer, F., & Ginsberg, J. P. (2017). An overview of HRV metrics and norms. Front Public Health, 5, 258.",
    pmid: "29034226",
  },
  {
    title: "Normal HRV Values",
    citation:
      "Nunan, D., et al. (2010). Normal values for short-term HRV in healthy adults. Pacing Clin Electrophysiol, 33(11), 1407-1417.",
    pmid: "20663071",
  },
  {
    title: "SAFTE Biomathematical Fatigue Model",
    citation:
      "Hursh, S. R., et al. (2004). Fatigue models for applied research in warfighting. Aviation, Space, and Environmental Medicine, 75(3 Suppl), A44-A53.",
    pmid: "15018270",
  },
];

interface ChangelogCategory {
  category: string;
  items: string[];
}

interface ChangelogReleaseSummary {
  version: string;
  date: string;
  categories: ChangelogCategory[];
}

interface ChangelogApiResponse {
  ok: boolean;
  release: ChangelogReleaseSummary | null;
  error?: string;
}

export default function AboutPage() {
  const [latestRelease, setLatestRelease] = React.useState<ChangelogReleaseSummary | null>(null);
  const [changelogError, setChangelogError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const loadChangelog = async () => {
      try {
        const response = await fetch("/api/about/changelog", {
          method: "GET",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const payload = (await response.json()) as ChangelogApiResponse;
        if (!cancelled && payload.ok) {
          setLatestRelease(payload.release);
          setChangelogError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setChangelogError(
            error instanceof Error ? error.message : "Unable to load changelog summary.",
          );
        }
      }
    };
    void loadChangelog();
    return () => {
      cancelled = true;
    };
  }, []);

  const displayedVersion = latestRelease?.version || APP_VERSION;
  const displayedDate = latestRelease?.date || APP_VERSION_DATE;

  return (
    <PageWrapper
      title="About Operational Frontend"
      description="Mission Control - Flight Surgeon Operational Layer"
    >
      <div className="space-y-6 max-w-6xl">
        {/* Mission Brief */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <CardHeader className="space-y-4">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="flex items-start gap-4">
                  <div className="h-14 w-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                    <Stethoscope className="h-7 w-7 text-primary" />
                  </div>
                  <div className="space-y-2">
                    <CardTitle className="text-xl md:text-2xl">
                      Mission Control - Flight Surgeon
                    </CardTitle>
                    <CardDescription className="max-w-2xl">
                      Operational decision support interface for aerospace medicine,
                      crew readiness, and mission scheduling in high-risk environments.
                    </CardDescription>
                    <div className="flex flex-wrap gap-2">
                      <Badge>Operational</Badge>
                      <Badge variant="outline">Clinical Oversight</Badge>
                      <Badge variant="outline">Research-Linked</Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="icon" asChild>
                    <a
                      href="https://github.com/strikerdlm/HRV"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Github className="h-4 w-4" />
                    </a>
                  </Button>
                  <Button variant="secondary" asChild>
                    <Link href="/">
                      Open Dashboard
                      <ArrowRight className="h-4 w-4 ml-1" />
                    </Link>
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-muted-foreground">
                Led by <strong>Dr Diego Malpica MD</strong> as a mission-oriented
                platform for translating physiological and environmental signals
                into practical crew operations.
              </p>
              <p className="text-sm text-muted-foreground">
                The operational frontend prioritizes rapid comprehension,
                risk-aware planning, and explainable outputs that are suitable
                for both field use and scientific review.
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Operational Capabilities */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Latest Release Capabilities by Category
              </CardTitle>
              <CardDescription>
                Auto-read from <code>CHANGELOG.md</code> so this page stays synchronized with release notes.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">Version {displayedVersion}</Badge>
                <Badge variant="outline">Updated {displayedDate}</Badge>
              </div>
              {latestRelease && latestRelease.categories.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  {latestRelease.categories.map((section) => (
                    <div key={section.category} className="rounded-lg border bg-muted/20 p-4 space-y-2">
                      <h4 className="text-sm font-semibold">{section.category}</h4>
                      {section.items.length > 0 ? (
                        <ul className="space-y-1 text-xs text-muted-foreground">
                          {section.items.slice(0, 8).map((item) => (
                            <li key={`${section.category}-${item}`} className="leading-relaxed">
                              - {item}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-muted-foreground">No capability entries in this section.</p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border bg-muted/20 p-4">
                  <p className="text-xs text-muted-foreground">
                    {changelogError
                      ? `Changelog read failed: ${changelogError}`
                      : "Changelog summary is loading or unavailable."}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Operational Capabilities</CardTitle>
              <CardDescription>
                Core modules used for day-to-day mission support
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {operationalCapabilities.map((item, index) => (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 + index * 0.08 }}
                    className="rounded-lg border bg-muted/30 p-4 flex flex-col gap-3"
                  >
                    <div className="flex items-start gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                        <item.icon className="h-5 w-5 text-primary" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-sm font-semibold">{item.title}</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {item.description}
                        </p>
                      </div>
                    </div>
                    <div>
                      <Button size="sm" variant="outline" asChild>
                        <Link href={item.href}>
                          Open module
                          <ArrowRight className="h-4 w-4 ml-1" />
                        </Link>
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Workflow + Integrations */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
        >
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Workflow className="h-5 w-5" />
                  Operational Workflow
                </CardTitle>
                <CardDescription>
                  Standard cycle used by the frontend for mission support
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {operationalWorkflow.map((step, index) => (
                  <div
                    key={step.title}
                    className="rounded-lg border bg-muted/20 p-3 flex gap-3"
                  >
                    <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
                      <step.icon className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-wide text-muted-foreground">
                        Step {index + 1}
                      </p>
                      <h4 className="text-sm font-semibold">{step.title}</h4>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        {step.description}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Data Integrations
                </CardTitle>
                <CardDescription>
                  Operational context fused across physiology, environment, and duty constraints
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {integrations.map((item) => (
                  <div key={item.name} className="rounded-lg border bg-muted/20 p-3">
                    <h4 className="text-sm font-semibold">{item.name}</h4>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                      {item.detail}
                    </p>
                  </div>
                ))}
                <Separator />
                <div className="flex flex-wrap gap-2">
                  {technologies.map((tech) => (
                    <Badge key={tech.name} variant="outline" className="py-1">
                      {tech.name}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* Version + Scientific References */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="h-5 w-5" />
                  Runtime and Release Information
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Version</p>
                  <p className="font-mono font-semibold">{displayedVersion}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Last Updated</p>
                  <p className="font-mono font-semibold">{displayedDate}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Frontend</p>
                  <p className="font-mono font-semibold">{FRONTEND_FRAMEWORK}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Python</p>
                  <p className="font-mono font-semibold">{PYTHON_VERSION}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">API Port</p>
                  <p className="font-mono font-semibold">{API_PORT}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Frontend Port</p>
                  <p className="font-mono font-semibold">{FRONTEND_PORT}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">License</p>
                  <p className="font-mono font-semibold">MIT</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Backend</p>
                  <p className="font-mono font-semibold">FastAPI</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Scientific Foundation
                </CardTitle>
                <CardDescription>
                  Core references that ground the operational interpretation layer
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {references.map((ref, index) => (
                  <div key={ref.pmid} className="space-y-1">
                    <h4 className="font-medium text-sm">{ref.title}</h4>
                    <p className="text-xs text-muted-foreground">{ref.citation}</p>
                    <a
                      href={`https://pubmed.ncbi.nlm.nih.gov/${ref.pmid}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      PMID: {ref.pmid}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                    {index < references.length - 1 && (
                      <Separator className="mt-3" />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.45 }}
          className="text-center text-sm text-muted-foreground py-4"
        >
          <p>
            Mission Control - Flight Surgeon © {new Date().getFullYear()} Dr
            Diego Malpica MD
          </p>
          <p className="mt-1">
            Operational frontend for mission readiness, scheduling, and physiological oversight
          </p>
          <div className="mt-3 flex items-center justify-center gap-2">
            <Button size="sm" variant="outline" asChild>
              <Link href="/scheduling">
                <Calendar className="h-4 w-4 mr-1" />
                Open Scheduling
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/research">
                <Activity className="h-4 w-4 mr-1" />
                Open Research Modules
              </Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
