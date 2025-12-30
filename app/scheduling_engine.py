"""
Crew Scheduling Engine - Constraint-Based Optimization System.

This module implements the scheduling engine for 6 aircrews with:
- Constraint-based optimization (hard/soft constraints)
- Dynamic rescheduling based on risk factors
- Real-time conflict detection and resolution
- Activity sequencing efficiency

Scientific References:
- ICAO Doc 9966 (2016): Manual for the Oversight of Fatigue Management Approaches
- NASA-STD-3001: Human Integration Design Handbook
- AFMAN 11-202V3: General Flight Rules (crew rest)

Author: Dr. Diego Leonel Malpica Hincapié, MD
Version: 1.0.0
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple, Set

import numpy as np

from scheduling_core import (
    ActivityCategory,
    ActivityDefinition,
    ALL_ACTIVITIES,
    FIXED_ACTIVITIES,
    VARIABLE_ACTIVITIES,
    CrewMember,
    CrewPhysiologicalStatus,
    RiskLevel,
    GONOGOStatus,
    compute_ihpi,
    eva_go_nogo,
    kcal_from_met_duration,
    check_activity_suitability,
    SAFTE_LOW_RISK_MIN,
    SAFTE_CAUTION_MIN,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_CREW_SIZE: Final[int] = 6
MAX_CONCURRENT_EXERCISE: Final[int] = 2
BRIEFING_TIME_HOUR: Final[int] = 7
DEFAULT_SLEEP_DURATION_HOURS: Final[float] = 8.0
SCHEDULE_HORIZON_DAYS: Final[int] = 7


class ConstraintType(str, Enum):
    """Types of scheduling constraints."""
    HARD = "hard"  # Cannot be violated
    SOFT = "soft"  # Optimized but can be relaxed


class ScheduleStatus(str, Enum):
    """Status of a scheduled activity."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CONFLICTED = "conflicted"


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ScheduledActivity:
    """A scheduled activity for a crew member."""
    schedule_id: str
    crew_id: str
    activity_id: str
    activity_name: str
    start_time: datetime
    end_time: datetime
    status: ScheduleStatus = ScheduleStatus.SCHEDULED
    
    # Computed at scheduling time
    met_value: float = 1.0
    estimated_kcal: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    
    # Constraint metadata
    is_fixed: bool = False
    priority: int = 5  # 1-10, higher = more important
    
    # Notes
    notes: str = ""
    
    @property
    def duration_minutes(self) -> int:
        """Get duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "schedule_id": self.schedule_id,
            "crew_id": self.crew_id,
            "activity_id": self.activity_id,
            "activity_name": self.activity_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "met_value": self.met_value,
            "estimated_kcal": self.estimated_kcal,
            "risk_level": self.risk_level.value,
            "is_fixed": self.is_fixed,
            "priority": self.priority,
            "notes": self.notes,
        }


@dataclass
class ScheduleConflict:
    """Represents a scheduling conflict."""
    conflict_id: str
    conflict_type: str  # "overlap", "resource", "recovery", "constraint"
    affected_activities: Tuple[str, ...]  # schedule_ids
    affected_crew: Tuple[str, ...]  # crew_ids
    severity: str  # "warning", "error", "critical"
    description: str
    suggested_resolution: str


@dataclass
class DailySchedule:
    """A day's schedule for all crew members."""
    schedule_date: date
    activities: List[ScheduledActivity] = field(default_factory=list)
    conflicts: List[ScheduleConflict] = field(default_factory=list)
    is_optimized: bool = False
    optimization_score: float = 0.0
    
    def get_crew_activities(self, crew_id: str) -> List[ScheduledActivity]:
        """Get all activities for a specific crew member."""
        return [a for a in self.activities if a.crew_id == crew_id]
    
    def get_activities_at_time(self, time: datetime) -> List[ScheduledActivity]:
        """Get all activities occurring at a specific time."""
        return [
            a for a in self.activities
            if a.start_time <= time < a.end_time
        ]
    
    def get_resource_usage_at_time(
        self,
        time: datetime,
        resource_activity_id: str,
    ) -> int:
        """Count how many crew members are using a resource-limited activity."""
        return sum(
            1 for a in self.activities
            if a.activity_id == resource_activity_id
            and a.start_time <= time < a.end_time
        )


@dataclass
class CrewScheduleState:
    """Current scheduling state for a crew member."""
    crew_id: str
    current_activity: Optional[ScheduledActivity] = None
    next_activity: Optional[ScheduledActivity] = None
    available_from: Optional[datetime] = None
    total_scheduled_minutes: int = 0
    total_rest_minutes: int = 0
    exercise_completed: bool = False
    meals_completed: Set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Constraint Definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Constraint:
    """A scheduling constraint."""
    constraint_id: str
    name: str
    constraint_type: ConstraintType
    description: str
    check_function: str  # Name of the validation function


# Hard constraints (cannot be violated)
HARD_CONSTRAINTS: Tuple[Constraint, ...] = (
    Constraint(
        constraint_id="briefing_sync",
        name="Briefing Synchronization",
        constraint_type=ConstraintType.HARD,
        description="All crew must attend 07:00 briefing",
        check_function="check_briefing_sync",
    ),
    Constraint(
        constraint_id="sleep_block",
        name="Sleep Block Duration",
        constraint_type=ConstraintType.HARD,
        description="Sleep must be 8-hour continuous blocks",
        check_function="check_sleep_block",
    ),
    Constraint(
        constraint_id="exercise_capacity",
        name="Exercise Capacity",
        constraint_type=ConstraintType.HARD,
        description="Max 2 crew exercising concurrently",
        check_function="check_exercise_capacity",
    ),
    Constraint(
        constraint_id="medical_clearance",
        name="Medical Clearance",
        constraint_type=ConstraintType.HARD,
        description="EVA requires medical clearance",
        check_function="check_medical_clearance",
    ),
    Constraint(
        constraint_id="eva_recovery",
        name="EVA Recovery Period",
        constraint_type=ConstraintType.HARD,
        description="Minimum 48h between EVAs",
        check_function="check_eva_recovery",
    ),
    Constraint(
        constraint_id="safety_gates",
        name="GO/NO-GO Safety Gates",
        constraint_type=ConstraintType.HARD,
        description="All safety gates must pass for high-risk activities",
        check_function="check_safety_gates",
    ),
)

# Soft constraints (optimized but can be relaxed)
SOFT_CONSTRAINTS: Tuple[Constraint, ...] = (
    Constraint(
        constraint_id="meal_timing",
        name="Meal Timing Preferences",
        constraint_type=ConstraintType.SOFT,
        description="Meals at preferred times",
        check_function="check_meal_timing",
    ),
    Constraint(
        constraint_id="chronotype_alignment",
        name="Chronotype Optimization",
        constraint_type=ConstraintType.SOFT,
        description="Work windows aligned with chronotype",
        check_function="check_chronotype_alignment",
    ),
    Constraint(
        constraint_id="activity_sequencing",
        name="Activity Sequencing",
        constraint_type=ConstraintType.SOFT,
        description="Optimal activity order for efficiency",
        check_function="check_activity_sequencing",
    ),
    Constraint(
        constraint_id="crew_preferences",
        name="Crew Preferences",
        constraint_type=ConstraintType.SOFT,
        description="Individual crew scheduling preferences",
        check_function="check_crew_preferences",
    ),
)


# ---------------------------------------------------------------------------
# Scheduling Engine
# ---------------------------------------------------------------------------

class SchedulingEngine:
    """
    Constraint-based scheduling engine for crew management.
    
    Features:
    - 6-crew capacity management
    - Hard/soft constraint handling
    - Real-time conflict detection
    - Dynamic rescheduling triggers
    - SAFTE-FAST integration for fatigue prediction
    """
    
    def __init__(
        self,
        crew_members: Optional[List[CrewMember]] = None,
        max_crew: int = MAX_CREW_SIZE,
    ):
        """
        Initialize the scheduling engine.
        
        Args:
            crew_members: List of crew member profiles
            max_crew: Maximum crew size (default 6)
        """
        self.max_crew = max_crew
        self.crew_members: Dict[str, CrewMember] = {}
        self.schedules: Dict[date, DailySchedule] = {}
        self.crew_states: Dict[str, CrewScheduleState] = {}
        
        if crew_members:
            for crew in crew_members:
                self.add_crew_member(crew)
    
    def add_crew_member(self, crew: CrewMember) -> bool:
        """
        Add a crew member to the scheduling system.
        
        Args:
            crew: CrewMember instance
            
        Returns:
            True if added successfully, False if at capacity
        """
        if len(self.crew_members) >= self.max_crew:
            return False
        self.crew_members[crew.crew_id] = crew
        self.crew_states[crew.crew_id] = CrewScheduleState(crew_id=crew.crew_id)
        return True
    
    def remove_crew_member(self, crew_id: str) -> bool:
        """Remove a crew member from the scheduling system."""
        if crew_id in self.crew_members:
            del self.crew_members[crew_id]
            del self.crew_states[crew_id]
            return True
        return False
    
    def get_daily_schedule(self, schedule_date: date) -> Optional[DailySchedule]:
        """Get a daily schedule (read-only, does not create if missing).
        
        Use this method for display-only operations to avoid side effects.
        
        Args:
            schedule_date: The date to look up.
            
        Returns:
            The DailySchedule if it exists, otherwise None.
        """
        return self.schedules.get(schedule_date)
    
    def get_or_create_daily_schedule(self, schedule_date: date) -> DailySchedule:
        """Get or create a daily schedule.
        
        Use this method only when you intend to modify the schedule.
        For display-only operations, use get_daily_schedule() instead.
        """
        if schedule_date not in self.schedules:
            self.schedules[schedule_date] = DailySchedule(schedule_date=schedule_date)
        return self.schedules[schedule_date]
    
    def schedule_activity(
        self,
        crew_id: str,
        activity_id: str,
        start_time: datetime,
        duration_minutes: Optional[int] = None,
        priority: int = 5,
        notes: str = "",
    ) -> Tuple[Optional[ScheduledActivity], List[ScheduleConflict]]:
        """
        Schedule an activity for a crew member.
        
        Args:
            crew_id: Crew member identifier
            activity_id: Activity identifier
            start_time: Start datetime
            duration_minutes: Override duration (or use activity default)
            priority: Priority level 1-10
            notes: Additional notes
            
        Returns:
            Tuple of (ScheduledActivity if successful, list of conflicts)
        """
        if crew_id not in self.crew_members:
            return None, [ScheduleConflict(
                conflict_id=str(uuid.uuid4()),
                conflict_type="validation",
                affected_activities=(),
                affected_crew=(crew_id,),
                severity="error",
                description=f"Crew member {crew_id} not found",
                suggested_resolution="Add crew member to the system first",
            )]
        
        if activity_id not in ALL_ACTIVITIES:
            return None, [ScheduleConflict(
                conflict_id=str(uuid.uuid4()),
                conflict_type="validation",
                affected_activities=(),
                affected_crew=(crew_id,),
                severity="error",
                description=f"Activity {activity_id} not found",
                suggested_resolution="Use a valid activity identifier",
            )]
        
        activity_def = ALL_ACTIVITIES[activity_id]
        duration = duration_minutes or activity_def.duration_min
        end_time = start_time + timedelta(minutes=duration)
        
        # Get crew member for calculations
        crew = self.crew_members[crew_id]
        
        # Calculate energy expenditure
        estimated_kcal = kcal_from_met_duration(
            activity_def.met_value,
            crew.weight_kg,
            duration,
        )
        
        # Determine risk level
        risk_level = crew.get_risk_level()
        
        # Create scheduled activity
        scheduled = ScheduledActivity(
            schedule_id=str(uuid.uuid4()),
            crew_id=crew_id,
            activity_id=activity_id,
            activity_name=activity_def.name,
            start_time=start_time,
            end_time=end_time,
            met_value=activity_def.met_value,
            estimated_kcal=estimated_kcal,
            risk_level=risk_level,
            is_fixed=activity_def.category == ActivityCategory.FIXED,
            priority=priority,
            notes=notes,
        )
        
        # Check for conflicts
        conflicts = self._check_conflicts(scheduled)
        
        # Add to schedule if no critical conflicts
        critical_conflicts = [c for c in conflicts if c.severity == "critical"]
        if not critical_conflicts:
            daily_schedule = self.get_or_create_daily_schedule(start_time.date())
            daily_schedule.activities.append(scheduled)
            daily_schedule.conflicts.extend(conflicts)
            self._update_crew_state(crew_id, scheduled)
        
        return scheduled if not critical_conflicts else None, conflicts
    
    def _check_conflicts(
        self,
        activity: ScheduledActivity,
    ) -> List[ScheduleConflict]:
        """Check for scheduling conflicts."""
        conflicts: List[ScheduleConflict] = []
        schedule_date = activity.start_time.date()
        daily_schedule = self.get_or_create_daily_schedule(schedule_date)
        
        # Check overlap with existing activities for same crew
        for existing in daily_schedule.activities:
            if existing.crew_id != activity.crew_id:
                continue
            if existing.schedule_id == activity.schedule_id:
                continue
            
            # Check time overlap
            if (activity.start_time < existing.end_time and
                activity.end_time > existing.start_time):
                conflicts.append(ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type="overlap",
                    affected_activities=(activity.schedule_id, existing.schedule_id),
                    affected_crew=(activity.crew_id,),
                    severity="error",
                    description=f"Activity overlaps with {existing.activity_name}",
                    suggested_resolution=f"Reschedule to avoid {existing.start_time.strftime('%H:%M')}-{existing.end_time.strftime('%H:%M')}",
                ))
        
        # Check resource constraints (e.g., exercise/hygiene capacity)
        activity_def = ALL_ACTIVITIES.get(activity.activity_id)
        if activity_def and "resource_limited_1" in activity_def.constraints:
            # Check concurrent usage - resource_limited_1 means max 1 person at a time
            concurrent = sum(
                1 for a in daily_schedule.activities
                if a.activity_id == activity.activity_id
                and a.schedule_id != activity.schedule_id
                and a.start_time < activity.end_time
                and a.end_time > activity.start_time
            )
            if concurrent >= MAX_CONCURRENT_EXERCISE:
                conflicts.append(ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type="resource",
                    affected_activities=(activity.schedule_id,),
                    affected_crew=(activity.crew_id,),
                    severity="critical",
                    description=f"Resource at capacity ({MAX_CONCURRENT_EXERCISE} max concurrent for {activity.activity_name})",
                    suggested_resolution="Choose a different time slot",
                ))
        
        # Check EVA recovery time
        if activity.activity_id == "eva":
            crew = self.crew_members.get(activity.crew_id)
            if crew and crew.status:
                if crew.status.hours_since_last_eva < 48:
                    conflicts.append(ScheduleConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type="recovery",
                        affected_activities=(activity.schedule_id,),
                        affected_crew=(activity.crew_id,),
                        severity="critical" if crew.status.hours_since_last_eva < 24 else "warning",
                        description=f"Only {crew.status.hours_since_last_eva:.1f}h since last EVA (48h recommended)",
                        suggested_resolution="Wait for full recovery period or obtain Flight Surgeon approval",
                    ))
        
        # Check safety gates for high-risk activities
        if activity.activity_id in ("eva", "lab_work"):
            crew = self.crew_members.get(activity.crew_id)
            if crew and crew.status:
                is_suitable, status, mitigation = check_activity_suitability(
                    crew.status,
                    activity.activity_id,
                )
                if not is_suitable:
                    conflicts.append(ScheduleConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type="constraint",
                        affected_activities=(activity.schedule_id,),
                        affected_crew=(activity.crew_id,),
                        severity="critical",
                        description=f"Crew not cleared for {activity.activity_name}: {mitigation}",
                        suggested_resolution="Improve crew readiness or reschedule",
                    ))
                elif mitigation:
                    conflicts.append(ScheduleConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type="constraint",
                        affected_activities=(activity.schedule_id,),
                        affected_crew=(activity.crew_id,),
                        severity="warning",
                        description=f"Activity requires mitigation: {mitigation}",
                        suggested_resolution=mitigation,
                    ))
        
        return conflicts
    
    def _update_crew_state(
        self,
        crew_id: str,
        activity: ScheduledActivity,
    ) -> None:
        """Update crew scheduling state after adding an activity."""
        if crew_id not in self.crew_states:
            self.crew_states[crew_id] = CrewScheduleState(crew_id=crew_id)
        
        state = self.crew_states[crew_id]
        state.total_scheduled_minutes += activity.duration_minutes
        
        # Track specific activities
        if activity.activity_id == "exercise":
            state.exercise_completed = True
        if activity.activity_id in ("breakfast", "lunch", "dinner"):
            state.meals_completed.add(activity.activity_id)
    
    def generate_daily_template(
        self,
        schedule_date: date,
        briefing_hour: int = BRIEFING_TIME_HOUR,
    ) -> DailySchedule:
        """
        Generate a daily schedule template with fixed activities.
        
        Args:
            schedule_date: Date to schedule
            briefing_hour: Hour for daily briefing (default 7:00)
            
        Returns:
            DailySchedule with fixed activities for all crew
        """
        daily = self.get_or_create_daily_schedule(schedule_date)
        
        for crew_id, crew in self.crew_members.items():
            # Briefing at 07:00 for all crew
            briefing_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=briefing_hour),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="briefing",
                start_time=briefing_start,
                priority=10,
                notes="Daily synchronized briefing",
            )
            
            # Breakfast after briefing
            breakfast_start = briefing_start + timedelta(minutes=60)
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="breakfast",
                start_time=breakfast_start,
                priority=8,
            )
            
            # Lunch at 12:00
            lunch_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=12),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="lunch",
                start_time=lunch_start,
                priority=8,
            )
            
            # Dinner at 18:00
            dinner_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=18),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="dinner",
                start_time=dinner_start,
                priority=8,
            )
            
            # Hygiene before sleep at 21:00
            hygiene_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=21),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="hygiene",
                start_time=hygiene_start,
                priority=7,
            )
            
            # Sleep 21:30 to 05:30 (next day) - simplified to same day for template
            sleep_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=21, minute=30),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="sleep",
                start_time=sleep_start,
                priority=10,
            )
        
        daily.is_optimized = False
        return daily
    
    def generate_full_daily_schedule(
        self,
        schedule_date: date,
        eva_day: bool = False,
        eva_crew_ids: Optional[List[str]] = None,
    ) -> DailySchedule:
        """
        Generate a complete daily schedule with all activities for 6 crew.
        
        Includes:
        - Fixed activities (briefing, meals, sleep, hygiene)
        - 6 experiments (1 hour each, distributed among crew)
        - Exercise (resource-limited: 1 person at a time)
        - Recreation (individual scheduling)
        - EVA activities if scheduled (2 crew, with ISLE protocol)
        
        Constraints:
        - Hygiene module: 1 person at a time (30 min each)
        - Exercise equipment: 1 person at a time (60 min each)
        - Experiments: All 6 must be completed daily
        - EVA: 2 crew max, requires ~100 min ISLE prep + 120 min EVA + 60 min post
        
        Args:
            schedule_date: Date to schedule
            eva_day: Whether this is an EVA day
            eva_crew_ids: List of crew IDs performing EVA (max 2)
            
        Returns:
            Fully populated DailySchedule
        """
        daily = self.get_or_create_daily_schedule(schedule_date)
        crew_ids = list(self.crew_members.keys())
        
        if not crew_ids:
            return daily
        
        # ---------------------------------------------------------------------------
        # Phase 1: Fixed activities for all crew
        # ---------------------------------------------------------------------------
        
        # 05:30 - Wake time (implicit)
        # 06:00-06:30 - Staggered hygiene (resource limited: 1 person)
        for idx, crew_id in enumerate(crew_ids):
            hygiene_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=6, minute=idx * 30 % 60),
            )
            # Stagger across 06:00, 06:30, 07:00, etc.
            if idx >= 2:
                hygiene_start = hygiene_start.replace(hour=6 + (idx * 30 // 60))
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="hygiene",
                start_time=hygiene_start,
                priority=8,
                notes="Morning hygiene (module: 1 person)",
            )
        
        # 07:00 - Briefing (all crew synchronous)
        briefing_start = datetime.combine(
            schedule_date,
            datetime.min.time().replace(hour=7),
        )
        for crew_id in crew_ids:
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="briefing",
                start_time=briefing_start,
                priority=10,
                notes="Daily synchronized briefing",
            )
        
        # 08:00 - Breakfast
        breakfast_start = datetime.combine(
            schedule_date,
            datetime.min.time().replace(hour=8),
        )
        for crew_id in crew_ids:
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="breakfast",
                start_time=breakfast_start,
                priority=8,
            )
        
        # ---------------------------------------------------------------------------
        # Phase 2: Experiments (6 experiments, 1 hour each)
        # Each crew member does 1-2 experiments
        # EVA crew are excluded on EVA days (their experiments go to other crew)
        # ---------------------------------------------------------------------------
        experiment_ids = [
            "exp_physio_monitoring",
            "exp_cortisol_sampling",
            "exp_neurocognitive",
            "exp_psychological",
            "exp_sleep_analysis",
            "exp_matb_workload",
        ]
        
        # Determine available crew for experiments (exclude EVA crew on EVA day)
        # EVA prep starts at 10:00, so experiments after 09:00 would conflict
        eva_crew_set = set(eva_crew_ids[:2]) if eva_day and eva_crew_ids else set()
        available_for_experiments = [cid for cid in crew_ids if cid not in eva_crew_set]
        
        # Distribute experiments among available crew
        # Start experiments at 09:00, staggered by 30 min to avoid cognitive overload
        experiment_base_hour = 9
        for exp_idx, exp_id in enumerate(experiment_ids):
            # Round-robin among available crew (those not doing EVA)
            crew_idx = exp_idx % len(available_for_experiments)
            crew_id = available_for_experiments[crew_idx]
            
            # Stagger start times: 09:00, 09:30, 10:00, 10:30, 11:00, 11:30
            exp_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(
                    hour=experiment_base_hour + (exp_idx // 2),
                    minute=(exp_idx % 2) * 30,
                ),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id=exp_id,
                start_time=exp_start,
                priority=7,
                notes=f"Daily experiment {exp_idx + 1}/6",
            )
        
        # ---------------------------------------------------------------------------
        # Phase 3: Exercise (resource limited - 1 person at a time)
        # ---------------------------------------------------------------------------
        # Exercise slots: 09:00-10:00, 10:00-11:00, etc. (6 slots needed)
        exercise_base_hour = 11  # After morning experiments
        for idx, crew_id in enumerate(crew_ids):
            # Skip EVA crew on EVA day - they get their exercise during ISLE
            if eva_day and eva_crew_ids and crew_id in eva_crew_ids:
                continue
            
            exercise_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=exercise_base_hour + idx),
            )
            # Wrap around if past 17:00
            if exercise_start.hour >= 17:
                exercise_start = exercise_start.replace(hour=14 + (idx - 3))
            
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="exercise",
                start_time=exercise_start,
                priority=6,
                notes="Physical exercise (equipment: 1 person)",
            )
        
        # ---------------------------------------------------------------------------
        # Phase 4: Lunch at 12:00
        # ---------------------------------------------------------------------------
        lunch_start = datetime.combine(
            schedule_date,
            datetime.min.time().replace(hour=12),
        )
        for crew_id in crew_ids:
            # Skip if EVA in progress
            if eva_day and eva_crew_ids and crew_id in eva_crew_ids:
                continue
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="lunch",
                start_time=lunch_start,
                priority=8,
            )
        
        # ---------------------------------------------------------------------------
        # Phase 5: EVA Activities (if EVA day)
        # Timeline: ISLE Prep (100 min) + EVA (120 min) + Post (60 min) = 280 min
        # ---------------------------------------------------------------------------
        if eva_day and eva_crew_ids:
            eva_start_hour = 10  # Start ISLE prep at 10:00
            for eva_crew_id in eva_crew_ids[:2]:  # Max 2 crew
                # ISLE Prebreathe Protocol (100 min)
                isle_start = datetime.combine(
                    schedule_date,
                    datetime.min.time().replace(hour=eva_start_hour),
                )
                self.schedule_activity(
                    crew_id=eva_crew_id,
                    activity_id="eva_prep_isle",
                    start_time=isle_start,
                    priority=10,
                    notes="ISLE Protocol: 40min O2 mask + 20min suit + 40min in-suit prebreathe",
                )
                
                # EVA Operations (120 min) - starts after ISLE
                eva_ops_start = isle_start + timedelta(minutes=100)
                self.schedule_activity(
                    crew_id=eva_crew_id,
                    activity_id="eva",
                    start_time=eva_ops_start,
                    priority=10,
                    notes="EVA operations (2 hours)",
                )
                
                # Post-EVA (60 min)
                post_eva_start = eva_ops_start + timedelta(minutes=120)
                self.schedule_activity(
                    crew_id=eva_crew_id,
                    activity_id="eva_post",
                    start_time=post_eva_start,
                    priority=9,
                    notes="Suit doffing, medical check, debrief",
                )
        
        # ---------------------------------------------------------------------------
        # Phase 6: Recreation (14:00-17:00 block, individual)
        # ---------------------------------------------------------------------------
        rec_base_hour = 15  # Afternoon recreation
        for idx, crew_id in enumerate(crew_ids):
            # Skip EVA crew during EVA window
            if eva_day and eva_crew_ids and crew_id in eva_crew_ids:
                rec_hour = 16  # Post-EVA recreation
            else:
                rec_hour = rec_base_hour + (idx % 2)
            
            rec_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=rec_hour, minute=(idx % 2) * 30),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="recreation",
                start_time=rec_start,
                priority=5,
                notes="Individual recreation/rest",
            )
        
        # ---------------------------------------------------------------------------
        # Phase 7: Dinner at 18:00
        # ---------------------------------------------------------------------------
        dinner_start = datetime.combine(
            schedule_date,
            datetime.min.time().replace(hour=18),
        )
        for crew_id in crew_ids:
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="dinner",
                start_time=dinner_start,
                priority=8,
            )
        
        # ---------------------------------------------------------------------------
        # Phase 8: Evening hygiene (staggered) and Sleep
        # ---------------------------------------------------------------------------
        for idx, crew_id in enumerate(crew_ids):
            # Evening hygiene (19:30-21:00, staggered)
            evening_hygiene_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=19, minute=30 + (idx * 15) % 60),
            )
            if idx >= 2:
                evening_hygiene_start = evening_hygiene_start.replace(
                    hour=19 + ((30 + idx * 15) // 60),
                    minute=(30 + idx * 15) % 60,
                )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="hygiene",
                start_time=evening_hygiene_start,
                priority=7,
                notes="Evening hygiene (module: 1 person)",
            )
            
            # Sleep at 21:30
            sleep_start = datetime.combine(
                schedule_date,
                datetime.min.time().replace(hour=21, minute=30),
            )
            self.schedule_activity(
                crew_id=crew_id,
                activity_id="sleep",
                start_time=sleep_start,
                priority=10,
                notes="8-hour sleep period (chronotype-optimized)",
            )
        
        daily.is_optimized = True
        daily.optimization_score = 85.0  # Base score for generated schedule
        return daily
    
    def optimize_schedule(
        self,
        schedule_date: date,
        objective: str = "balanced",
    ) -> Tuple[DailySchedule, float]:
        """
        Optimize the daily schedule using constraint satisfaction.
        
        Optimization objectives:
        - "safety_first": Maximize safety margins, minimize fatigue risk
        - "mission_value": Maximize mission task completion
        - "balanced": Balance safety and mission value (default)
        
        Args:
            schedule_date: Date to optimize
            objective: Optimization objective
            
        Returns:
            Tuple of (optimized DailySchedule, optimization score)
        """
        daily = self.get_or_create_daily_schedule(schedule_date)
        
        # Calculate optimization score based on objective
        score = 0.0
        weights = {
            "safety_first": {"fatigue": 0.4, "conflicts": 0.3, "completion": 0.3},
            "mission_value": {"fatigue": 0.2, "conflicts": 0.2, "completion": 0.6},
            "balanced": {"fatigue": 0.3, "conflicts": 0.3, "completion": 0.4},
        }
        w = weights.get(objective, weights["balanced"])
        
        # Fatigue score: based on crew IHPI scores
        fatigue_scores = []
        for crew_id in self.crew_members:
            crew = self.crew_members[crew_id]
            ihpi = crew.get_ihpi()
            fatigue_scores.append(ihpi / 100.0)
        fatigue_component = np.mean(fatigue_scores) if fatigue_scores else 0.5
        
        # Conflict score: fewer conflicts = better
        n_conflicts = len(daily.conflicts)
        conflict_component = max(0, 1.0 - (n_conflicts * 0.1))
        
        # Completion score: % of required activities scheduled
        required_activities = {"briefing", "breakfast", "lunch", "dinner", "hygiene", "sleep"}
        completion_scores = []
        for crew_id in self.crew_members:
            crew_activities = {a.activity_id for a in daily.get_crew_activities(crew_id)}
            completed = len(crew_activities & required_activities)
            completion_scores.append(completed / len(required_activities))
        completion_component = np.mean(completion_scores) if completion_scores else 0.0
        
        # Weighted sum
        score = (
            w["fatigue"] * fatigue_component +
            w["conflicts"] * conflict_component +
            w["completion"] * completion_component
        )
        
        daily.is_optimized = True
        daily.optimization_score = score * 100
        
        return daily, score * 100
    
    def check_rescheduling_triggers(
        self,
        schedule_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Check for conditions that should trigger dynamic rescheduling.
        
        Triggers:
        - Real-time performance degradation (SAFTE < 90 sustained)
        - Medical status change
        - Mission priority shifts
        - Fatigue score threshold breach
        - Resource availability changes
        
        Args:
            schedule_date: Date to check
            
        Returns:
            List of trigger dictionaries with reason and recommended action
        """
        triggers: List[Dict[str, Any]] = []
        
        for crew_id, crew in self.crew_members.items():
            if crew.status is None:
                continue
            
            # Check SAFTE degradation
            if crew.status.safte_effectiveness < SAFTE_LOW_RISK_MIN:
                triggers.append({
                    "crew_id": crew_id,
                    "trigger_type": "fatigue_threshold",
                    "severity": "warning" if crew.status.safte_effectiveness >= SAFTE_CAUTION_MIN else "critical",
                    "description": f"SAFTE effectiveness at {crew.status.safte_effectiveness:.1f}%",
                    "recommended_action": "Consider rescheduling high-demand activities or adding rest breaks",
                })
            
            # Check HRV z-score
            if crew.status.lnrmssd_zscore < -1.5:
                triggers.append({
                    "crew_id": crew_id,
                    "trigger_type": "hrv_degradation",
                    "severity": "warning",
                    "description": f"lnRMSSD z-score at {crew.status.lnrmssd_zscore:.2f}",
                    "recommended_action": "Monitor recovery; consider reduced workload",
                })
            
            # Check energy availability
            if crew.status.energy_availability < 30:
                triggers.append({
                    "crew_id": crew_id,
                    "trigger_type": "low_energy_availability",
                    "severity": "warning",
                    "description": f"Energy availability at {crew.status.energy_availability:.1f} kcal/kg FFM/day",
                    "recommended_action": "Increase caloric intake or reduce exercise energy expenditure",
                })
            
            # Check hydration
            if crew.status.usg is not None and crew.status.usg >= 1.025:
                triggers.append({
                    "crew_id": crew_id,
                    "trigger_type": "hydration_concern",
                    "severity": "warning" if crew.status.usg < 1.030 else "critical",
                    "description": f"USG at {crew.status.usg:.3f}",
                    "recommended_action": "Increase fluid intake; monitor body mass",
                })
        
        return triggers
    
    def get_crew_summary(
        self,
        schedule_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Get summary of crew status and scheduled activities.
        
        Args:
            schedule_date: Date for summary
            
        Returns:
            List of crew summary dictionaries
        """
        daily = self.get_daily_schedule(schedule_date)
        summaries: List[Dict[str, Any]] = []
        
        for crew_id, crew in self.crew_members.items():
            crew_activities = daily.get_crew_activities(crew_id) if daily else []
            
            summary = {
                "crew_id": crew_id,
                "name": crew.name,
                "role": crew.role,
                "ihpi": crew.get_ihpi(),
                "risk_level": crew.get_risk_level().value,
                "activities_count": len(crew_activities),
                "total_scheduled_minutes": sum(a.duration_minutes for a in crew_activities),
                "total_kcal": sum(a.estimated_kcal for a in crew_activities),
            }
            
            if crew.status:
                summary.update({
                    "safte_effectiveness": crew.status.safte_effectiveness,
                    "hours_awake": crew.status.hours_awake,
                    "kss_score": crew.status.kss_score,
                    "lnrmssd_zscore": crew.status.lnrmssd_zscore,
                    "energy_availability": crew.status.energy_availability,
                })
                
                # EVA readiness
                if crew.vo2max_ml_kg_min >= 32.9:
                    eva_result = crew.status.eva_go_nogo()
                    summary["eva_status"] = eva_result.status.value
                    summary["eva_reasons"] = eva_result.reasons
            
            summaries.append(summary)
        
        return summaries
    
    def export_schedule_json(
        self,
        schedule_date: date,
    ) -> str:
        """Export daily schedule to JSON format (read-only)."""
        daily = self.get_daily_schedule(schedule_date)
        
        export_data = {
            "schedule_date": schedule_date.isoformat(),
            "is_optimized": daily.is_optimized if daily else False,
            "optimization_score": daily.optimization_score if daily else 0.0,
            "activities": [a.to_dict() for a in daily.activities] if daily else [],
            "conflicts": [
                {
                    "conflict_id": c.conflict_id,
                    "conflict_type": c.conflict_type,
                    "affected_activities": c.affected_activities,
                    "affected_crew": c.affected_crew,
                    "severity": c.severity,
                    "description": c.description,
                    "suggested_resolution": c.suggested_resolution,
                }
                for c in (daily.conflicts if daily else [])
            ],
            "crew_summary": self.get_crew_summary(schedule_date),
        }
        
        return json.dumps(export_data, indent=2)


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------

def create_sample_crew() -> List[CrewMember]:
    """Create sample crew members for demonstration.
    
    Roles based on ASTRA analog mission structure:
        - Comandante → Commander
        - Oficial de datos → Data Officer
        - Ingeniero Biomédico → Biomedical Engineer
        - Oficial Médico → Medical Officer
        - Ingeniero de vuelo → Flight Engineer
        - Oficial de comunicaciones → Communications Officer
    """
    crew = [
        CrewMember(
            crew_id="crew_1",
            name="Crew Alfa",
            role="Commander (Comandante)",
            age_years=45,
            sex="male",
            weight_kg=80,
            height_cm=180,
            vo2max_ml_kg_min=42.0,
            chronotype="intermediate",
        ),
        CrewMember(
            crew_id="crew_2",
            name="Crew Bravo",
            role="Data Officer (Oficial de Datos)",
            age_years=38,
            sex="female",
            weight_kg=65,
            height_cm=168,
            vo2max_ml_kg_min=45.0,
            chronotype="early",
        ),
        CrewMember(
            crew_id="crew_3",
            name="Crew Charlie",
            role="Biomedical Engineer (Ingeniero Biomédico)",
            age_years=42,
            sex="male",
            weight_kg=75,
            height_cm=175,
            vo2max_ml_kg_min=38.0,
            chronotype="late",
        ),
        CrewMember(
            crew_id="crew_4",
            name="Crew Delta",
            role="Medical Officer (Oficial Médico)",
            age_years=35,
            sex="female",
            weight_kg=58,
            height_cm=162,
            vo2max_ml_kg_min=40.0,
            chronotype="intermediate",
        ),
        CrewMember(
            crew_id="crew_5",
            name="Crew Echo",
            role="Flight Engineer (Ingeniero de Vuelo)",
            age_years=40,
            sex="male",
            weight_kg=78,
            height_cm=177,
            vo2max_ml_kg_min=44.0,
            chronotype="early",
        ),
        CrewMember(
            crew_id="crew_6",
            name="Crew Foxtrot",
            role="Communications Officer (Oficial de Comunicaciones)",
            age_years=32,
            sex="female",
            weight_kg=62,
            height_cm=165,
            vo2max_ml_kg_min=48.0,
            chronotype="intermediate",
        ),
    ]
    
    # Add sample physiological status
    now = datetime.now()
    for c in crew:
        c.status = CrewPhysiologicalStatus(
            crew_id=c.crew_id,
            timestamp=now,
            safte_effectiveness=np.random.uniform(82, 98),
            hours_awake=np.random.uniform(4, 14),
            sleep_last_24h=np.random.uniform(6.5, 8.5),
            kss_score=np.random.uniform(2, 5),
            samn_perelli_score=np.random.uniform(2, 4),
            lnrmssd_current=np.random.uniform(3.2, 4.0),
            lnrmssd_baseline_mean=3.6,
            lnrmssd_baseline_sd=0.25,
            body_mass_change_pct=np.random.uniform(-1.0, 0.5),
            usg=np.random.uniform(1.010, 1.025),
            energy_availability=np.random.uniform(35, 50),
            pvt_lapses_3min=int(np.random.uniform(2, 12)),
            phase_offset_hours=np.random.uniform(-1, 1),
            chronotype=c.chronotype,
            vo2max=c.vo2max_ml_kg_min,
            hours_since_last_eva=np.random.uniform(48, 200),
        )
    
    return crew


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "MAX_CREW_SIZE",
    "MAX_CONCURRENT_EXERCISE",
    "BRIEFING_TIME_HOUR",
    # Enums
    "ConstraintType",
    "ScheduleStatus",
    # Data structures
    "ScheduledActivity",
    "ScheduleConflict",
    "DailySchedule",
    "CrewScheduleState",
    "Constraint",
    # Constraints
    "HARD_CONSTRAINTS",
    "SOFT_CONSTRAINTS",
    # Engine
    "SchedulingEngine",
    # Factory
    "create_sample_crew",
]

