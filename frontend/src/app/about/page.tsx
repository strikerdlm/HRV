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
  Watch,
  Timer,
  Moon,
  Bed,
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
    title: "Home Dashboard & Space Weather",
    description:
      "Crew snapshot, IHPI-style gauges, and live NOAA/NASA space-weather context for operational timing and risk awareness.",
    icon: Globe,
    href: "/",
  },
  {
    title: "Crew Readiness Console",
    description:
      "Mission-level readiness scoring with physiological inputs, fatigue context, and scheduling-linked decision support.",
    icon: Gauge,
    href: "/scheduling/readiness",
  },
  {
    title: "Scheduling & FRMS Controls",
    description:
      "Fatigue-aware duty planning, workload cards, Go/No-Go style indicators, and FRMS-oriented crew safety framing.",
    icon: Shield,
    href: "/scheduling",
  },
  {
    title: "Operational PVT (Pre-Flight Gate)",
    description:
      "Canonical PVT-B (3-minute, 355 ms lapse threshold per Basner & Dinges 2011) scoring wired to the same Python core as research — pre-flight vigilance gate feeding the scheduling pipeline.",
    icon: Timer,
    href: "/scheduling/pvt",
  },
  {
    title: "Operational Sleep Gate",
    description:
      "Four-band pre-flight sleep readiness (GO / GO_MONITOR / CAUTION / NO_GO) from last-night duration, 7-night debt, Sleep Regularity Index (Lunsford-Avery 2018), and SpO₂ screening proxy. Garmin-backed; never clinical apnea claims.",
    icon: Bed,
    href: "/scheduling/sleep",
  },
  {
    title: "Research Hub & HRV Stack",
    description:
      "Time, frequency, nonlinear, windowed, and HRF analyses; circadian and SAFTE-style fatigue; ventilatory threshold (DFA-α1); norms, export, and publication-grade charts.",
    icon: Microscope,
    href: "/research",
  },
  {
    title: "Research Sleep Dashboard",
    description:
      "Chart-heavy Garmin sleep analytics: duration trend, 7-night debt curve, stage balance, bedtime regularity strip, correlation matrix (FDR-q) and six scatter plots vs overnight HRV RMSSD. Bounded to Pending.md Tier A; Lee 2025 / Schyvens 2024 vs-PSG disclosure.",
    icon: Moon,
    href: "/research/sleep",
  },
  {
    title: "Research PVT (Longitudinal)",
    description:
      "Variant selector (PVT-B / PVT-5 / PVT-10) with session history table and decision badges. Browser timing ~5–10 ms per Anwyl-Irvine 2020; PsychoPy desktop driver for sub-ms research sessions.",
    icon: Timer,
    href: "/research/pvt",
  },
  {
    title: "Garmin Connect & Correlations",
    description:
      "Sync daily wellness metrics via FastAPI, align crew mission and user_id with SQLite, and explore trends plus solar–physiology correlation views.",
    icon: Watch,
    href: "/research/garmin",
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
  { name: "React 18", category: "UI" },
  { name: "SQLite", category: "Database" },
  { name: "Zustand", category: "State" },
];

const operationalWorkflow = [
  {
    title: "Ingest",
    description:
      "RR uploads and tracing, crew profiles, mission-scoped SQLite (per HRV_ACTIVE_MISSION), optional Garmin Connect sync, and NOAA/NASA environment feeds.",
    icon: Database,
  },
  {
    title: "Analyze",
    description:
      "HRV pipelines, PVT scoring, workload and vigilance models, fatigue and readiness endpoints — shared Python core behind FastAPI.",
    icon: LineChart,
  },
  {
    title: "Decide",
    description:
      "Scheduling with fatigue and readiness gates, operational PVT checks, and explainable metrics suitable for clinical and field review.",
    icon: Workflow,
  },
  {
    title: "Monitor",
    description:
      "Dashboards and research modules track trajectories over time; Streamlit remains available as a legacy local workbench alongside this UI.",
    icon: Radar,
  },
];

const integrations = [
  {
    name: "Physiological Data",
    detail:
      "Polar-style RR and HRV time series, research PVT variants (PVT-B / PVT-5 / PVT-10), Garmin daily metrics sync, and readiness or fatigue modifiers from the same analysis core.",
  },
  {
    name: "Environmental Signals",
    detail:
      "NOAA and NASA space-weather context (e.g., Kp, solar wind) for scheduling and research correlation workflows.",
  },
  {
    name: "Crew & Mission Context",
    detail:
      "Mission 1 / Mission 2 workspaces, crew profiles via REST, and SQLite under crew/<Mission>/db — keep FastAPI and Streamlit on the same active mission when comparing data.",
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
  {
    title: "PVT-B 3-minute validation (355 ms lapse threshold)",
    citation:
      "Basner, M., & Dinges, D. F. (2011). Maximizing sensitivity of the Psychomotor Vigilance Test (PVT) to sleep loss. Sleep, 34(5), 581-591.",
    pmid: "21532951",
  },
  {
    title: "Mobile PVT-B smartphone/tablet validation",
    citation:
      "Grant, D. A., Honn, K. A., Layton, M. E., Riedy, S. M., & Van Dongen, H. P. A. (2017). 3-minute smartphone-based and tablet-based psychomotor vigilance tests for the assessment of reduced alertness due to sleep deprivation. Behavior Research Methods, 49(3), 1020-1029.",
    pmid: "27325169",
  },
  {
    title: "Sleep Regularity Index (SRI)",
    citation:
      "Lunsford-Avery, J. R., Engelhard, M. M., Navar, A. M., & Kollins, S. H. (2018). Validation of the Sleep Regularity Index in Older Adults and Associations with Cardiometabolic Risk. Scientific Reports, 8, 14158.",
    pmid: "30242174",
  },
  {
    title: "Consumer wearable vs PSG (Garmin, Fitbit, WHOOP) meta-analysis",
    citation:
      "Lee, Y. J., Lee, J. Y., Cho, J. H., Kang, Y. J., & Choi, J. H. (2025). Performance of consumer wrist-worn sleep tracking devices compared to polysomnography: a meta-analysis. Journal of Clinical Sleep Medicine, 21(3), 573-582.",
    pmid: "39484805",
  },
  {
    title: "Browser-based reaction-time timing precision",
    citation:
      "Anwyl-Irvine, A., Dalmaijer, E. S., Hodges, N., & Evershed, J. K. (2020). Realistic precision and accuracy of online experiment platforms, web browsers, and devices. Behavior Research Methods, 53(4), 1407-1425.",
    pmid: "33140376",
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
      title="About Mission Control"
      description="Next.js + FastAPI flight surgeon console — operations, research, and wearables"
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
                      Primary web stack (2026): production Next.js frontend on FastAPI — crew
                      readiness, FRMS-oriented scheduling, operational PVT gates, a deep research
                      analytics hub (HRV through export), and Garmin Connect integration. Shares one
                      Python analysis core with the legacy Streamlit workbench.
                    </CardDescription>
                    <div className="flex flex-wrap gap-2">
                      <Badge>Operations</Badge>
                      <Badge variant="outline">Research</Badge>
                      <Badge variant="outline">Wearables</Badge>
                      <Badge variant="outline">FastAPI</Badge>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="icon" asChild>
                    <a
                      href="https://github.com/strikerdlm/HRV"
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Mission Control HRV repository on GitHub"
                      aria-label="Mission Control HRV repository on GitHub"
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
                Led by <strong>Dr Diego Malpica MD</strong> — a mission-oriented platform for
                translating physiology, fatigue, vigilance, and environment into actionable crew
                operations and reproducible research outputs.
              </p>
              <p className="text-sm text-muted-foreground">
                New capability ships here first: PVT scoring shared with scheduling gates, expanded
                research routes (workload, flight fatigue, ventilatory threshold, correlations,
                export), and Garmin sync aligned to mission-scoped databases. The UI favors rapid
                comprehension, bounded analysis pipelines, and citations where interpretation
                matters.
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
              <CardTitle>Product surface</CardTitle>
              <CardDescription>
                Primary entry points for operations and research (see also the sidebar and{" "}
                <Link
                  href="/research"
                  className="text-primary underline-offset-4 hover:underline"
                  title="Open research hub"
                >
                  Research hub
                </Link>
                )
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
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
            Mission readiness, scheduling, PVT gates, research analytics, and Garmin-backed
            physiology — one console
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            <Button size="sm" variant="outline" asChild>
              <Link href="/scheduling">
                <Calendar className="h-4 w-4 mr-1" />
                Scheduling
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/research">
                <Activity className="h-4 w-4 mr-1" />
                Research hub
              </Link>
            </Button>
            <Button size="sm" variant="outline" asChild>
              <Link href="/research/garmin">
                <Watch className="h-4 w-4 mr-1" />
                Garmin
              </Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
