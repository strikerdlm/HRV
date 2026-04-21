# Cover Letter — Applied Ergonomics submission

*Draft. Finalise author metadata and institutional address before submission. Placeholder institutional details are marked `[PLACEHOLDER]`.*

---

Dr Diego Malpica MD
Aerospace Medicine Specialist
Bogotá, Colombia
dlmalpica@yahoo.com

Date: [submission date]

---

To the Editorial Office,
*Applied Ergonomics*
Elsevier Ltd.

Dear Editor-in-Chief,

I am pleased to submit for your consideration the manuscript **"Task-calibrated Operational Performance Indicators for aviation and unmanned aircraft system operators: a biomathematical framework integrating SAFTE fatigue, heart-rate variability, and cognitive-load theory, with open-source reference implementation"** as a Research Article for *Applied Ergonomics*.

### What the paper does

The manuscript introduces the **Operational Performance Indicator (OPI) framework** — a task-calibrated composite readiness index that integrates SAFTE-style fatigue effectiveness, heart-rate-variability-derived autonomic markers, task-specific cognitive-load modifiers grounded in Multiple Resource Theory, and environmental/operational modifiers into a single per-task interpretable score. The framework specifies per-task weight profiles and thresholds for **ten manned-aviation task categories** (instrument flight, night-vision operations, helmet-mounted-display flying, high-density air-traffic control, critical and non-critical emergencies, test-pilot operations, carrier landing, weapons delivery, and new-platform testing) and **seven UAS/teleoperator categories** (ISR, strike, SAR/CSAR, autonomous-swarm supervisory control, contested-environment operations, ground-robot teleoperation, and subsea/long-latency teleoperation). A Warm-type vigilance-decrement function and a Chen-type logarithmic control-latency penalty are included for the UAS subset.

The reference implementation is open-source under the MIT license at `https://github.com/strikerdlm/HRV` and is delivered through a Next.js client over a FastAPI orchestration layer and a shared Python biomathematical backend. Engineering verification is documented across the fusion pathway. A single 128-minute HRV recording is used as an illustrative framework-instantiation worked example across three task hypotheses.

### Why *Applied Ergonomics*

*Applied Ergonomics* is the natural venue for this contribution for three reasons. First, the paper's central contribution is **methodological** — a theoretically grounded framework for operator-state integration, not a single-study empirical finding — and *Applied Ergonomics* explicitly welcomes methodology papers bearing on the design, planning, and management of technical and social systems in aviation and military contexts. Second, recent precedent (Berthon et al., *Applied Ergonomics* 129, 2025, 104599) confirms that multi-dimensional physiological workload studies in aviation contexts are in scope and that HRV-inclusive composite assessments of aerospace operators fit the journal's readership. Third, the paper addresses a research gap explicitly identified in two recent systematic reviews — Li, Molloy, El-Fiqi, & Eves (*Drones* 2025) for UAS operator cognitive-load assessment, and Rabat et al. (*BMJ Military Health* 2025) for warfighter mental endurance management — both of which called for integrated, inspectable frameworks that combine physiological monitoring with biomathematical fatigue estimation and task-specific calibration.

### Contribution summary

The paper contributes four specific elements:

1. An explicit four-component weighted composite readiness index with per-task weight profiles derived from Multiple Resource Theory and related HF constructs.
2. A task taxonomy covering seventeen operator categories across manned aviation and UAS operations, with expected autonomic signatures and dominant failure modes.
3. Integration of a Warm-type vigilance-decrement model and a Chen-type control-latency penalty into a composite operator-readiness index — these components have no analogue in manned aviation and are absent from prior composite readiness frameworks.
4. An open-source reference implementation with MIT licensing, documented execution environment, and engineering verification across the fusion pathway.

The manuscript explicitly does **not** claim validated operator outcomes, diagnostic accuracy, numerical parity with external HRV packages, or regulatory clearance. Per-task weights are theory-derived pending field calibration. The illustrative worked example uses a single HRV recording and is framed as a framework-instantiation demonstration, not as inferential data. Limitations and a concrete validation roadmap (weight calibration, external HRV benchmarking, comparative benchmarking, prospective pilot study) are explicit in Section 4.

### Suggested reviewers

(Optional; list to be finalised after internal review. Candidates familiar with the adjacent literature include researchers who have worked on composite pilot workload (Feng C., et al.; Military Psychology and NATO AFRL lineages including Stevens C. A., Morris M. B.), UAS operator cognitive-load assessment (Molloy O., Eves G.), cockpit physiological monitoring (Dehais F., ISAE-SUPAERO), and SAFTE/fatigue-management methodology (Hursh S. R., Devine J. K.). A formal list with ORCIDs and affiliations will be prepared.)

### Not under consideration elsewhere

This work is original and is not under consideration by any other journal. No portion has been previously published. All authors have approved the submission.

### Data and code availability

Code, tables, and all manuscript support files are publicly accessible at `https://github.com/strikerdlm/HRV`. A tagged release or archived DOI corresponding to the exact reported version will be issued and cited in the final manuscript.

### Conflicts of interest

(To be completed before submission.)

Thank you for considering this manuscript for *Applied Ergonomics*. I am available for any questions or clarifications at the contact address above.

Sincerely,

**Dr Diego Malpica MD**
Aerospace Medicine Specialist
[PLACEHOLDER — institutional affiliation]
[PLACEHOLDER — ORCID]
Bogotá, Colombia
dlmalpica@yahoo.com
