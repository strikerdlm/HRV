// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Info,
  Github,
  Heart,
  Rocket,
  Shield,
  BookOpen,
  Mail,
  ExternalLink,
} from "lucide-react";
import { PageWrapper } from "@/components/layout";
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

const features = [
  {
    title: "HRV Analysis",
    description:
      "Comprehensive time-domain, frequency-domain, and nonlinear HRV metrics following Task Force standards.",
    icon: Heart,
  },
  {
    title: "Space Weather Integration",
    description:
      "Real-time NOAA/NASA space weather data with correlation analysis for physiological effects.",
    icon: Rocket,
  },
  {
    title: "Crew Scheduling",
    description:
      "SAFTE fatigue modeling, FRMS compliance, and intelligent crew scheduling with workload management.",
    icon: Shield,
  },
  {
    title: "Publication Ready",
    description:
      "Export publication-quality charts, LaTeX tables, and comprehensive reports with scientific citations.",
    icon: BookOpen,
  },
];

const technologies = [
  { name: "Next.js 14", category: "Frontend" },
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
];

export default function AboutPage() {
  return (
    <PageWrapper title="About" description="Mission Control - Flight Surgeon">
      <div className="space-y-6 max-w-4xl">
        {/* Author Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-primary/50 flex items-center justify-center">
                    <span className="text-2xl font-bold text-primary-foreground">
                      DM
                    </span>
                  </div>
                  <div>
                    <CardTitle className="text-xl">
                      Dr Diego Malpica MD
                    </CardTitle>
                    <CardDescription className="mt-1">
                      Aerospace Medicine Specialist
                    </CardDescription>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge>National University of Colombia</Badge>
                      <Badge variant="outline">Colombian Aerospace Force</Badge>
                    </div>
                  </div>
                </div>
                <Button variant="outline" size="icon" asChild>
                  <a
                    href="https://github.com/strikerdlm/HRV"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Github className="h-4 w-4" />
                  </a>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Contributing to the <strong>AsterPhysiology</strong> Research
                Initiative. This application is a comprehensive, research-grade
                Heart Rate Variability operations console designed for
                clinicians, researchers, and aerospace medicine specialists.
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Version Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="h-5 w-5" />
                Version Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Version
                  </p>
                  <p className="font-mono font-semibold">1.9.16</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Last Updated
                  </p>
                  <p className="font-mono font-semibold">2026-02-02</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Python
                  </p>
                  <p className="font-mono font-semibold">3.12</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Frontend
                  </p>
                  <p className="font-mono font-semibold">Next.js 16</p>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    License
                  </p>
                  <p className="font-mono font-semibold">MIT</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Backend
                  </p>
                  <p className="font-mono font-semibold">FastAPI</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    API Port
                  </p>
                  <p className="font-mono font-semibold">8180</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">
                    Frontend Port
                  </p>
                  <p className="font-mono font-semibold">3100</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Features */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Key Features</CardTitle>
              <CardDescription>
                Comprehensive physiological analysis capabilities
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid sm:grid-cols-2 gap-4">
                {features.map((feature, index) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + index * 0.1 }}
                    className="flex gap-3 p-3 rounded-lg bg-muted/50"
                  >
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <feature.icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm">{feature.title}</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        {feature.description}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Technologies */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Technology Stack</CardTitle>
              <CardDescription>
                Built with modern, production-ready technologies
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {technologies.map((tech) => (
                  <Badge key={tech.name} variant="outline" className="py-1">
                    {tech.name}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Scientific References */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Core References
              </CardTitle>
              <CardDescription>
                Evidence-based analysis following peer-reviewed standards
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {references.map((ref, index) => (
                <div key={index} className="space-y-1">
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
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-sm text-muted-foreground py-4"
        >
          <p>
            Mission Control - Flight Surgeon © {new Date().getFullYear()} Dr
            Diego Malpica MD
          </p>
          <p className="mt-1">
            TypeScript Frontend for comprehensive HRV analysis
          </p>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
