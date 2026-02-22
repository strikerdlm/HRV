// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Book,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Search,
  FileText,
  Heart,
  Waves,
  Network,
  Zap,
  Sun,
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
import { Input } from "@/components/ui/input";

interface Reference {
  id: string;
  authors: string;
  year: number;
  title: string;
  journal: string;
  doi?: string;
  pmid?: string;
  category: string;
}

const references: Reference[] = [
  {
    id: "taskforce1996",
    authors: "Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology",
    year: 1996,
    title: "Heart rate variability: Standards of measurement, physiological interpretation, and clinical use",
    journal: "Circulation, 93(5), 1043-1065",
    doi: "10.1161/01.CIR.93.5.1043",
    pmid: "8598068",
    category: "Standards",
  },
  {
    id: "shaffer2017",
    authors: "Shaffer F, Ginsberg JP",
    year: 2017,
    title: "An Overview of Heart Rate Variability Metrics and Norms",
    journal: "Front Public Health, 5, 258",
    doi: "10.3389/fpubh.2017.00258",
    pmid: "29034226",
    category: "Overview",
  },
  {
    id: "nunan2010",
    authors: "Nunan D, Sandercock GR, Brodie DA",
    year: 2010,
    title: "A quantitative systematic review of normal values for short-term heart rate variability in healthy adults",
    journal: "Pacing Clin Electrophysiol, 33(11), 1407-17",
    doi: "10.1111/j.1540-8159.2010.02841.x",
    pmid: "20663071",
    category: "Norms",
  },
  {
    id: "costa2017",
    authors: "Costa MD, Davis RB, Goldberger AL",
    year: 2017,
    title: "Heart Rate Fragmentation: A New Approach to the Analysis of Cardiac Interbeat Interval Dynamics",
    journal: "Front Physiol, 8, 255",
    doi: "10.3389/fphys.2017.00255",
    pmid: "28536533",
    category: "HRF",
  },
  {
    id: "peng1995",
    authors: "Peng CK, Havlin S, Stanley HE, Goldberger AL",
    year: 1995,
    title: "Quantification of scaling exponents and crossover phenomena in nonstationary heartbeat time series",
    journal: "Chaos, 5(1), 82-7",
    doi: "10.1063/1.166141",
    pmid: "11538314",
    category: "Nonlinear",
  },
  {
    id: "plews2013",
    authors: "Plews DJ, Laursen PB, Stanley J, Kilding AE, Buchheit M",
    year: 2013,
    title: "Training adaptation and heart rate variability in elite endurance athletes: opening the door to effective monitoring",
    journal: "Sports Med, 43(9), 773-81",
    doi: "10.1007/s40279-013-0071-8",
    pmid: "23852425",
    category: "Training",
  },
  {
    id: "alabdulgader2018",
    authors: "Alabdulgader A, McCraty R, Atkinson M, et al.",
    year: 2018,
    title: "Long-Term Study of Heart Rate Variability Responses to Changes in the Solar and Geomagnetic Environment",
    journal: "Sci Rep, 8(1), 2663",
    doi: "10.1038/s41598-018-20932-x",
    pmid: "29422621",
    category: "Space Weather",
  },
  {
    id: "hursh2004",
    authors: "Hursh SR, Redmond DP, Johnson ML, et al.",
    year: 2004,
    title: "Fatigue models for applied research in warfighting",
    journal: "Aviat Space Environ Med, 75(3 Suppl), A44-53",
    pmid: "15018265",
    category: "Fatigue",
  },
  {
    id: "billman2013",
    authors: "Billman GE",
    year: 2013,
    title: "The LF/HF ratio does not accurately measure cardiac sympatho-vagal balance",
    journal: "Front Physiol, 4, 26",
    doi: "10.3389/fphys.2013.00026",
    pmid: "23431279",
    category: "Frequency",
  },
  {
    id: "brennan2001",
    authors: "Brennan M, Palaniswami M, Kamen P",
    year: 2001,
    title: "Do existing measures of Poincaré plot geometry reflect nonlinear features of heart rate variability?",
    journal: "IEEE Trans Biomed Eng, 48(11), 1342-7",
    doi: "10.1109/10.959330",
    pmid: "11686633",
    category: "Nonlinear",
  },
];

const methodologySections = [
  {
    id: "time-domain",
    title: "Time Domain Analysis",
    icon: Heart,
    content: `Time-domain measures quantify the variability in RR intervals using statistical methods.

**Primary Metrics:**
- **SDNN**: Standard deviation of all NN intervals. Reflects overall HRV powered by all cyclic components.
- **RMSSD**: Root mean square of successive differences. Reflects parasympathetic (vagal) activity.
- **pNN50**: Percentage of successive intervals differing by >50ms. Correlates with RMSSD.

**Requirements:**
- Minimum 5 minutes for short-term recordings
- 24 hours for comprehensive SDNN assessment (includes circadian components)

**Clinical Significance:**
- SDNN <50ms (24h): Increased cardiovascular risk
- RMSSD decline: Reduced vagal tone, stress, or overtraining`,
  },
  {
    id: "frequency-domain",
    title: "Frequency Domain Analysis",
    icon: Waves,
    content: `Power spectral density (PSD) analysis decomposes HRV into frequency components.

**Frequency Bands:**
- **VLF (0.003-0.04 Hz)**: Very low frequency. Associated with thermoregulation, hormonal rhythms.
- **LF (0.04-0.15 Hz)**: Low frequency. Mixed sympathetic and parasympathetic, includes baroreflex.
- **HF (0.15-0.4 Hz)**: High frequency. Primarily parasympathetic, respiratory sinus arrhythmia.

**Methods:**
- Welch's method (recommended): Averaged periodograms with overlapping segments
- AR modeling: Autoregressive spectral estimation
- Periodogram: Simple FFT-based method

**Interpretation Caveats:**
- LF/HF ratio does NOT accurately reflect "sympathovagal balance" (Billman 2013)
- HF is reliably parasympathetic; LF interpretation is complex`,
  },
  {
    id: "nonlinear",
    title: "Nonlinear Analysis",
    icon: Network,
    content: `Nonlinear methods capture complexity and fractal properties of heart rate dynamics.

**Poincaré Plot:**
- **SD1**: Short-term variability (perpendicular to identity line)
- **SD2**: Long-term variability (along identity line)
- SD1/SD2 ratio: Indicates balance between short and long-term dynamics

**Detrended Fluctuation Analysis (DFA):**
- **α1 (4-11 beats)**: Short-term scaling exponent
  - α1 ≈ 1.0: Healthy fractal correlation
  - α1 < 0.65: Loss of correlation, cardiac pathology
  - α1 > 1.35: Loss of complexity, rigid rhythm
- **α2 (>11 beats)**: Long-term scaling exponent

**Entropy:**
- **Sample Entropy (SampEn)**: Lower = more regular/predictable
- Reduced entropy associated with aging and disease`,
  },
  {
    id: "hrf",
    title: "Heart Rate Fragmentation",
    icon: Zap,
    content: `HRF captures non-autonomic irregularity not explained by traditional HRV.

**Key Metrics:**
- **PIP**: Percentage of Inflection Points (direction changes)
- **IALS**: Inverse Average Length of Segments
- **PSS**: Percentage of Short Segments (<3 consecutive monotonic beats)
- **PAS**: Percentage of Alternating Segments

**Clinical Relevance:**
- PIP >60% associated with increased AF risk (PROOF-AF Study)
- HRF independent of SDNN, RMSSD, and traditional HRV
- May reflect subclinical atrial substrate abnormalities

**Reference:**
Costa MD et al. (2017, 2021) - Heart Rate Fragmentation series`,
  },
  {
    id: "space-weather",
    title: "Space Weather & HRV",
    icon: Sun,
    content: `Emerging research links solar/geomagnetic activity to cardiovascular physiology.

**Key Indices:**
- **Kp Index**: Planetary geomagnetic activity (0-9 scale)
- **Dst Index**: Ring current strength (nT), negative during storms
- **Solar Wind**: Speed, density, and IMF Bz component
- **F10.7 Flux**: Solar radio flux, proxy for overall solar activity

**Reported Correlations:**
- Elevated Kp associated with reduced HRV (Alabdulgader 2018)
- Geomagnetic storms linked to cardiovascular events (Stoupel studies)
- Effects appear 12-36 hours post-event

**Limitations:**
- Effect sizes modest (r ≈ 0.2-0.4)
- Individual sensitivity varies significantly
- Confounding by weather, stress, other factors`,
  },
];

function ReferenceCard({ reference }: { reference: Reference }) {
  return (
    <div className="p-4 rounded-lg border bg-card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <p className="font-medium text-sm">{reference.title}</p>
          <p className="text-xs text-muted-foreground mt-1">{reference.authors} ({reference.year})</p>
          <p className="text-xs text-muted-foreground italic">{reference.journal}</p>
        </div>
        <Badge variant="outline" className="shrink-0">{reference.category}</Badge>
      </div>
      <div className="flex items-center gap-3 mt-3">
        {reference.doi && (
          <a
            href={`https://doi.org/${reference.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <ExternalLink className="h-3 w-3" />
            DOI
          </a>
        )}
        {reference.pmid && (
          <a
            href={`https://pubmed.ncbi.nlm.nih.gov/${reference.pmid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <ExternalLink className="h-3 w-3" />
            PubMed
          </a>
        )}
      </div>
    </div>
  );
}

function MethodologyAccordion({ section }: { section: typeof methodologySections[0] }) {
  const [open, setOpen] = React.useState(false);
  const Icon = section.icon;

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full p-4 flex items-center justify-between hover:bg-muted/50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-3">
          <Icon className="h-5 w-5 text-primary" />
          <span className="font-medium">{section.title}</span>
        </div>
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open && (
        <div className="p-4 pt-0 border-t">
          <div className="text-sm text-muted-foreground whitespace-pre-line">
            {section.content}
          </div>
        </div>
      )}
    </div>
  );
}

export default function SciencePage() {
  const [searchQuery, setSearchQuery] = React.useState("");

  const filteredRefs = references.filter(
    (item) =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.authors.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <PageWrapper
      title="Science & References"
      description="Methodology Documentation and Citation Library"
    >
      <div className="space-y-6">
        {/* Methodology */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                Methodology Documentation
              </CardTitle>
              <CardDescription>
                Scientific background for HRV analysis methods
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {methodologySections.map((section) => (
                <MethodologyAccordion key={section.id} section={section} />
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Reference Library */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Book className="h-5 w-5 text-info" />
                Reference Library
              </CardTitle>
              <CardDescription>
                Key scientific publications underlying this application
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-4">
                <Search className="h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search references..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="max-w-sm"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {filteredRefs.map((item) => (
                  <ReferenceCard key={item.id} reference={item} />
                ))}
              </div>
              {filteredRefs.length === 0 && (
                <p className="text-center text-muted-foreground py-8">
                  No references found matching &quot;{searchQuery}&quot;
                </p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Citation Guide */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>How to Cite</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-4">
              <p>
                When using this application for research, please cite the relevant primary sources
                for the specific analyses performed. Key citations:
              </p>
              <div className="p-3 rounded-lg bg-muted/50 font-mono text-xs">
                <p><strong>Time/Frequency Domain:</strong></p>
                <p>Task Force (1996). Circulation, 93(5), 1043-1065.</p>
                <p className="mt-2"><strong>HRV Norms:</strong></p>
                <p>Nunan et al. (2010). Pacing Clin Electrophysiol, 33(11), 1407-17.</p>
                <p className="mt-2"><strong>HRF Metrics:</strong></p>
                <p>Costa et al. (2017). Front Physiol, 8, 255.</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </PageWrapper>
  );
}
