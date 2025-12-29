Develop a crew scheduling and human performance management tool with the best practices in the industry following the project rules in python using streamlit. You must do this in multiple steps and not rush to finish. It is better to have a well written app with all the scientific standards and rigor than an app full of errors. Some of the features are available on the app, they  have been written already. The plots must follow the rules as well as the scietific accuracy at all times. You can use mcp tools paper-search and brave to find whatever information you need. 

### 1. System Architecture (Streamlit-based)

#### 1.1 Core Components
- **Scheduling Engine**: Constraint-based optimization system for 6 aircrews
- **Risk Assessment Matrix**: Multi-dimensional risk calculation following standardized framework
- **Performance Prediction Module**: Integrates SAFTE-FAST biomathematical model
- **Real-time Monitoring Dashboard**: Live crew status and performance indicators
- **Automated Conflict Resolution**: Dynamic rescheduling based on risk factors

### 2. Fixed Activity Schedule (Daily Requirements)

| Activity | Duration | Constraints | MET Value* |
|----------|----------|-------------|------------|
| Briefing | 60 min (07:00) | All crew synchronous | 1.3-1.8 |
| Breakfast | 45 min | Flexible timing | 1.5 |
| Lunch | 45 min | Flexible timing | 1.5 |
| Dinner | 45 min | Flexible timing | 1.5 |
| Exercise/Physical Activity | 60 min | **Resource limited** (capacity restriction) | 6-8 |
| Recreation/Fun | 60 min | Individual scheduling | 1-6 (activity-dependent) |
| Hygiene/Prep | 30 min | Pre-duty mandatory | 2.0-2.8 |
| Sleep | 8 hours | Optimized by chronotype | 1.0 |

*MET = Metabolic Equivalent of Task (1 MET = 3.5 ml O₂/kg/min = ~1 kcal/kg/hr)

**Energy Computation Note**: All metabolic cost internally stored in **kcal** (nutrition/energy availability) and **Watts** (thermal/ECLSS). Conversion: 1 kcal = 4184 J; Power (W) = (kcal/hr × 4184) / 3600.

### 3. Variable Activity Workload Parameters

#### 3.1 Laboratory Work
- **MET Value**: 1.5-2.5 (light-moderate physical activity)
- **Cognitive Load**: Moderate-High
- **Duration**: Variable (30-240 min blocks)
- **Metabolic Cost**: Computed as kcal/hr = MET × body_mass_kg
- **Recovery Time**: 15 min per hour of activity

#### 3.2 Extravehicular Activity (EVA)
**Aerobic Capacity Requirement**: VO₂max ≥ 32.9 ml/kg/min (NASA Human Performance standard for microgravity EVA)
- **MET Value**: 2-7 (task-dependent; measured NASA EVA average ~194-238 kcal/hr for 70-80 kg crewmember)
- **Metabolic Cost**: 
  - Typical range: 100-500 kcal/hr (task/pacing dependent)
  - Skylab EVA historical mean: ~238 kcal/hr
  - Shuttle EVA average: ~194 kcal/hr
  - **Nutritional planning**: +200 kcal per EVA-hour above nominal intake
- **Duration**: Typically 5-7+ hours (ISS operational range)
- **Dehydration Risk**: Avoid >2% body mass loss (operational threshold)
  - **Hydration monitoring**: USG < 1.020 (euhydrated), 1.020-1.029 (caution), ≥1.030 (significant hypohydration)
- **Recovery Time**: 48 hours minimum between EVAs (24 hours absolute minimum with Flight Surgeon approval)
- **Pre-EVA Requirements**: Medical clearance + prebreathe protocol

#### 3.3 Physical Exercise (Static Cycle)
- **MET Value**: 6-8 depending on intensity (≈90-150 W workload)
- **Duration**: 60 min
- **VO₂ Requirement**: Calculated per individual fitness level
- **Uses Existing Tool**: Training readiness calculator integration

### 4. SAFTE-FAST Integration for Performance Prediction

SAFTE (Sleep Activity Fatigue Task Effectiveness) is a validated biomathematical model that estimates sleep patterns and performance levels through three processes: circadian function, homeostatic sleep reservoir, and sleep inertia.

#### 4.1 Model Inputs
- **Sleep History**: Duration, quality, timing (actigraphy-derived or predicted)
- **Work Schedule**: Duty periods, activity types, breaks
- **Circadian Phase**: Individual chronotype, geographic location
- **Time Awake**: Continuous wake duration tracking

#### 4.2 Model Outputs
- **Effectiveness Score**: 0-100% cognitive effectiveness prediction
- **Sleep Debt**: Cumulative deficit from optimal sleep
- **Lapse Likelihood**: Probability of attention lapses
- **Recommended Activity Windows**: Optimal timing for high-demand tasks

#### 4.3 Risk-Based Interpretation (Evidence-Grounded)
Based on U.S. Senate testimony validation evidence:
- **≥90**: Low-risk zone (optimal performance)
- **80-89**: Caution zone (elevated accident risk)
- **70-79**: High-risk zone (significant performance degradation)
- **<70**: Critical risk (roughly equivalent to 0.08 BAC or ~21 hours awake after 8-hour sleep)

**Operational Philosophy Options**:
- **Conservative (Aviation-style)**: Require ≥90 for EVA
- **Balanced Ops**: Require ≥80 with <70 absolute NO-GO
- **Research/Analog**: Allow 75-79 with strict mitigations

**Default Implementation**: Balanced Ops (≥80 required, <70 hard NO-GO)

### 5. Multi-Dimensional Risk Matrix Framework

#### 5.1 Risk Components (All use standardized classification)

**Likelihood Categories**: Low | Moderate | High | Very High
**Severity Categories**: Negligible | Minor | Major | Severe

#### 5.2 Risk Factors Assessment

##### A. Physiological Readiness
1. **Sleep Quality/Quantity**
   - SAFTE-FAST effectiveness score (see 4.3 interpretation)
   - Sleep debt accumulation
   - Circadian alignment (phase offset vs chronotype)

2. **HRV (Heart Rate Variability) - lnRMSSD Method**
   - **Measurement**: Daily lnRMSSD (natural log of root mean square of successive differences)
   - **Baseline**: Rolling 14-28 day window
   - **Z-score calculation**: (daily_lnRMSSD - baseline_mean) / baseline_SD
   - **Interpretation**:
     - z ≥ -0.5: Normal (Green)
     - z = -0.5 to -1.5: Caution (Yellow)
     - z < -1.5: High risk (Red - context-dependent)
   - **Measurement conditions**: Standardized (e.g., morning, seated, 5-min)

3. **Energy Availability (EA)**
   - **Formula**: EA = (Energy_Intake - Exercise_Energy_Expenditure) / Fat_Free_Mass
   - **Units**: kcal/kg FFM/day
   - **IOC-based thresholds**:
     - ≥45: Optimal
     - 30-44: Suboptimal
     - <30: Low EA (RED - system perturbations expected)

4. **Hydration Status**
   - **Body mass change**: Monitor for >2% loss (operational threshold)
   - **Urine Specific Gravity (USG)**:
     - <1.020: Euhydrated (Green)
     - 1.020-1.029: Hypohydrated (Yellow)
     - ≥1.030: Significantly hypohydrated (Red)

##### B. Operational Performance Indicators
1. **Psychomotor Vigilance Task (PVT) - 3-Minute Protocol**
   - **Lapse threshold**: >355 ms reaction time
   - **Operational anchors** (3-min PVT):
     - ≤10 lapses: High-performance band (Green)
     - 11-19 lapses: Medium-performance band (Yellow)
     - ≥20 lapses: Low-performance band (Red)
   - **Personalization**: Calibrate to individual baseline distribution

2. **Reaction Time Trends**
3. **Activity-Specific Performance History**

##### C. Behavioral/Psychological Metrics
- **PANAS** (Positive and Negative Affect Schedule)
- **VAS** (Visual Analog Scale - fatigue/alertness)
- **SP** (Samn-Perelli Fatigue Scale)
- **KSS** (Karolinska Sleepiness Scale) - **Acute gate metric**
  - Normal: 1-5 (Green)
  - Caution: 6-7 (Yellow)
  - NO-GO: 8-9 (Red)
- **ESS** (Epworth Sleepiness Scale) - **Baseline screening only (NOT acute gate)**
  - Use for: Longitudinal trait-like screening (weeks/months)
  - Normal: 0-10
  - Borderline: 11-14
  - Elevated: 15-24
  - **Not used for daily GO/NO-GO decisions** (use SAFTE + KSS + PVT + time-awake instead)

##### D. Mission-Specific Factors
- **VO₂ Capacity vs. Task Demand**
  - NASA EVA requirement: VO₂max ≥ 32.9 ml/kg/min
- **Recent Activity Load** (last 7 days)
- **Time Since Last High-Intensity Activity** (EVA: ≥48h optimal, ≥24h minimum)
- **Environmental Conditions**

### 6. Decision Algorithms

#### 6.1 EVA GO/NO-GO Decision Matrix

```
GO Criteria (ALL must be met):
├── Flight Surgeon Clearance: APPROVED
├── SAFTE Effectiveness: ≥80% (balanced ops policy)
├── HRV Status: z-score ≥ -1.5 (context-dependent threshold)
├── KSS Score: ≤5
├── Time Awake: <21 hours
├── Sleep: ≥6 hours in last 24h (conservative: ≥7h)
├── Hydration: 
│   ├── Body mass loss ≤2%
│   └── USG <1.030 (if available)
├── Energy Availability: ≥30 kcal/kg FFM/day
├── PVT (3-min): <20 lapses
├── VO₂max: ≥32.9 ml/kg/min
├── Time Since Last EVA: ≥48 hours (or ≥24h with FS approval)
└── Behavioral Metrics: ALL in normal/caution range

NO-GO Triggers (ANY disqualifies):
├── Flight Surgeon: HOLD or NO-GO
├── SAFTE Effectiveness: <70% (critical risk floor)
├── KSS Score: ≥8
├── Time Awake: ≥21 hours
├── Sleep: <6 hours in last 24h
├── Dehydration: 
│   ├── >2% body mass loss OR
│   └── USG ≥1.030
├── PVT (3-min): ≥20 lapses
├── Energy Availability: <30 kcal/kg FFM/day
└── VO₂max: <32.9 ml/kg/min

GO-WITH-MITIGATION Zone (75 ≤ SAFTE < 80):
├── All hard gates passed
├── IHPI 75-84
└── Required: Add naps/breaks/task simplification
```

#### 6.2 Exercise/Physical Activity Clearance
- Uses **Training Readiness Tool** (existing)
- Factors: Recovery status, injury risk, recent load
- Capacity Constraint: Max 2 crew members simultaneously

### 7. Scheduling Optimization Algorithm

#### 7.1 Constraint Hierarchy
1. **Hard Constraints** (Cannot be violated)
   - Briefing: 07:00 for all crew
   - Sleep: 8-hour blocks
   - Exercise capacity: ≤2 concurrent
   - Medical clearances
   - Recovery periods post-EVA (≥48h between EVAs)
   - All GO/NO-GO safety gates

2. **Soft Constraints** (Optimized)
   - Meal timing preferences
   - Chronotype-optimized work windows
   - Activity sequencing efficiency
   - Crew preferences

#### 7.2 Dynamic Rescheduling Triggers
- Real-time performance degradation detected
- Medical status change
- Mission priority shifts
- Fatigue score threshold breach (SAFTE <90 sustained)
- Resource availability changes

#### 7.3 Optimization Objectives (Science-First Formulation)

**Primary objective**: Maximize mission value while keeping predicted fatigue risk low

```python
# For candidate schedule S:
maximize:
  mission_value(S) 
  - λ × expected_fatigue_risk(S)  # time-below-90 and time-below-70 penalties
  - μ × circadian_misalignment(S)

subject to:
  - All hard constraints (safety gates, recovery, resources)
  - Medical clearance gates
  - GO/NO-GO decision criteria
```

**Weights (mission-dependent)**:
- Safety-critical missions: λ high (fatigue risk dominant)
- Research operations: λ moderate, mission value balanced

### 8. Integrated Human Performance Indicator (IHPI)

#### 8.1 Composite Score Components (Science-Revised)

```
IHPI = weighted_sum(
  SAFTE_effectiveness: 30%,
  PVT_performance: 20%,
  Circadian_alignment: 10%,
  HRV_lnRMSSD_z: 10%,
  Hydration_status: 10%,
  Energy_availability: 10%,
  Subjective_sleepiness: 5%,  # KSS + Samn-Perelli
  Task_specific_readiness: 5%  # VO₂ margin + recovery + load
)

with hard-cap gating logic:
  if any(SAFTE, Hydration, PVT, Subjective) == 0:
    IHPI_final = 0
```

**Component scoring functions** (0-1 scale):
- **SAFTE**: Linear ramp 70→90 (0→1)
- **PVT**: ≤10 lapses=1.0, ≥20 lapses=0, linear between
- **HRV**: z≥-0.5=1.0, z≤-2.0=0, linear between
- **Hydration**: Combined BM% + USG (conservative=min)
- **Energy Availability**: ≥45=1.0, ≤30=0, linear between
- **KSS**: ≤5=1.0, ≥8=0, linear 5→8
- **Circadian**: Phase offset ≤1h=1.0, ≥6h=0
- **Task-specific**: min(VO₂_OK, recovery_time_adequacy)

#### 8.2 Activity Suitability Matrix

| Activity Domain | Minimum IHPI | Critical Factors |
|-----------------|--------------|------------------|
| Space EVA | 85 (GO), 75 (GO-with-mitigation) | HRV, SAFTE, EA, Hydration, VO₂max |
| Aviation (PIC) | 80 | SAFTE, PVT, Circadian alignment |
| Extreme Sports | 75 | HRV, EA, Recent load |
| Mountaineering | 70 | VO₂, EA, Acclimatization |
| Technical Diving | 80 | SAFTE, Behavioral, PVT |

### 9. Streamlit UI Components

#### 9.1 Main Dashboard
- **Live Status Grid**: 6-crew status cards with color-coded IHPI
- **Timeline View**: 24-hour Gantt chart with activity assignments
- **Risk Heatmap**: Real-time risk levels per crew member
- **Alert Panel**: Active warnings and recommendations

#### 9.2 Scheduling Tab
- **Drag-and-drop Activity Assignment**
- **Automated Conflict Detection**
- **Constraint Violation Indicators**
- **"Optimize Schedule" Button**: Runs algorithm
- **Scenario Comparison**: Side-by-side schedule options

#### 9.3 Individual Crew Profile
- **Clinical Profile Summary**
  - Chronotype
  - Baseline VO₂max (NASA requirement: ≥32.9 ml/kg/min for EVA)
  - Fat-Free Mass (FFM) for EA calculation
  - Energy requirements (BMR + activity)
  - Hydration needs
  - HRV baseline (lnRMSSD mean ± SD, rolling 14-28 days)
  - Historical performance trends
- **Current Status Dashboard**
  - Sleep history (7-day)
  - SAFTE effectiveness curve (with risk zones marked)
  - HRV trend (lnRMSSD z-score)
  - Behavioral metrics (latest scores: KSS acute, ESS baseline)
  - Energy Availability (EA) trend
  - Hydration status (BM% + USG)
  - Activity log

#### 9.4 Risk Analysis Tab
- **Risk Matrix Visualization** (Likelihood × Severity)
- **Drill-down by Risk Factor**
- **Historical Risk Trends**
- **Mitigation Recommendations**

#### 9.5 Performance Prediction Tab
- **SAFTE-FAST Outputs**:
  - 24-hour effectiveness forecast per crew (with 90/80/70 thresholds marked)
  - Optimal work windows highlighted
  - Sleep opportunity windows
- **Activity Simulation**: "What-if" analysis for schedule changes
- **Fatigue risk projection**: Time-below-90 and time-below-70 estimates

### 10. Scientific References & Validation

#### 10.1 Key Literature Support
- EVA metabolic modeling: Skylab EVA mean ~238 kcal/hr, Shuttle EVA average ~194 kcal/hr (NASA NTRS reports)
- SAFTE-FAST validation: Risk elevated below 90 effectiveness; <70 roughly equivalent to 0.08 BAC or ~21h awake (U.S. Senate testimony)
- Circadian rhythm disruption in shift work
- MET values from Compendium of Physical Activities (2024 Adult Compendium)
- HRV (lnRMSSD) as performance indicator: Daily monitoring with z-score approach
- Energy Availability (IOC consensus): ~45 kcal/kg FFM/day optimal, <30 threshold for system perturbations
- Hydration: >2% body mass loss threshold (ACSM position stand); USG operational bins
- PVT operational anchors: 11 and 20 lapses (355ms) for performance stratification
- NASA Human Performance Capabilities standard: VO₂max ≥32.9 ml/kg/min for microgravity EVA
- NASA exploration nutrition: +200 kcal per EVA-hour above nominal

#### 10.2 Model Calibration Requirements
- Individual baseline establishment (2-week minimum for HRV; 14-28 day rolling window)
- Population norms for comparison
- Activity-specific validation trials
- Regular recalibration (monthly recommended)

#### 10.3 MET Source Tracking
All activities stored with:
- `met` (dimensionless value)
- `met_source` (e.g., "2024 Adult Compendium", "NASA measured EVA metabolic rate", "assumption")
Enables audit trail for evidence-grounding.

### 11. Implementation Priorities

#### Phase 1: Core Functionality
- [ ] Fixed schedule template with constraints
- [ ] Basic SAFTE-FAST integration (API or library)
- [ ] Manual activity assignment UI
- [ ] Simple risk scoring with evidence-based thresholds

#### Phase 2: Intelligence Layer
- [ ] Automated scheduling optimization (safety-dominant objective)
- [ ] Real-time performance monitoring (HRV z-score, PVT, hydration)
- [ ] Dynamic rescheduling engine
- [ ] Integrated risk matrix with gating logic

#### Phase 3: Advanced Features
- [ ] IHPI composite indicator with hard-cap gating
- [ ] Energy Availability (EA) calculation and tracking
- [ ] Multi-domain activity suitability
- [ ] Machine learning for personalization
- [ ] Predictive analytics dashboard

### 12. Data Requirements & APIs

#### 12.1 Real-time Inputs
- Actigraphy devices (sleep tracking)
- HR/HRV monitors (lnRMSSD capable)
- Behavioral questionnaire responses (KSS acute, ESS baseline)
- Activity logs (manual or automated)
- Environmental sensors
- Body mass (daily weigh-ins for hydration)
- Urine specific gravity (USG) measurements
- Dietary intake logs (for EA calculation)

#### 12.2 External Integrations
- SAFTE-FAST API (if available, else implement model)
- Training Readiness Tool (existing)
- Profile Tools Engine
- Medical clearance system

### 13. Compliance & Safety

- All risk matrices follow standardized framework
- Flight Surgeon has override authority on all GO/NO-GO decisions
- Automated alerts for threshold breaches (SAFTE <80, KSS ≥6, HRV z <-1.5, etc.)
- Audit trail for all scheduling decisions
- Privacy protection for individual health data
- ESS used only for baseline screening, not acute operational gates

---

## Appendix A: Python Science Layer (Drop-In Equations)

```python
from dataclasses import dataclass
import math

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# ----------------------------
# MET / energy conversions
# ----------------------------
def kcal_per_hour_from_met(met: float, mass_kg: float) -> float:
    """1 MET ≈ 1 kcal/kg/hour"""
    return met * mass_kg

def watts_from_kcal_per_hour(kcal_h: float) -> float:
    """Convert kcal/hr to Watts. 1 kcal = 4184 J; 1 hour = 3600 s"""
    return kcal_h * 4184.0 / 3600.0

def kcal_from_met_duration(met: float, mass_kg: float, minutes: float) -> float:
    return kcal_per_hour_from_met(met, mass_kg) * (minutes / 60.0)

# ----------------------------
# Subscore mappers (0..1)
# ----------------------------
def score_safte(effectiveness_0_100: float) -> float:
    """
    Anchors:
    - >=90: low risk zone (accident risk elevated below 90 in SAFTE validation)
    - <=70: high risk zone (roughly 0.08 BAC / ~21h awake equivalence)
    """
    e = effectiveness_0_100
    if e >= 90: return 1.0
    if e <= 70: return 0.0
    return (e - 70) / 20.0

def score_kss(kss_1_9: float) -> float:
    """1-5 good; 6 caution; 7 poor; 8-9 no-go"""
    k = kss_1_9
    if k <= 5: return 1.0
    if k >= 8: return 0.0
    return 1.0 - (k - 5) / 3.0

def score_pvt_lapses_3min(lapses: int) -> float:
    """
    Operational anchors (3-min PVT, 355ms lapse threshold):
    ~<=10: high-performance
    ~>=20: low-performance
    """
    if lapses <= 10: return 1.0
    if lapses >= 20: return 0.0
    return 1.0 - (lapses - 10) / 10.0

def score_hrv_z(z_lnrmssd: float) -> float:
    """Conservative readiness mapping for lnRMSSD z-score"""
    if z_lnrmssd >= -0.5: return 1.0
    if z_lnrmssd <= -2.0: return 0.0
    return 1.0 - (abs(z_lnrmssd) - 0.5) / 1.5

def score_hydration(body_mass_change_pct: float, usg: float | None) -> float:
    """
    body_mass_change_pct: negative means loss (e.g., -1.5 for 1.5% loss)
    usg: urine specific gravity
    """
    loss = -body_mass_change_pct
    # body mass: 0% loss best, >2% problematic
    if loss <= 0.5: bm = 1.0
    elif loss >= 2.0: bm = 0.0
    else: bm = 1.0 - (loss - 0.5) / 1.5

    if usg is None:
        return bm

    # <1.020 euhydrated; >=1.030 significant hypohydration
    if usg < 1.020: u = 1.0
    elif usg >= 1.030: u = 0.0
    else: u = 1.0 - (usg - 1.020) / 0.010

    return min(bm, u)  # conservative

def score_energy_availability(EA_kcal_per_kgFFM_day: float) -> float:
    """
    IOC-style anchors:
    - ~45: optimal
    - <30: commonly used "low EA" threshold
    """
    ea = EA_kcal_per_kgFFM_day
    if ea >= 45: return 1.0
    if ea <= 30: return 0.0
    return (ea - 30) / 15.0

def score_circadian_alignment(phase_offset_hours: float) -> float:
    """Absolute difference between scheduled and chronotype sleep midpoint"""
    d = abs(phase_offset_hours)
    if d <= 1.0: return 1.0
    if d >= 6.0: return 0.0
    return 1.0 - (d - 1.0) / 5.0

def score_task_specific(vo2max_ml_min_kg: float, hours_since_last_eva: float) -> float:
    """
    NASA EVA requirement: VO2max >= 32.9 ml/min/kg
    Recovery: <24h bad, >=48h good
    """
    vo2_ok = 1.0 if vo2max_ml_min_kg >= 32.9 else 0.0

    if hours_since_last_eva >= 48: rec = 1.0
    elif hours_since_last_eva <= 24: rec = 0.0
    else: rec = (hours_since_last_eva - 24) / 24.0

    return min(vo2_ok, rec)

# ----------------------------
# IHPI composite (0..100) + gating
# ----------------------------
@dataclass
class IHPISubscores:
    safte: float
    pvt: float
    circadian: float
    hrv: float
    hydration: float
    energy_availability: float
    subjective: float
    task_specific: float

DEFAULT_WEIGHTS = {
    "safte": 0.30,
    "pvt": 0.20,
    "circadian": 0.10,
    "hrv": 0.10,
    "hydration": 0.10,
    "energy_availability": 0.10,
    "subjective": 0.05,
    "task_specific": 0.05,
}

def ihpi(sub: IHPISubscores, w: dict = DEFAULT_WEIGHTS) -> float:
    """Compute IHPI with hard-cap gating for critical domains"""
    critical_floor = min(sub.safte, sub.hydration, sub.pvt, sub.subjective)
    if critical_floor <= 0.0:
        return 0.0

    s = (
        w["safte"] * sub.safte +
        w["pvt"] * sub.pvt +
        w["circadian"] * sub.circadian +
        w["hrv"] * sub.hrv +
        w["hydration"] * sub.hydration +
        w["energy_availability"] * sub.energy_availability +
        w["subjective"] * sub.subjective +
        w["task_specific"] * sub.task_specific
    )
    return 100.0 * clamp(s, 0.0, 1.0)

# ----------------------------
# EVA GO/NO-GO (guardrails first, then IHPI)
# ----------------------------
def eva_go_nogo(
    safte_eff: float,
    kss: float,
    sleep_last_24h_h: float,
    time_awake_h: float,
    body_mass_change_pct: float,
    usg: float | None,
    pvt_lapses_3min: int,
    ihpi_value: float,
    vo2max: float,
    hours_since_last_eva: float
) -> tuple[str, list[str]]:
    """EVA GO/NO-GO decision with science-based gates"""
    reasons = []

    # Hard NO-GO gates
    if safte_eff < 70:
        reasons.append("SAFTE effectiveness < 70 (critical risk zone)")
    if kss >= 8:
        reasons.append("KSS >= 8 (severe sleepiness)")
    if sleep_last_24h_h < 6.0:
        reasons.append("Sleep < 6h in last 24h")
    if time_awake_h >= 21:
        reasons.append("Time awake >= 21h (very high risk)")
    if (-body_mass_change_pct) > 2.0:
        reasons.append(">2% body mass loss (hypohydration)")
    if usg is not None and usg >= 1.030:
        reasons.append("USG >= 1.030 (significant hypohydration)")
    if pvt_lapses_3min >= 20:
        reasons.append("3-min PVT lapses >= 20 (low-performance)")
    if vo2max < 32.9:
        reasons.append("VO2max < 32.9 ml/kg/min (NASA EVA requirement)")
    if hours_since_last_eva < 24:
        reasons.append("Time since last EVA < 24h (minimum recovery)")

    if reasons:
        return "NO-GO", reasons

    # Balanced ops gate: SAFTE >= 80
    if safte_eff < 80:
        reasons.append("SAFTE effectiveness 70-79 (high-risk zone)")
        return "HOLD", reasons

    # IHPI-based final decision
    if ihpi_value >= 85:
        return "GO", ["All gates passed; IHPI >= 85"]
    if ihpi_value >= 75:
        return "GO-with-mitigation", [
            "All gates passed; IHPI 75-84 (add mitigation: naps/breaks/task simplification)"
        ]
    return "HOLD", [
        "All gates passed but IHPI < 75 (optimize sleep / delay EVA / reduce workload)"
    ]
```

### or

```python
from dataclasses import dataclass
import math

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

# ----------------------------
# MET / energy conversions
# ----------------------------
def kcal_per_hour_from_met(met: float, mass_kg: float) -> float:
    # 1 MET ≈ 1 kcal/kg/hour
    return met * mass_kg

def watts_from_kcal_per_hour(kcal_h: float) -> float:
    # 1 kcal = 4184 J; 1 hour = 3600 s
    return kcal_h * 4184.0 / 3600.0

def kcal_from_met_duration(met: float, mass_kg: float, minutes: float) -> float:
    return kcal_per_hour_from_met(met, mass_kg) * (minutes / 60.0)

# ----------------------------
# Subscore mappers (0..1)
# ----------------------------
def score_safte(effectiveness_0_100: float) -> float:
    """
    Anchors:
    - >=90: low risk zone (accident risk elevated below 90 in SAFTE validation testimony)
    - <=70: high risk zone (roughly 0.08 BAC / ~21h awake equivalence)
    """
    e = effectiveness_0_100
    if e >= 90: return 1.0
    if e <= 70: return 0.0
    # linear ramp 70->90
    return (e - 70) / 20.0

def score_kss(kss_1_9: float) -> float:
    # 1-5 good; 6 caution; 7 poor; 8-9 no-go territory
    k = kss_1_9
    if k <= 5: return 1.0
    if k >= 8: return 0.0
    # map 5->8 down to 1->0
    return 1.0 - (k - 5) / 3.0

def score_pvt_lapses_3min(lapses: int) -> float:
    """
    Operational anchors (3-min PVT, 355ms lapse threshold):
    ~<=10: high-performance band
    ~>=20: low-performance band
    """
    if lapses <= 10: return 1.0
    if lapses >= 20: return 0.0
    return 1.0 - (lapses - 10) / 10.0

def score_hrv_z(z_lnrmssd: float) -> float:
    # conservative readiness mapping
    if z_lnrmssd >= -0.5: return 1.0
    if z_lnrmssd <= -2.0: return 0.0
    # -0.5 -> -2.0 maps 1 -> 0
    return 1.0 - (abs(z_lnrmssd) - 0.5) / 1.5

def score_hydration(body_mass_change_pct: float, usg: float | None) -> float:
    """
    body_mass_change_pct: negative means loss (e.g., -1.5 for 1.5% loss)
    usg: urine specific gravity
    """
    loss = -body_mass_change_pct  # convert to positive "loss %"
    # body mass: 0% loss best, >2% problematic
    if loss <= 0.5: bm = 1.0
    elif loss >= 2.0: bm = 0.0
    else: bm = 1.0 - (loss - 0.5) / 1.5  # 0.5 -> 2.0

    if usg is None:
        return bm

    # common operational bins: <1.020 euhydrated; >=1.030 significant hypohydration
    if usg < 1.020: u = 1.0
    elif usg >= 1.030: u = 0.0
    else: u = 1.0 - (usg - 1.020) / 0.010  # 1.020 -> 1.030

    # combine (min is conservative)
    return min(bm, u)

def score_energy_availability(EA_kcal_per_kgFFM_day: float) -> float:
    """
    IOC-style anchors:
    - ~45: optimal
    - <30: commonly used "low EA" threshold
    """
    ea = EA_kcal_per_kgFFM_day
    if ea >= 45: return 1.0
    if ea <= 30: return 0.0
    return (ea - 30) / 15.0

def score_circadian_alignment(phase_offset_hours: float) -> float:
    """
    phase_offset_hours: absolute difference between scheduled sleep midpoint and chronotype sleep midpoint.
    """
    d = abs(phase_offset_hours)
    if d <= 1.0: return 1.0
    if d >= 6.0: return 0.0
    return 1.0 - (d - 1.0) / 5.0

def score_task_specific(vo2max_ml_min_kg: float, eva_metabolic_kcal_h: float, mass_kg: float,
                        hours_since_last_eva: float) -> float:
    """
    Minimal placeholder:
    - NASA uses VO2max >= ~32.9 ml/min/kg as EVA-related requirement.
    - Penalize short recovery between EVAs.
    """
    vo2_ok = 1.0 if vo2max_ml_min_kg >= 32.9 else 0.0

    # simple recovery ramp: <24h bad, >=48h good
    if hours_since_last_eva >= 48: rec = 1.0
    elif hours_since_last_eva <= 24: rec = 0.0
    else: rec = (hours_since_last_eva - 24) / 24.0

    return min(vo2_ok, rec)

# ----------------------------
# IHPI composite (0..100) + gating
# ----------------------------
@dataclass
class IHPISubscores:
    safte: float
    pvt: float
    circadian: float
    hrv: float
    hydration: float
    energy_availability: float
    subjective: float
    task_specific: float

DEFAULT_WEIGHTS = {
    "safte": 0.30,
    "pvt": 0.20,
    "circadian": 0.10,
    "hrv": 0.10,
    "hydration": 0.10,
    "energy_availability": 0.10,
    "subjective": 0.05,
    "task_specific": 0.05,
}

def ihpi(sub: IHPISubscores, w: dict = DEFAULT_WEIGHTS) -> float:
    # hard-cap logic: if any critical domain is 0, cap score hard
    critical_floor = min(sub.safte, sub.hydration, sub.pvt, sub.subjective)
    if critical_floor <= 0.0:
        return 0.0

    s = (
        w["safte"] * sub.safte +
        w["pvt"] * sub.pvt +
        w["circadian"] * sub.circadian +
        w["hrv"] * sub.hrv +
        w["hydration"] * sub.hydration +
        w["energy_availability"] * sub.energy_availability +
        w["subjective"] * sub.subjective +
        w["task_specific"] * sub.task_specific
    )
    return 100.0 * clamp(s, 0.0, 1.0)

# ----------------------------
# EVA GO/NO-GO (guardrails first, then IHPI)
# ----------------------------
def eva_go_nogo(
    safte_eff: float,
    kss: float,
    sleep_last_24h_h: float,
    time_awake_h: float,
    body_mass_change_pct: float,
    usg: float | None,
    pvt_lapses_3min: int,
    ihpi_value: float
) -> tuple[str, list[str]]:
    reasons = []

    # Hard NO-GO gates (editable policy)
    if safte_eff < 70:
        reasons.append("SAFTE effectiveness < 70 (high-risk zone)")
    if kss >= 8:
        reasons.append("KSS >= 8 (severe sleepiness)")
    if sleep_last_24h_h < 6.0:
        reasons.append("Sleep < 6h in last 24h")
    if time_awake_h >= 21:
        reasons.append("Time awake >= 21h (very high risk)")
    if (-body_mass_change_pct) > 2.0:
        reasons.append(">2% body mass loss (hypohydration)")
    if usg is not None and usg >= 1.030:
        reasons.append("USG >= 1.030 (significant hypohydration)")
    if pvt_lapses_3min >= 20:
        reasons.append("3-min PVT lapses >= 20 (low-performance band)")

    if reasons:
        return "NO-GO", reasons

    # Soft gate using IHPI (policy choice)
    if ihpi_value >= 85:
        return "GO", ["All gates passed; IHPI >= 85"]
    if ihpi_value >= 75:
        return "GO-with-mitigation", ["All gates passed; IHPI 75–84 (add mitigation: naps/breaks/task simplification)"]
    return "HOLD", ["All gates passed but IHPI < 75 (optimize sleep / delay EVA / reduce workload)"]
```
---

**Key Optimization Benefits:**
1. **Evidence-based**: All parameters grounded in peer-reviewed research and NASA operational standards
2. **Standardized**: Consistent risk assessment framework with validated thresholds
3. **Adaptive**: Dynamic rescheduling based on real-time data
4. **Comprehensive**: Multi-factor human performance integration with gating logic
5. **Scientifically Validated**: SAFTE-FAST, MET values, HRV z-scores, EA thresholds all from peer-reviewed sources
6. **Scalable**: Extensible to other operational domains beyond space
7. **Operationally Coherent**: Energy in kcal/W, acute vs baseline metrics distinguished, safety-dominant optimization


## Summary of Key Scientific Revisions

I've comprehensively updated your document with all the scientific fixes specified in your detailed feedback:

### **Energy & Metabolism**
- Removed BTU/hr; all energy now in **kcal** (nutrition) and **Watts** (thermal/ECLSS)
- Updated MET values to 2024 Adult Compendium standards (sleep 1.0, hygiene 2.0-2.8, briefing 1.3-1.8)
- EVA metabolic cost corrected to measured NASA ranges: ~100-500 kcal/hr, with Skylab mean ~238 kcal/hr and Shuttle average ~194 kcal/hr
- EVA MET revised from 8-10 to realistic **2-7** based on measured data

### **Physiological Thresholds**
- HRV upgraded from "±20% baseline" to **lnRMSSD z-score method** (14-28 day rolling baseline)
- Added **Energy Availability (EA)**: (EI - EEE)/FFM with IOC thresholds (≥45 optimal, <30 red)
- Hydration: Added **USG thresholds** (<1.020, 1.020-1.029, ≥1.030) alongside 2% body mass loss
- NASA VO₂max requirement: **≥32.9 ml/kg/min** for microgravity EVA missions

### **Fatigue Assessment**
- **SAFTE thresholds validated**: ≥90 low-risk, 80-89 caution, 70-79 high-risk, <70 critical (≈0.08 BAC)
- **ESS demoted** from acute gate to baseline screening only (trait-like, not daily decision)
- **PVT calibrated**: 3-min protocol with ≤10/≥20 lapses as performance bands (355ms threshold)
- **KSS retained** as primary acute sleepiness gate (≤5 normal, 6-7 caution, 8-9 NO-GO)

### **Decision Logic**
- EVA GO/NO-GO updated with science-grounded gates (SAFTE ≥80 required, <70 hard NO-GO)
- IHPI reweighted (SAFTE 30%, PVT 20%, EA 10%) with **hard-cap gating** (any critical=0 → IHPI=0)
- Optimization objective changed to **safety-dominant**: mission value - λ×fatigue_risk - μ×circadian_misalignment

### **Implementation**
- Added MET source tracking (`met_source` field for audit trail)
- Provided complete Python science layer with all scoring functions
- Clear operational philosophy choice: **Balanced Ops** (SAFTE ≥80, <70 NO-GO) as default