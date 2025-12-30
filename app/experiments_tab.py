"""
Experiment Management Tab - Mission Science Protocol Tracking.

This module implements a comprehensive experiment management system for
space missions with:
- Experiment protocol form (max 10 experiments per mission)
- Intelligent crew assignment based on IHPI and workload
- Integration with scheduling engine for time allocation
- Troubleshooting guides and procedure tracking

Scientific Foundations:
───────────────────────────────────────────────────────────────────────────
ISS EXPERIMENT SCHEDULING:
  • Marquez JJ, et al. (2019). Lessons Learned from ISS Crew Autonomous
    Scheduling Test. IWPSS 2019. NASA ARC-E-DAA-TN70121.
    → Self-scheduling capability, constraint-aware planning

  • Lee C, Márquez J, Edwards T. (2021). Crew Autonomy through Self-Scheduling:
    Scheduling Performance Pilot Study. AIAA 2021-1578.
    DOI: 10.2514/6.2021-1578
    → Non-expert scheduling performance decreases with complexity

WORKLOAD MANAGEMENT:
  • NASA-STD-3001 Vol 2 Rev D. Human Factors, Habitability, Environmental Health.
    → Cognitive workload limits (Bedford Scale), physical workload (Borg CR-10)

  • NASA OCHMO Cognitive Workload Technical Brief (2023).
    → Task complexity factors for crew scheduling

FATIGUE & PERFORMANCE:
  • Barger LK, et al. (2014). Prevalence of sleep deficiency in astronauts.
    Lancet Neurol. 13(9):904-912. DOI: 10.1016/S1474-4422(14)70122-X
    → Sleep deficiency prevalence, hypnotic use in spaceflight
───────────────────────────────────────────────────────────────────────────

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple, Set

import streamlit as st

try:
    from echarts_component import render_echarts
except ImportError:
    render_echarts = None  # type: ignore[assignment]

try:
    from scheduling_engine import SchedulingEngine, create_sample_crew
    from scheduling_core import (
        CrewMember,
        RiskLevel,
        ActivityCategory,
        compute_ihpi,
    )
    SCHEDULING_AVAILABLE = True
except ImportError:
    SCHEDULING_AVAILABLE = False
    SchedulingEngine = None  # type: ignore[assignment, misc]
    create_sample_crew = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_EXPERIMENTS: Final[int] = 10
MIN_DURATION_MINUTES: Final[int] = 15
MAX_DURATION_MINUTES: Final[int] = 480  # 8 hours
DEFAULT_DURATION_MINUTES: Final[int] = 60

# Experiment status
class ExperimentStatus(str, Enum):
    """Status of an experiment in the mission."""
    DRAFT = "draft"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# Experiment priority levels
class ExperimentPriority(str, Enum):
    """Priority level for experiment scheduling."""
    CRITICAL = "critical"  # Must complete, high science value
    HIGH = "high"  # Important, schedule preferentially
    MEDIUM = "medium"  # Standard science
    LOW = "low"  # Opportunistic, schedule when available
    CONTINGENCY = "contingency"  # Only if time permits


# Cognitive load categories (Bedford Scale alignment)
class CognitiveLoad(str, Enum):
    """Cognitive workload category."""
    LOW = "low"  # Bedford 1-3: Routine, monitoring
    MODERATE = "moderate"  # Bedford 4-5: Complex procedures
    HIGH = "high"  # Bedford 6-7: Critical operations
    VERY_HIGH = "very_high"  # Bedford 8-9: Emergency/time-critical


# Physical load categories (Borg CR-10 alignment)
class PhysicalLoad(str, Enum):
    """Physical workload category."""
    SEDENTARY = "sedentary"  # Borg 0-1: Sitting, observation
    LIGHT = "light"  # Borg 2-3: Standing, light manipulation
    MODERATE = "moderate"  # Borg 4-5: Active work
    HEAVY = "heavy"  # Borg 6-7: Physical exertion
    VERY_HEAVY = "very_heavy"  # Borg 8-10: EVA-level exertion


# Science disciplines (NASA ISS Research categories)
class ScienceDiscipline(str, Enum):
    """Science discipline category."""
    HUMAN_RESEARCH = "Human Research"
    BIOLOGY = "Biology & Biotechnology"
    PHYSICAL_SCIENCES = "Physical Sciences"
    EARTH_OBSERVATION = "Earth & Space Science"
    TECHNOLOGY = "Technology Development"
    EDUCATION = "Education & Outreach"
    COMMERCIAL = "Commercial Research"


# Risk levels for experiment hazards
class ExperimentRiskLevel(str, Enum):
    """Risk level for experiment execution."""
    MINIMAL = "minimal"  # No special precautions
    LOW = "low"  # Standard procedures
    MODERATE = "moderate"  # Enhanced monitoring
    HIGH = "high"  # Requires Flight Surgeon approval
    CRITICAL = "critical"  # Ground control supervision required


# Status colors
STATUS_COLORS: Dict[ExperimentStatus, str] = {
    ExperimentStatus.DRAFT: "#95a5a6",
    ExperimentStatus.APPROVED: "#3498db",
    ExperimentStatus.IN_PROGRESS: "#f39c12",
    ExperimentStatus.PAUSED: "#9b59b6",
    ExperimentStatus.COMPLETED: "#27ae60",
    ExperimentStatus.CANCELLED: "#e74c3c",
}

PRIORITY_COLORS: Dict[ExperimentPriority, str] = {
    ExperimentPriority.CRITICAL: "#e74c3c",
    ExperimentPriority.HIGH: "#f39c12",
    ExperimentPriority.MEDIUM: "#3498db",
    ExperimentPriority.LOW: "#27ae60",
    ExperimentPriority.CONTINGENCY: "#95a5a6",
}

RISK_COLORS: Dict[ExperimentRiskLevel, str] = {
    ExperimentRiskLevel.MINIMAL: "#27ae60",
    ExperimentRiskLevel.LOW: "#2ecc71",
    ExperimentRiskLevel.MODERATE: "#f39c12",
    ExperimentRiskLevel.HIGH: "#e67e22",
    ExperimentRiskLevel.CRITICAL: "#e74c3c",
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ProcedureStep:
    """A single step in the experiment procedure."""
    step_number: int
    title: str
    description: str
    duration_minutes: int
    hazards: str = ""
    safety_notes: str = ""
    crew_required: int = 1
    equipment_needed: List[str] = field(default_factory=list)


@dataclass
class EquipmentItem:
    """Equipment required for the experiment."""
    name: str
    quantity: int = 1
    location: str = ""
    notes: str = ""
    consumable: bool = False


@dataclass
class TroubleshootingEntry:
    """Troubleshooting guide entry."""
    problem: str
    symptoms: str
    cause: str
    solution: str
    escalation: str = ""  # When to contact ground


@dataclass
class ScheduleBlock:
    """A scheduled time block for the experiment."""
    block_id: str
    scheduled_date: date
    start_time: datetime
    end_time: datetime
    assigned_crew: List[str]
    procedure_steps: List[int]  # Step numbers to execute
    status: str = "scheduled"
    notes: str = ""


@dataclass
class Experiment:
    """Complete experiment definition."""
    # Identification
    experiment_id: str
    experiment_number: int  # 1-10
    title: str
    short_code: str  # e.g., "EXP-001"
    
    # Classification
    discipline: ScienceDiscipline
    priority: ExperimentPriority
    status: ExperimentStatus
    risk_level: ExperimentRiskLevel
    
    # Description
    description: str
    objectives: List[str]
    
    # Workload assessment (required fields)
    cognitive_load: CognitiveLoad
    physical_load: PhysicalLoad
    total_duration_minutes: int
    
    # Optional description fields
    hypothesis: str = ""
    expected_outcomes: str = ""
    
    # Optional workload fields
    min_crew_required: int = 1
    max_crew_allowed: int = 2
    
    # Requirements
    equipment: List[EquipmentItem] = field(default_factory=list)
    consumables: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)  # Other experiments that must complete first
    special_conditions: str = ""  # e.g., "Microgravity only", "Post-EVA only"
    
    # Procedure
    procedure_steps: List[ProcedureStep] = field(default_factory=list)
    
    # Scheduling
    schedule_blocks: List[ScheduleBlock] = field(default_factory=list)
    assigned_crew: List[str] = field(default_factory=list)
    primary_operator: str = ""
    backup_operator: str = ""
    
    # Timeline
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    
    # Troubleshooting
    troubleshooting_guide: List[TroubleshootingEntry] = field(default_factory=list)
    
    # Metadata
    principal_investigator: str = ""
    sponsoring_organization: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    def get_completion_percentage(self) -> float:
        """Calculate experiment completion percentage."""
        if not self.schedule_blocks:
            return 0.0
        completed = sum(1 for b in self.schedule_blocks if b.status == "completed")
        return (completed / len(self.schedule_blocks)) * 100.0
    
    def get_remaining_duration_minutes(self) -> int:
        """Calculate remaining time needed."""
        scheduled_minutes = sum(
            (b.end_time - b.start_time).total_seconds() / 60
            for b in self.schedule_blocks
            if b.status != "completed"
        )
        return int(scheduled_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Experiment Storage (Session State)
# ---------------------------------------------------------------------------

def _get_experiments() -> Dict[str, Experiment]:
    """Get experiments from session state."""
    if "mission_experiments" not in st.session_state:
        st.session_state["mission_experiments"] = {}
    return st.session_state["mission_experiments"]


def _save_experiment(experiment: Experiment) -> None:
    """Save experiment to session state."""
    experiments = _get_experiments()
    experiment.updated_at = datetime.now()
    experiments[experiment.experiment_id] = experiment
    st.session_state["mission_experiments"] = experiments


def _delete_experiment(experiment_id: str) -> bool:
    """Delete experiment from session state."""
    experiments = _get_experiments()
    if experiment_id in experiments:
        del experiments[experiment_id]
        st.session_state["mission_experiments"] = experiments
        return True
    return False


def _get_next_experiment_number() -> int:
    """Get the next available experiment number (1-10)."""
    experiments = _get_experiments()
    used_numbers = {e.experiment_number for e in experiments.values()}
    for i in range(1, MAX_EXPERIMENTS + 1):
        if i not in used_numbers:
            return i
    return -1  # All slots used


# ---------------------------------------------------------------------------
# Crew Assignment Intelligence
# ---------------------------------------------------------------------------

def _get_crew_suitability_score(
    crew: CrewMember,
    experiment: Experiment,
) -> Tuple[float, List[str]]:
    """
    Calculate crew suitability score for an experiment.
    
    Returns:
        Tuple of (score 0-100, list of factors)
    
    Based on:
    - IHPI (overall readiness)
    - Cognitive workload capacity
    - Physical workload capacity
    - Current schedule load
    """
    score = 100.0
    factors: List[str] = []
    
    # Get IHPI
    ihpi = crew.get_ihpi()
    
    # IHPI factor (30% weight)
    if ihpi < 60:
        score -= 40
        factors.append(f"⚠️ Low IHPI ({ihpi:.0f})")
    elif ihpi < 75:
        score -= 20
        factors.append(f"⚡ Moderate IHPI ({ihpi:.0f})")
    elif ihpi >= 85:
        factors.append(f"✅ High IHPI ({ihpi:.0f})")
    
    # Cognitive load capacity (25% weight)
    if experiment.cognitive_load == CognitiveLoad.VERY_HIGH:
        if ihpi < 80:
            score -= 25
            factors.append("🧠 High cognitive demand requires higher IHPI")
    elif experiment.cognitive_load == CognitiveLoad.HIGH:
        if ihpi < 70:
            score -= 15
            factors.append("🧠 Complex task may strain capacity")
    
    # Physical load capacity (25% weight)
    if crew.status:
        # Check hydration
        if crew.status.usg and crew.status.usg > 1.025:
            if experiment.physical_load in (PhysicalLoad.HEAVY, PhysicalLoad.VERY_HEAVY):
                score -= 20
                factors.append("💧 Dehydration risk for physical work")
        
        # Check energy availability
        if crew.status.energy_availability and crew.status.energy_availability < 35:
            if experiment.physical_load in (PhysicalLoad.MODERATE, PhysicalLoad.HEAVY, PhysicalLoad.VERY_HEAVY):
                score -= 15
                factors.append("⚡ Low energy availability")
    
    # Role suitability (10% weight) - Placeholder for role-specific matching
    if "Medical" in crew.role and experiment.discipline == ScienceDiscipline.HUMAN_RESEARCH:
        score += 10
        factors.append("👨‍⚕️ Medical Officer suitable for Human Research")
    elif "Engineer" in crew.role and experiment.discipline == ScienceDiscipline.TECHNOLOGY:
        score += 10
        factors.append("🔧 Engineer suitable for Tech Development")
    elif "Data" in crew.role and experiment.discipline == ScienceDiscipline.PHYSICAL_SCIENCES:
        score += 5
        factors.append("📊 Data Officer suitable for Physical Sciences")
    
    # Clamp score
    score = max(0.0, min(100.0, score))
    
    return score, factors


def _rank_crew_for_experiment(
    experiment: Experiment,
    engine: Optional[Any] = None,
) -> List[Tuple[CrewMember, float, List[str]]]:
    """
    Rank all crew members by suitability for an experiment.
    
    Returns:
        List of (crew, score, factors) sorted by score descending
    """
    if engine is None or not hasattr(engine, 'crew_members'):
        return []
    
    rankings: List[Tuple[CrewMember, float, List[str]]] = []
    
    for crew in engine.crew_members.values():
        score, factors = _get_crew_suitability_score(crew, experiment)
        rankings.append((crew, score, factors))
    
    # Sort by score descending
    rankings.sort(key=lambda x: x[1], reverse=True)
    
    return rankings


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def _render_experiment_card(experiment: Experiment) -> None:
    """Render a compact experiment card."""
    status_color = STATUS_COLORS.get(experiment.status, "#888")
    priority_color = PRIORITY_COLORS.get(experiment.priority, "#888")
    completion = experiment.get_completion_percentage()
    
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border-left: 4px solid {priority_color};
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="
                        background: {priority_color}22;
                        color: {priority_color};
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 0.75em;
                        font-weight: 600;
                    ">{experiment.short_code}</span>
                    <span style="
                        background: {status_color}22;
                        color: {status_color};
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 0.75em;
                        font-weight: 600;
                        margin-left: 8px;
                    ">{experiment.status.value.upper()}</span>
                </div>
                <div style="color: #94a3b8; font-size: 0.85em;">
                    {experiment.discipline.value}
                </div>
            </div>
            <div style="margin-top: 10px;">
                <div style="font-weight: 600; color: #f1f5f9; font-size: 1.1em;">
                    {experiment.title}
                </div>
                <div style="color: #94a3b8; font-size: 0.9em; margin-top: 4px;">
                    {experiment.description[:150]}{'...' if len(experiment.description) > 150 else ''}
                </div>
            </div>
            <div style="margin-top: 12px; display: flex; gap: 16px; color: #cbd5e1; font-size: 0.85em;">
                <span>⏱️ {experiment.total_duration_minutes} min</span>
                <span>👥 {experiment.min_crew_required}-{experiment.max_crew_allowed} crew</span>
                <span>📈 {completion:.0f}% complete</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_experiment_form(
    experiment: Optional[Experiment] = None,
    engine: Optional[Any] = None,
) -> Optional[Experiment]:
    """
    Render the experiment creation/editing form.
    
    Returns:
        Experiment if saved, None otherwise
    """
    is_edit = experiment is not None
    form_key = f"exp_form_{experiment.experiment_id if experiment else 'new'}"
    
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #3b82f6;
        ">
            <h3 style="margin: 0; color: #fff;">
                📋 {'Edit' if is_edit else 'New'} Experiment Protocol
            </h3>
            <p style="margin: 8px 0 0 0; color: #93c5fd; font-size: 0.9em;">
                Define experiment parameters following NASA ISS Research standards
            </p>
        </div>
        """.replace("{'Edit' if is_edit else 'New'}", "Edit" if is_edit else "New"),
        unsafe_allow_html=True,
    )
    
    # Check capacity
    if not is_edit:
        next_num = _get_next_experiment_number()
        if next_num == -1:
            st.error(f"❌ Maximum {MAX_EXPERIMENTS} experiments reached. Delete an experiment to add a new one.")
            return None
    
    with st.form(form_key):
        # Section 1: Basic Information
        st.markdown("#### 1️⃣ Basic Information")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            title = st.text_input(
                "Experiment Title *",
                value=experiment.title if experiment else "",
                max_chars=100,
                help="Clear, descriptive title for the experiment",
            )
        
        with col2:
            short_code = st.text_input(
                "Short Code *",
                value=experiment.short_code if experiment else f"EXP-{next_num:03d}" if not is_edit else "",
                max_chars=10,
                help="e.g., EXP-001, BIO-003",
            )
        
        with col3:
            exp_number = st.number_input(
                "Experiment # (1-10)",
                min_value=1,
                max_value=MAX_EXPERIMENTS,
                value=experiment.experiment_number if experiment else (next_num if not is_edit else 1),
                help="Slot number (max 10 experiments)",
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            discipline = st.selectbox(
                "Science Discipline *",
                options=[d.value for d in ScienceDiscipline],
                index=[d.value for d in ScienceDiscipline].index(experiment.discipline.value) if experiment else 0,
            )
        
        with col2:
            priority = st.selectbox(
                "Priority Level *",
                options=[p.value.title() for p in ExperimentPriority],
                index=[p.value for p in ExperimentPriority].index(experiment.priority.value) if experiment else 2,
            )
        
        with col3:
            status = st.selectbox(
                "Status",
                options=[s.value.title() for s in ExperimentStatus],
                index=[s.value for s in ExperimentStatus].index(experiment.status.value) if experiment else 0,
            )
        
        # Section 2: Description & Objectives
        st.markdown("---")
        st.markdown("#### 2️⃣ Description & Objectives")
        
        description = st.text_area(
            "Experiment Description *",
            value=experiment.description if experiment else "",
            height=100,
            help="Detailed description of what the experiment investigates",
        )
        
        objectives_text = st.text_area(
            "Objectives (one per line) *",
            value="\n".join(experiment.objectives) if experiment and experiment.objectives else "",
            height=100,
            help="List each objective on a separate line",
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            hypothesis = st.text_area(
                "Hypothesis",
                value=experiment.hypothesis if experiment else "",
                height=80,
                help="Scientific hypothesis being tested",
            )
        
        with col2:
            expected_outcomes = st.text_area(
                "Expected Outcomes",
                value=experiment.expected_outcomes if experiment else "",
                height=80,
                help="What results are expected",
            )
        
        # Section 3: Workload & Requirements
        st.markdown("---")
        st.markdown("#### 3️⃣ Workload Assessment & Requirements")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cognitive_load = st.selectbox(
                "Cognitive Load",
                options=[c.value.title() for c in CognitiveLoad],
                index=[c.value for c in CognitiveLoad].index(experiment.cognitive_load.value) if experiment else 1,
                help="Bedford Scale: Low (1-3), Moderate (4-5), High (6-7), Very High (8-9)",
            )
        
        with col2:
            physical_load = st.selectbox(
                "Physical Load",
                options=[p.value.title() for p in PhysicalLoad],
                index=[p.value for p in PhysicalLoad].index(experiment.physical_load.value) if experiment else 1,
                help="Borg CR-10 Scale alignment",
            )
        
        with col3:
            risk_level = st.selectbox(
                "Risk Level",
                options=[r.value.title() for r in ExperimentRiskLevel],
                index=[r.value for r in ExperimentRiskLevel].index(experiment.risk_level.value) if experiment else 1,
            )
        
        with col4:
            total_duration = st.number_input(
                "Total Duration (min)",
                min_value=MIN_DURATION_MINUTES,
                max_value=MAX_DURATION_MINUTES,
                value=experiment.total_duration_minutes if experiment else DEFAULT_DURATION_MINUTES,
                step=15,
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_crew = st.number_input(
                "Min Crew Required",
                min_value=1,
                max_value=6,
                value=experiment.min_crew_required if experiment else 1,
            )
        
        with col2:
            max_crew = st.number_input(
                "Max Crew Allowed",
                min_value=1,
                max_value=6,
                value=experiment.max_crew_allowed if experiment else 2,
            )
        
        with col3:
            special_conditions = st.text_input(
                "Special Conditions",
                value=experiment.special_conditions if experiment else "",
                help="e.g., 'Post-EVA only', 'Requires darkness'",
            )
        
        # Section 4: Equipment
        st.markdown("---")
        st.markdown("#### 4️⃣ Equipment & Consumables")
        
        equipment_text = st.text_area(
            "Equipment List (one per line, format: Name | Quantity | Location)",
            value="\n".join(
                f"{e.name} | {e.quantity} | {e.location}"
                for e in experiment.equipment
            ) if experiment and experiment.equipment else "",
            height=100,
            help="Example: Heart Rate Monitor | 2 | Lab Module A",
        )
        
        consumables_text = st.text_area(
            "Consumables (one per line)",
            value="\n".join(experiment.consumables) if experiment and experiment.consumables else "",
            height=60,
            help="List all consumable materials needed",
        )
        
        # Section 5: Procedure Steps
        st.markdown("---")
        st.markdown("#### 5️⃣ Procedure Steps")
        
        st.info("📝 Enter procedure steps in JSON format or use the simplified format below")
        
        procedure_text = st.text_area(
            "Procedure Steps (format: Step# | Title | Description | Duration(min))",
            value="\n".join(
                f"{s.step_number} | {s.title} | {s.description} | {s.duration_minutes}"
                for s in experiment.procedure_steps
            ) if experiment and experiment.procedure_steps else "1 | Setup | Prepare equipment and workspace | 10\n2 | Calibration | Calibrate instruments | 5\n3 | Data Collection | Execute main procedure | 30\n4 | Cleanup | Secure equipment and clean area | 15",
            height=150,
            help="One step per line: Step# | Title | Description | Duration(min)",
        )
        
        # Section 6: Schedule & Assignment
        st.markdown("---")
        st.markdown("#### 6️⃣ Schedule & Crew Assignment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            planned_start = st.date_input(
                "Planned Start Date",
                value=experiment.planned_start_date if experiment and experiment.planned_start_date else date.today(),
            )
        
        with col2:
            planned_end = st.date_input(
                "Planned End Date",
                value=experiment.planned_end_date if experiment and experiment.planned_end_date else date.today() + timedelta(days=7),
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            primary_operator = st.text_input(
                "Primary Operator",
                value=experiment.primary_operator if experiment else "",
                help="Crew member primarily responsible",
            )
        
        with col2:
            backup_operator = st.text_input(
                "Backup Operator",
                value=experiment.backup_operator if experiment else "",
                help="Backup crew member",
            )
        
        # Section 7: Troubleshooting
        st.markdown("---")
        st.markdown("#### 7️⃣ Troubleshooting Guide")
        
        troubleshooting_text = st.text_area(
            "Troubleshooting Entries (format: Problem | Symptoms | Cause | Solution | Escalation)",
            value="\n".join(
                f"{t.problem} | {t.symptoms} | {t.cause} | {t.solution} | {t.escalation}"
                for t in experiment.troubleshooting_guide
            ) if experiment and experiment.troubleshooting_guide else "",
            height=100,
            help="One entry per line",
        )
        
        # Section 8: Metadata
        st.markdown("---")
        st.markdown("#### 8️⃣ Metadata")
        
        col1, col2 = st.columns(2)
        
        with col1:
            principal_investigator = st.text_input(
                "Principal Investigator",
                value=experiment.principal_investigator if experiment else "",
            )
        
        with col2:
            sponsoring_org = st.text_input(
                "Sponsoring Organization",
                value=experiment.sponsoring_organization if experiment else "",
            )
        
        notes = st.text_area(
            "Additional Notes",
            value=experiment.notes if experiment else "",
            height=60,
        )
        
        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submitted = st.form_submit_button(
                "💾 Save Experiment",
                type="primary",
                use_container_width=True,
            )
        
        with col2:
            if is_edit:
                delete_clicked = st.form_submit_button(
                    "🗑️ Delete",
                    type="secondary",
                    use_container_width=True,
                )
            else:
                delete_clicked = False
        
        if submitted:
            # Validate required fields
            if not title or not short_code or not description or not objectives_text.strip():
                st.error("❌ Please fill in all required fields (marked with *)")
                return None
            
            # Parse objectives
            objectives = [o.strip() for o in objectives_text.strip().split("\n") if o.strip()]
            
            # Parse equipment
            equipment_list: List[EquipmentItem] = []
            for line in equipment_text.strip().split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 1:
                        equipment_list.append(EquipmentItem(
                            name=parts[0],
                            quantity=int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1,
                            location=parts[2] if len(parts) > 2 else "",
                        ))
            
            # Parse consumables
            consumables = [c.strip() for c in consumables_text.strip().split("\n") if c.strip()]
            
            # Parse procedure steps
            procedure_steps: List[ProcedureStep] = []
            for line in procedure_text.strip().split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        try:
                            step_num = int(parts[0])
                            duration = int(parts[3])
                            procedure_steps.append(ProcedureStep(
                                step_number=step_num,
                                title=parts[1],
                                description=parts[2],
                                duration_minutes=duration,
                            ))
                        except ValueError:
                            pass
            
            # Parse troubleshooting
            troubleshooting: List[TroubleshootingEntry] = []
            for line in troubleshooting_text.strip().split("\n"):
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        troubleshooting.append(TroubleshootingEntry(
                            problem=parts[0],
                            symptoms=parts[1],
                            cause=parts[2],
                            solution=parts[3],
                            escalation=parts[4] if len(parts) > 4 else "",
                        ))
            
            # Create or update experiment
            new_experiment = Experiment(
                experiment_id=experiment.experiment_id if experiment else str(uuid.uuid4()),
                experiment_number=exp_number,
                title=title,
                short_code=short_code,
                discipline=ScienceDiscipline(discipline),
                priority=ExperimentPriority(priority.lower()),
                status=ExperimentStatus(status.lower()),
                risk_level=ExperimentRiskLevel(risk_level.lower()),
                description=description,
                objectives=objectives,
                hypothesis=hypothesis,
                expected_outcomes=expected_outcomes,
                cognitive_load=CognitiveLoad(cognitive_load.lower()),
                physical_load=PhysicalLoad(physical_load.lower()),
                total_duration_minutes=total_duration,
                min_crew_required=min_crew,
                max_crew_allowed=max_crew,
                special_conditions=special_conditions,
                equipment=equipment_list,
                consumables=consumables,
                procedure_steps=procedure_steps,
                planned_start_date=planned_start,
                planned_end_date=planned_end,
                primary_operator=primary_operator,
                backup_operator=backup_operator,
                troubleshooting_guide=troubleshooting,
                principal_investigator=principal_investigator,
                sponsoring_organization=sponsoring_org,
                notes=notes,
                created_at=experiment.created_at if experiment else datetime.now(),
                schedule_blocks=experiment.schedule_blocks if experiment else [],
                assigned_crew=experiment.assigned_crew if experiment else [],
            )
            
            _save_experiment(new_experiment)
            st.success(f"✅ Experiment '{title}' saved successfully!")
            return new_experiment
        
        if delete_clicked and is_edit and experiment:
            _delete_experiment(experiment.experiment_id)
            st.success(f"🗑️ Experiment '{experiment.title}' deleted.")
            st.rerun()
    
    return None


def _render_crew_assignment_panel(
    experiment: Experiment,
    engine: Optional[Any] = None,
) -> None:
    """Render intelligent crew assignment panel."""
    st.markdown("### 👥 Intelligent Crew Assignment")
    
    if engine is None or not SCHEDULING_AVAILABLE:
        st.warning("Scheduling engine not available. Manual assignment only.")
        return
    
    # Get crew rankings
    rankings = _rank_crew_for_experiment(experiment, engine)
    
    if not rankings:
        st.info("No crew members available for ranking.")
        return
    
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #14532d22, #16653422);
            border: 1px solid #22c55e;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 16px;
        ">
            <div style="color: #4ade80; font-weight: 600; margin-bottom: 4px;">
                🧠 AI Crew Recommendations
            </div>
            <div style="color: #86efac; font-size: 0.9em;">
                Rankings based on IHPI, workload capacity, and role suitability
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    for idx, (crew, score, factors) in enumerate(rankings):
        # Determine recommendation level
        if score >= 80:
            rec_color = "#22c55e"
            rec_label = "Highly Recommended"
        elif score >= 60:
            rec_color = "#f59e0b"
            rec_label = "Suitable"
        elif score >= 40:
            rec_color = "#ef4444"
            rec_label = "Caution"
        else:
            rec_color = "#991b1b"
            rec_label = "Not Recommended"
        
        with st.expander(f"**{idx + 1}. {crew.name}** — {rec_label} ({score:.0f}%)", expanded=(idx == 0)):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown(
                    f"""
                    <div style="
                        background: {rec_color}22;
                        border: 2px solid {rec_color};
                        border-radius: 50%;
                        width: 80px;
                        height: 80px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0 auto;
                    ">
                        <span style="font-size: 1.8em; font-weight: 700; color: {rec_color};">
                            {score:.0f}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(f"Role: {crew.role}")
            
            with col2:
                st.markdown("**Suitability Factors:**")
                for factor in factors:
                    st.markdown(f"- {factor}")
            
            # Assignment buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Set as Primary", key=f"primary_{crew.crew_id}_{experiment.experiment_id}"):
                    experiment.primary_operator = crew.name
                    _save_experiment(experiment)
                    st.success(f"✅ {crew.name} set as Primary Operator")
                    st.rerun()
            
            with col2:
                if st.button(f"Set as Backup", key=f"backup_{crew.crew_id}_{experiment.experiment_id}"):
                    experiment.backup_operator = crew.name
                    _save_experiment(experiment)
                    st.success(f"✅ {crew.name} set as Backup Operator")
                    st.rerun()


def _render_schedule_integration_panel(
    experiment: Experiment,
    engine: Optional[Any] = None,
) -> None:
    """Render scheduling integration panel."""
    st.markdown("### 📅 Schedule Integration")
    
    if engine is None or not SCHEDULING_AVAILABLE:
        st.warning("Scheduling engine not available.")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Duration",
            f"{experiment.total_duration_minutes} min",
            help="Total experiment time",
        )
    
    with col2:
        scheduled_minutes = sum(
            (b.end_time - b.start_time).total_seconds() / 60
            for b in experiment.schedule_blocks
        )
        st.metric(
            "Scheduled",
            f"{scheduled_minutes:.0f} min",
            delta=f"{scheduled_minutes - experiment.total_duration_minutes:.0f} min" if scheduled_minutes else None,
        )
    
    with col3:
        completion = experiment.get_completion_percentage()
        st.metric(
            "Completion",
            f"{completion:.0f}%",
        )
    
    # Quick schedule form
    st.markdown("---")
    st.markdown("#### ➕ Add Schedule Block")
    
    with st.form(f"schedule_block_{experiment.experiment_id}"):
        col1, col2 = st.columns(2)
        
        with col1:
            block_date = st.date_input(
                "Date",
                value=experiment.planned_start_date or date.today(),
            )
        
        with col2:
            block_duration = st.number_input(
                "Duration (min)",
                min_value=15,
                max_value=experiment.total_duration_minutes,
                value=min(60, experiment.total_duration_minutes),
                step=15,
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_hour = st.selectbox(
                "Start Hour",
                options=list(range(6, 22)),
                index=3,  # 9 AM
            )
        
        with col2:
            start_minute = st.selectbox(
                "Start Minute",
                options=[0, 15, 30, 45],
                index=0,
            )
        
        # Crew selection
        crew_options = [c.name for c in engine.crew_members.values()]
        assigned = st.multiselect(
            "Assigned Crew",
            options=crew_options,
            default=[experiment.primary_operator] if experiment.primary_operator in crew_options else [],
        )
        
        block_notes = st.text_input("Notes", value="")
        
        if st.form_submit_button("➕ Add Block", type="primary"):
            start_dt = datetime.combine(
                block_date,
                datetime.strptime(f"{start_hour}:{start_minute}", "%H:%M").time()
            )
            end_dt = start_dt + timedelta(minutes=block_duration)
            
            new_block = ScheduleBlock(
                block_id=str(uuid.uuid4()),
                scheduled_date=block_date,
                start_time=start_dt,
                end_time=end_dt,
                assigned_crew=assigned,
                procedure_steps=[],
                notes=block_notes,
            )
            
            experiment.schedule_blocks.append(new_block)
            _save_experiment(experiment)
            st.success("✅ Schedule block added!")
            st.rerun()
    
    # Show existing blocks
    if experiment.schedule_blocks:
        st.markdown("#### 📋 Scheduled Blocks")
        for block in sorted(experiment.schedule_blocks, key=lambda b: b.start_time):
            status_color = "#22c55e" if block.status == "completed" else "#3b82f6"
            st.markdown(
                f"""
                <div style="
                    background: #1e293b;
                    border-left: 3px solid {status_color};
                    padding: 10px 14px;
                    border-radius: 4px;
                    margin: 6px 0;
                ">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #f1f5f9; font-weight: 500;">
                            📅 {block.scheduled_date.strftime('%Y-%m-%d')} | {block.start_time.strftime('%H:%M')} - {block.end_time.strftime('%H:%M')}
                        </span>
                        <span style="color: #94a3b8; font-size: 0.85em;">
                            {block.status.upper()}
                        </span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.85em; margin-top: 4px;">
                        👥 {', '.join(block.assigned_crew) if block.assigned_crew else 'Unassigned'}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_experiments_overview(engine: Optional[Any] = None) -> None:
    """Render experiments overview dashboard."""
    experiments = _get_experiments()
    
    # Header with stats
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 50%, #3b82f6 100%);
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid #60a5fa;
        ">
            <h2 style="margin: 0; color: #fff;">
                🔬 Mission Experiments
            </h2>
            <p style="margin: 8px 0 0 0; color: #bfdbfe; font-size: 0.95em;">
                {len(experiments)}/{MAX_EXPERIMENTS} experiment slots in use
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Quick stats
    if experiments:
        col1, col2, col3, col4 = st.columns(4)
        
        in_progress = sum(1 for e in experiments.values() if e.status == ExperimentStatus.IN_PROGRESS)
        completed = sum(1 for e in experiments.values() if e.status == ExperimentStatus.COMPLETED)
        total_hours = sum(e.total_duration_minutes for e in experiments.values()) / 60
        
        with col1:
            st.metric("Total Experiments", len(experiments))
        with col2:
            st.metric("In Progress", in_progress)
        with col3:
            st.metric("Completed", completed)
        with col4:
            st.metric("Total Hours", f"{total_hours:.1f}")
    
    st.markdown("---")
    
    # Experiment cards
    if experiments:
        for exp in sorted(experiments.values(), key=lambda e: e.experiment_number):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                _render_experiment_card(exp)
            
            with col2:
                st.write("")  # Spacer
                if st.button("📝 Edit", key=f"edit_{exp.experiment_id}"):
                    st.session_state["editing_experiment"] = exp.experiment_id
                    st.rerun()
                if st.button("📅 Schedule", key=f"sched_{exp.experiment_id}"):
                    st.session_state["scheduling_experiment"] = exp.experiment_id
                    st.rerun()
    else:
        st.info("No experiments defined yet. Create your first experiment to get started!")


# ---------------------------------------------------------------------------
# Main Tab Renderer
# ---------------------------------------------------------------------------

def render_experiments_tab() -> None:
    """Render the complete experiments management tab."""
    
    # Initialize scheduling engine
    engine = None
    if SCHEDULING_AVAILABLE and create_sample_crew is not None:
        if "scheduling_engine" not in st.session_state:
            crew = create_sample_crew()
            st.session_state["scheduling_engine"] = SchedulingEngine(crew_members=crew)
        engine = st.session_state.get("scheduling_engine")
    
    # Navigation
    experiments = _get_experiments()
    
    # Check for edit/schedule mode
    editing_id = st.session_state.get("editing_experiment")
    scheduling_id = st.session_state.get("scheduling_experiment")
    
    if editing_id and editing_id in experiments:
        # Edit mode
        exp = experiments[editing_id]
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to List"):
                st.session_state.pop("editing_experiment", None)
                st.rerun()
        
        _render_experiment_form(experiment=exp, engine=engine)
        
        st.markdown("---")
        _render_crew_assignment_panel(exp, engine)
        
    elif scheduling_id and scheduling_id in experiments:
        # Schedule mode
        exp = experiments[scheduling_id]
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to List"):
                st.session_state.pop("scheduling_experiment", None)
                st.rerun()
        
        st.markdown(f"## 📅 Schedule: {exp.title}")
        
        _render_schedule_integration_panel(exp, engine)
        
        st.markdown("---")
        _render_crew_assignment_panel(exp, engine)
        
    else:
        # Overview mode
        tab1, tab2 = st.tabs(["📋 Experiments Overview", "➕ New Experiment"])
        
        with tab1:
            _render_experiments_overview(engine)
        
        with tab2:
            result = _render_experiment_form(engine=engine)
            if result:
                st.rerun()


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

EXPERIMENTS_TAB_AVAILABLE = True

__all__ = [
    "render_experiments_tab",
    "Experiment",
    "ExperimentStatus",
    "ExperimentPriority",
    "ScienceDiscipline",
    "EXPERIMENTS_TAB_AVAILABLE",
]

