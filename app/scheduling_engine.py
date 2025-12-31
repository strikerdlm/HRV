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
    WorkloadMetrics,
    compute_workload_balance,
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
    
    # Spatial planning (NASA Mission Control standard)
    location: Optional[str] = None  # e.g., "Lab Module", "Exercise Area", "Crew Quarters"
    
    # Procedure integration (NASA Mission Control standard)
    procedure_id: Optional[str] = None  # Link to procedure/checklist
    checklist_items: List[str] = field(default_factory=list)  # Checklist item IDs
    
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
            "location": self.location,
            "procedure_id": self.procedure_id,
            "checklist_items": self.checklist_items,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ScheduledActivity:
        """Reconstruct ScheduledActivity from dictionary."""
        from scheduling_core import RiskLevel
        
        return cls(
            schedule_id=data["schedule_id"],
            crew_id=data["crew_id"],
            activity_id=data["activity_id"],
            activity_name=data["activity_name"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            status=ScheduleStatus(data.get("status", "scheduled")),
            met_value=data.get("met_value", 1.0),
            estimated_kcal=data.get("estimated_kcal", 0.0),
            risk_level=RiskLevel(data.get("risk_level", "low")),
            is_fixed=data.get("is_fixed", False),
            priority=data.get("priority", 5),
            location=data.get("location"),
            procedure_id=data.get("procedure_id"),
            checklist_items=data.get("checklist_items", []),
            notes=data.get("notes", ""),
        )


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
class ActivityGroup:
    """A group of related activities that can be moved together (NASA Playbook standard)."""
    group_id: str
    name: str
    activity_ids: List[str] = field(default_factory=list)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "group_id": self.group_id,
            "name": self.name,
            "activity_ids": self.activity_ids,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ScheduleVersion:
    """A version snapshot of a schedule for rollback functionality (NASA Playbook standard)."""
    version_id: str
    schedule_date: date
    activities: List[ScheduledActivity] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    created_by: str = "system"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version_id": self.version_id,
            "schedule_date": self.schedule_date.isoformat(),
            "activities": [a.to_dict() for a in self.activities],
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
        }


@dataclass
class DailySchedule:
    """A day's schedule for all crew members."""
    schedule_date: date
    activities: List[ScheduledActivity] = field(default_factory=list)
    conflicts: List[ScheduleConflict] = field(default_factory=list)
    is_optimized: bool = False
    optimization_score: float = 0.0
    version_history: List[ScheduleVersion] = field(default_factory=list)  # For rollback
    
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
        self.activity_groups: Dict[str, ActivityGroup] = {}  # Activity grouping (NASA Playbook)
        self.schedule_changes: List[Dict[str, Any]] = []  # Real-time change tracking
        
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
        location: Optional[str] = None,
        procedure_id: Optional[str] = None,
        checklist_items: Optional[List[str]] = None,
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
            location=location,
            procedure_id=procedure_id,
            checklist_items=checklist_items or [],
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
            # Track change for real-time updates
            self._track_schedule_change("activity_added", scheduled.schedule_id, {
                "crew_id": crew_id,
                "activity_id": activity_id,
                "start_time": start_time.isoformat(),
            })
        
        return scheduled if not critical_conflicts else None, conflicts
    
    def _track_schedule_change(
        self,
        change_type: str,
        schedule_id: str,
        details: Dict[str, Any],
    ) -> None:
        """Track schedule changes for real-time updates (NASA Mission Control standard).
        
        Args:
            change_type: Type of change ("activity_added", "activity_updated", "activity_deleted", "schedule_rolled_back")
            schedule_id: Schedule instance ID (UUID), not activity definition ID
            details: Additional change details (may include activity_id for activity definition)
        """
        change = {
            "change_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "change_type": change_type,
            "schedule_id": schedule_id,  # Schedule instance UUID
            "details": details,  # May contain activity_id (activity definition) and other metadata
        }
        self.schedule_changes.append(change)
        # Keep only last 100 changes to prevent memory bloat
        if len(self.schedule_changes) > 100:
            self.schedule_changes = self.schedule_changes[-100:]
    
    def get_recent_changes(
        self,
        since: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent schedule changes for real-time updates (NASA Mission Control standard)."""
        if since:
            return [
                c for c in self.schedule_changes
                if datetime.fromisoformat(c["timestamp"]) >= since
            ][-limit:]
        return self.schedule_changes[-limit:]
    
    def link_procedure_to_activity(
        self,
        schedule_id: str,
        procedure_id: str,
        checklist_items: Optional[List[str]] = None,
    ) -> bool:
        """Link a procedure/checklist to a scheduled activity (NASA Mission Control standard)."""
        # Find activity across all schedules
        for daily in self.schedules.values():
            activity = next((a for a in daily.activities if a.schedule_id == schedule_id), None)
            if activity:
                activity.procedure_id = procedure_id
                if checklist_items:
                    activity.checklist_items = checklist_items
                self._track_schedule_change("activity_updated", schedule_id, {
                    "procedure_id": procedure_id,
                    "checklist_items": checklist_items or [],
                })
                return True
        return False
    
    def _check_conflicts(
        self,
        activity: ScheduledActivity,
    ) -> List[ScheduleConflict]:
        """Check for scheduling conflicts."""
        conflicts: List[ScheduleConflict] = []
        schedule_date = activity.start_time.date()
        daily_schedule = self.get_or_create_daily_schedule(schedule_date)
        
        # Check spatial conflicts (NASA Mission Control standard)
        if activity.location:
            for existing in daily_schedule.activities:
                if existing.schedule_id == activity.schedule_id:
                    continue
                # Check if same location at same time (spatial conflict)
                if (existing.location and 
                    existing.location == activity.location and
                    activity.start_time < existing.end_time and
                    activity.end_time > existing.start_time):
                    conflicts.append(ScheduleConflict(
                        conflict_id=str(uuid.uuid4()),
                        conflict_type="spatial",
                        affected_activities=(activity.schedule_id, existing.schedule_id),
                        affected_crew=(activity.crew_id, existing.crew_id),
                        severity="warning",
                        description=f"Spatial conflict: Multiple crew in '{activity.location}' at same time",
                        suggested_resolution=f"Reschedule one activity or use different location",
                    ))
        
        # Check overlap with existing activities for same crew
        for existing in daily_schedule.activities:
            if existing.crew_id != activity.crew_id:
                continue
            if existing.schedule_id == activity.schedule_id:
                continue
            
            # Check time overlap with priority-based resolution (NASA Mission Control standard)
            if (activity.start_time < existing.end_time and
                activity.end_time > existing.start_time):
                # Priority-based conflict resolution
                if activity.priority > existing.priority:
                    # New activity has higher priority - suggest moving existing
                    resolution = f"Move lower-priority activity '{existing.activity_name}' (priority {existing.priority}) to accommodate '{activity.activity_name}' (priority {activity.priority})"
                    severity = "warning"
                elif activity.priority < existing.priority:
                    # Existing activity has higher priority - suggest moving new
                    resolution = f"Reschedule '{activity.activity_name}' (priority {activity.priority}) - conflicts with higher-priority '{existing.activity_name}' (priority {existing.priority})"
                    severity = "error"
                else:
                    # Same priority - suggest negotiation
                    resolution = f"Priority conflict: Both activities have priority {activity.priority}. Reschedule one or adjust priorities."
                    severity = "warning"
                
                conflicts.append(ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type="overlap",
                    affected_activities=(activity.schedule_id, existing.schedule_id),
                    affected_crew=(activity.crew_id,),
                    severity=severity,
                    description=f"Activity overlaps with {existing.activity_name} (Priority: {existing.priority} vs {activity.priority})",
                    suggested_resolution=resolution,
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
    
    def create_schedule_snapshot(self, schedule_date: date, description: str = "", created_by: str = "system") -> Optional[ScheduleVersion]:
        """Create a version snapshot of the current schedule for rollback (NASA Playbook standard).
        
        Args:
            schedule_date: Date of the schedule to snapshot
            description: Optional description of the snapshot
            created_by: User/system identifier
            
        Returns:
            ScheduleVersion if successful, None if schedule doesn't exist
        """
        daily = self.get_daily_schedule(schedule_date)
        if not daily:
            return None
        
        # Create snapshot with copy of activities
        snapshot = ScheduleVersion(
            version_id=str(uuid.uuid4()),
            schedule_date=schedule_date,
            activities=[ScheduledActivity.from_dict(a.to_dict()) for a in daily.activities],  # Deep copy
            created_at=datetime.now(),
            created_by=created_by,
            description=description,
        )
        
        # Add to version history
        daily.version_history.append(snapshot)
        
        # Keep only last 10 versions to prevent memory bloat
        if len(daily.version_history) > 10:
            daily.version_history = daily.version_history[-10:]
        
        return snapshot
    
    def rollback_schedule(self, schedule_date: date, version_id: Optional[str] = None) -> bool:
        """Rollback schedule to a previous version (NASA Playbook standard).
        
        Args:
            schedule_date: Date of the schedule to rollback
            version_id: Specific version to rollback to (uses latest if None)
            
        Returns:
            True if rollback successful, False otherwise
        """
        daily = self.get_daily_schedule(schedule_date)
        if not daily or not daily.version_history:
            return False
        
        # Find version to rollback to
        if version_id:
            target_version = next((v for v in daily.version_history if v.version_id == version_id), None)
        else:
            # Use second-to-last version (last is current)
            if len(daily.version_history) < 2:
                return False
            target_version = daily.version_history[-2]
        
        if not target_version:
            return False
        
        # Create snapshot of current state before rollback
        self.create_schedule_snapshot(schedule_date, description="Pre-rollback snapshot", created_by="system")
        
        # Restore activities from version
        daily.activities = [ScheduledActivity.from_dict(a.to_dict()) for a in target_version.activities]
        
        return True
    
    def create_activity_group(self, name: str, activity_ids: List[str], description: str = "") -> ActivityGroup:
        """Create an activity group for batch operations (NASA Playbook standard).
        
        Args:
            name: Group name (e.g., "Morning Routine", "EVA Prep")
            activity_ids: List of schedule_ids to include in group
            description: Optional description
            
        Returns:
            Created ActivityGroup
        """
        group = ActivityGroup(
            group_id=str(uuid.uuid4()),
            name=name,
            activity_ids=activity_ids,
            description=description,
            created_at=datetime.now(),
        )
        self.activity_groups[group.group_id] = group
        return group
    
    def get_activity_group(self, group_id: str) -> Optional[ActivityGroup]:
        """Get an activity group by ID."""
        return self.activity_groups.get(group_id)
    
    def move_activity_group(self, group_id: str, time_offset_minutes: int, schedule_date: date) -> Tuple[bool, List[ScheduleConflict]]:
        """Move an entire activity group by time offset (NASA Playbook standard).
        
        Args:
            group_id: Activity group ID
            time_offset_minutes: Minutes to shift (positive = later, negative = earlier)
            schedule_date: Date of the schedule
            
        Returns:
            Tuple of (success, list of conflicts)
        """
        group = self.get_activity_group(group_id)
        if not group:
            return False, []
        
        daily = self.get_or_create_daily_schedule(schedule_date)
        all_conflicts: List[ScheduleConflict] = []
        
        # Find and move all activities in group
        for activity_id in group.activity_ids:
            activity = next((a for a in daily.activities if a.schedule_id == activity_id), None)
            if not activity:
                continue
            
            # Skip fixed activities
            if activity.is_fixed:
                all_conflicts.append(ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type="constraint",
                    affected_activities=(activity.schedule_id,),
                    affected_crew=(activity.crew_id,),
                    severity="warning",
                    description=f"Cannot move fixed activity: {activity.activity_name}",
                    suggested_resolution="Fixed activities cannot be moved",
                ))
                continue
            
            # Move activity
            new_start = activity.start_time + timedelta(minutes=time_offset_minutes)
            new_end = activity.end_time + timedelta(minutes=time_offset_minutes)
            
            # Check for conflicts
            conflicts = self._check_time_conflicts(schedule_date, activity.crew_id, new_start, new_end, activity.schedule_id)
            if conflicts:
                all_conflicts.extend(conflicts)
                continue
            
            # Apply move
            activity.start_time = new_start
            activity.end_time = new_end
        
        return len(all_conflicts) == 0, all_conflicts
    
    def _check_time_conflicts(self, schedule_date: date, crew_id: str, start_time: datetime, end_time: datetime, exclude_activity_id: Optional[str] = None) -> List[ScheduleConflict]:
        """Check for time conflicts with existing activities."""
        daily = self.get_daily_schedule(schedule_date)
        if not daily:
            return []
        
        conflicts: List[ScheduleConflict] = []
        
        for activity in daily.activities:
            if activity.schedule_id == exclude_activity_id:
                continue
            if activity.crew_id != crew_id:
                continue
            
            # Check for overlap
            if not (end_time <= activity.start_time or start_time >= activity.end_time):
                conflicts.append(ScheduleConflict(
                    conflict_id=str(uuid.uuid4()),
                    conflict_type="overlap",
                    affected_activities=(activity.schedule_id,),
                    affected_crew=(crew_id,),
                    severity="error",
                    description=f"Time conflict with {activity.activity_name}",
                    suggested_resolution="Reschedule one of the conflicting activities",
                ))
        
        return conflicts
    
    def suggest_optimal_times(
        self,
        crew_id: str,
        activity_id: str,
        schedule_date: date,
        duration_minutes: int,
        preferred_start: Optional[datetime] = None,
    ) -> List[Tuple[datetime, float]]:
        """
        Suggest optimal activity times based on circadian rhythm (NASA Mission Control standard).
        
        Args:
            crew_id: Crew member ID
            activity_id: Activity to schedule
            schedule_date: Target date
            duration_minutes: Activity duration
            preferred_start: Preferred start time (optional)
            
        Returns:
            List of (start_time, score) tuples sorted by score (highest first)
            Score indicates circadian alignment (0-1, higher = better)
        """
        import math
        from scheduling_core import ALL_ACTIVITIES
        
        crew = self.crew_members.get(crew_id)
        if not crew:
            return []
        
        activity_def = ALL_ACTIVITIES.get(activity_id)
        if not activity_def:
            return []
        
        # Get chronotype offset (convert string to hours)
        chronotype_map = {
            "early": -2.0,
            "intermediate": 0.0,
            "late": 2.0,
        }
        chronotype_offset = chronotype_map.get(crew.chronotype, 0.0)
        
        # Circadian nadir at ~4 AM (adjusted for chronotype)
        nadir_hour = 4.0 + chronotype_offset
        circadian_period = 24.0
        circadian_amplitude = 15.0  # 15% modulation
        
        suggestions: List[Tuple[datetime, float]] = []
        
        # Generate suggestions for each hour of the day
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                start_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=hour, minute=minute))
                end_time = start_time + timedelta(minutes=duration_minutes)
                
                # Skip if extends past midnight
                if end_time.date() > schedule_date:
                    continue
                
                # Check for conflicts
                conflicts = self._check_time_conflicts(schedule_date, crew_id, start_time, end_time)
                if conflicts:
                    continue
                
                # Calculate circadian score
                hour_of_day = hour + minute / 60.0
                phase = 2 * math.pi * ((hour_of_day - nadir_hour) / circadian_period)
                circadian_factor = 1.0 - (circadian_amplitude / 100.0) * (1 - math.cos(phase)) / 2
                
                # Activity-specific adjustments
                # High cognitive tasks: prefer morning (circadian peak)
                # Physical tasks: prefer afternoon (body temperature peak)
                # Low cognitive tasks: flexible
                if activity_def.cognitive_load == "high":
                    # Peak performance typically 2-4 hours after wake (~10 AM for early, ~12 PM for intermediate, ~2 PM for late)
                    optimal_hour = 10.0 + chronotype_offset
                    hour_diff = abs(hour_of_day - optimal_hour)
                    if hour_diff > 12:
                        hour_diff = 24 - hour_diff
                    cognitive_bonus = max(0, 1.0 - hour_diff / 6.0)  # Bonus within 6 hours
                    score = circadian_factor * 0.7 + cognitive_bonus * 0.3
                elif activity_def.cognitive_load == "moderate":
                    score = circadian_factor
                else:  # low cognitive load
                    # Physical tasks benefit from afternoon (body temp peak ~2-4 PM)
                    if activity_def.met_value > 3.0:
                        optimal_hour = 14.0 + chronotype_offset
                        hour_diff = abs(hour_of_day - optimal_hour)
                        if hour_diff > 12:
                            hour_diff = 24 - hour_diff
                        physical_bonus = max(0, 1.0 - hour_diff / 4.0)  # Bonus within 4 hours
                        score = circadian_factor * 0.6 + physical_bonus * 0.4
                    else:
                        score = circadian_factor
                
                # Prefer times closer to preferred_start if provided
                if preferred_start:
                    time_diff_hours = abs((start_time - preferred_start).total_seconds() / 3600)
                    if time_diff_hours > 12:
                        time_diff_hours = 24 - time_diff_hours
                    preference_bonus = max(0, 1.0 - time_diff_hours / 6.0)
                    score = score * 0.8 + preference_bonus * 0.2
                
                suggestions.append((start_time, score))
        
        # Sort by score (highest first) and return top 10
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:10]
    
    def suggest_workload_redistribution(
        self,
        schedule_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Suggest workload redistribution to balance crew workload (NASA Mission Control standard).
        
        Args:
            schedule_date: Date to analyze
            
        Returns:
            List of redistribution suggestions with crew_id, activity_id, suggested_time, reason
        """
        daily = self.get_daily_schedule(schedule_date)
        if not daily or not daily.activities:
            return []
        
        # Calculate workload for each crew member
        crew_workloads: Dict[str, WorkloadMetrics] = {}
        crew_activities: Dict[str, List[ScheduledActivity]] = {}
        
        for activity in daily.activities:
            if activity.crew_id not in crew_activities:
                crew_activities[activity.crew_id] = []
            crew_activities[activity.crew_id].append(activity)
        
        for crew_id, activities in crew_activities.items():
            crew = self.crew_members.get(crew_id)
            if not crew:
                continue
            workload = compute_workload_balance(activities, crew.weight_kg)
            workload.crew_id = crew_id
            crew_workloads[crew_id] = workload
        
        if len(crew_workloads) < 2:
            return []  # Need at least 2 crew members for redistribution
        
        # Find crew with highest and lowest workload
        sorted_crew = sorted(crew_workloads.items(), key=lambda x: x[1].total_work_minutes, reverse=True)
        max_crew_id, max_workload = sorted_crew[0]
        min_crew_id, min_workload = sorted_crew[-1]
        
        # Calculate workload difference
        workload_diff = max_workload.total_work_minutes - min_workload.total_work_minutes
        
        # Only suggest if difference is significant (>60 minutes)
        if workload_diff < 60:
            return []
        
        suggestions: List[Dict[str, Any]] = []
        
        # Find activities from high-workload crew that could be moved to low-workload crew
        max_crew_activities = crew_activities[max_crew_id]
        for activity in sorted(max_crew_activities, key=lambda a: a.duration_minutes, reverse=True):
            # Skip fixed activities
            if activity.is_fixed:
                continue
            
            # Skip if activity requires specific crew (e.g., EVA for specific role)
            activity_def = ALL_ACTIVITIES.get(activity.activity_id)
            if activity_def and "crew_specific" in activity_def.constraints:
                continue
            
            # Check if activity can be moved to low-workload crew
            # (In real implementation, would check crew roles, qualifications, etc.)
            suggestions.append({
                "from_crew_id": max_crew_id,
                "to_crew_id": min_crew_id,
                "activity_id": activity.activity_id,
                "activity_name": activity.activity_name,
                "schedule_id": activity.schedule_id,
                "current_time": activity.start_time,
                "workload_reduction": activity.duration_minutes,
                "reason": f"Redistribute {activity.duration_minutes} min from {max_crew_id} (high workload) to {min_crew_id} (low workload)",
            })
            
            # Limit to top 5 suggestions
            if len(suggestions) >= 5:
                break
        
        return suggestions
    
    def check_all_constraints(
        self,
        schedule_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Check all constraints for a schedule and return violations (NASA Mission Control standard).
        
        Args:
            schedule_date: Date to check
            
        Returns:
            List of constraint violations with details
        """
        daily = self.get_daily_schedule(schedule_date)
        if not daily or not daily.activities:
            return []
        
        violations: List[Dict[str, Any]] = []
        
        # Check hard constraints
        for constraint in HARD_CONSTRAINTS:
            if constraint.constraint_id == "briefing_sync":
                # All crew must have briefing at same time
                briefing_times = set()
                for activity in daily.activities:
                    if activity.activity_id == "briefing":
                        briefing_times.add(activity.start_time)
                
                if len(briefing_times) > 1:
                    violations.append({
                        "constraint_id": constraint.constraint_id,
                        "constraint_type": "hard",
                        "severity": "error",
                        "description": "Briefing times not synchronized across crew",
                        "affected_activities": [a.schedule_id for a in daily.activities if a.activity_id == "briefing"],
                        "suggested_resolution": "Synchronize all briefing times to same hour",
                    })
            
            elif constraint.constraint_id == "sleep_block":
                # Sleep must be continuous 8-hour block
                for crew_id in self.crew_members.keys():
                    sleep_activities = [a for a in daily.activities if a.crew_id == crew_id and a.activity_id == "sleep"]
                    if sleep_activities:
                        total_sleep = sum(a.duration_minutes for a in sleep_activities)
                        if total_sleep < 480:  # Less than 8 hours
                            violations.append({
                                "constraint_id": constraint.constraint_id,
                                "constraint_type": "hard",
                                "severity": "error",
                                "description": f"Crew {crew_id}: Sleep duration < 8 hours ({total_sleep} min)",
                                "affected_activities": [a.schedule_id for a in sleep_activities],
                                "suggested_resolution": "Ensure continuous 8-hour sleep block",
                            })
            
            elif constraint.constraint_id == "exercise_capacity":
                # Max 2 crew exercising concurrently
                exercise_activities = [a for a in daily.activities if a.activity_id == "exercise"]
                # Check for concurrent exercise periods
                for i, activity1 in enumerate(exercise_activities):
                    concurrent_count = 1  # Count activity1 itself
                    overlapping_activities = [activity1.schedule_id]
                    
                    for activity2 in exercise_activities[i+1:]:
                        # Check if activities overlap in time
                        if (activity1.start_time < activity2.end_time and
                            activity2.start_time < activity1.end_time):
                            concurrent_count += 1
                            overlapping_activities.append(activity2.schedule_id)
                    
                    if concurrent_count > MAX_CONCURRENT_EXERCISE:
                        crew_names = []
                        for schedule_id in overlapping_activities:
                            activity = next((a for a in daily.activities if a.schedule_id == schedule_id), None)
                            if activity:
                                crew = self.crew_members.get(activity.crew_id)
                                crew_names.append(crew.name if crew else activity.crew_id)
                        violations.append({
                            "constraint_id": constraint.constraint_id,
                            "constraint_type": "hard",
                            "severity": "error",
                            "description": f"Exercise capacity exceeded: {concurrent_count} crew exercising concurrently (max {MAX_CONCURRENT_EXERCISE})",
                            "affected_activities": overlapping_activities,
                            "suggested_resolution": f"Reschedule exercise for: {', '.join(crew_names)}",
                        })
                        break  # Only report once per violation
            
            elif constraint.constraint_id == "medical_clearance":
                # EVA requires medical clearance (GO/NO-GO check)
                eva_activities = [a for a in daily.activities if a.activity_id == "eva"]
                for eva_activity in eva_activities:
                    crew = self.crew_members.get(eva_activity.crew_id)
                    if crew and crew.status:
                        eva_result = crew.status.eva_go_nogo()
                        if not eva_result.all_gates_passed or eva_result.status != GONOGOStatus.GO:
                            violations.append({
                                "constraint_id": constraint.constraint_id,
                                "constraint_type": "hard",
                                "severity": "error",
                                "description": f"Crew {crew.name}: EVA medical clearance failed - {eva_result.status.value}",
                                "affected_activities": [eva_activity.schedule_id],
                                "suggested_resolution": f"Medical clearance required. Status: {eva_result.status.value}. Reasons: {', '.join(eva_result.reasons[:3])}",
                            })
                    else:
                        # No status data - assume clearance required
                        violations.append({
                            "constraint_id": constraint.constraint_id,
                            "constraint_type": "hard",
                            "severity": "error",
                            "description": f"Crew {eva_activity.crew_id}: EVA scheduled but no medical status available",
                            "affected_activities": [eva_activity.schedule_id],
                            "suggested_resolution": "Obtain medical clearance before scheduling EVA",
                        })
            
            elif constraint.constraint_id == "eva_recovery":
                # Minimum 48h between EVAs for same crew
                eva_activities = [a for a in daily.activities if a.activity_id == "eva"]
                # Check all schedules (not just current day) for previous EVAs
                for eva_activity in eva_activities:
                    crew_id = eva_activity.crew_id
                    eva_start = eva_activity.start_time
                    
                    # Check previous EVAs in all schedules
                    for schedule_date_check, schedule_check in self.schedules.items():
                        if schedule_date_check >= schedule_date:
                            continue  # Only check past schedules
                        
                        for past_activity in schedule_check.activities:
                            if (past_activity.crew_id == crew_id and
                                past_activity.activity_id == "eva"):
                                hours_since_last_eva = (eva_start - past_activity.end_time).total_seconds() / 3600
                                if hours_since_last_eva < 48:
                                    crew = self.crew_members.get(crew_id)
                                    crew_name = crew.name if crew else crew_id
                                    violations.append({
                                        "constraint_id": constraint.constraint_id,
                                        "constraint_type": "hard",
                                        "severity": "error",
                                        "description": f"Crew {crew_name}: EVA scheduled {hours_since_last_eva:.1f}h after previous EVA (minimum 48h required)",
                                        "affected_activities": [eva_activity.schedule_id],
                                        "suggested_resolution": f"Reschedule EVA to allow at least 48h recovery period",
                                    })
                                    break
            
            elif constraint.constraint_id == "safety_gates":
                # All safety gates must pass for high-risk activities
                high_risk_activities = [a for a in daily.activities if a.risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH)]
                for activity in high_risk_activities:
                    if activity.activity_id == "eva":
                        # Use EVA GO/NO-GO check
                        crew = self.crew_members.get(activity.crew_id)
                        if crew and crew.status:
                            eva_result = crew.status.eva_go_nogo()
                            if not eva_result.all_gates_passed:
                                violations.append({
                                    "constraint_id": constraint.constraint_id,
                                    "constraint_type": "hard",
                                    "severity": "error",
                                    "description": f"Crew {crew.name}: Safety gates failed for {activity.activity_name}",
                                    "affected_activities": [activity.schedule_id],
                                    "suggested_resolution": f"All safety gates must pass. Failed gates: {', '.join(eva_result.reasons[:3])}",
                                })
                    else:
                        # For other high-risk activities, check IHPI threshold
                        crew = self.crew_members.get(activity.crew_id)
                        if crew:
                            ihpi = crew.get_ihpi()
                            if ihpi < 75:  # IHPI threshold for high-risk activities
                                violations.append({
                                    "constraint_id": constraint.constraint_id,
                                    "constraint_type": "hard",
                                    "severity": "error",
                                    "description": f"Crew {crew.name}: IHPI {ihpi:.0f} below threshold (75) for {activity.activity_name}",
                                    "affected_activities": [activity.schedule_id],
                                    "suggested_resolution": "Improve crew readiness or reschedule activity",
                                })
        
        # Check soft constraints (workload, recovery, etc.)
        from scheduling_core import compute_workload_balance
        
        for crew_id, crew in self.crew_members.items():
            crew_activities = [a for a in daily.activities if a.crew_id == crew_id]
            if not crew_activities:
                continue
            
            workload = compute_workload_balance(crew_activities, crew.weight_kg)
            
            # Check work-rest ratio
            if workload.work_rest_ratio > 2.5:
                violations.append({
                    "constraint_id": "work_rest_ratio",
                    "constraint_type": "soft",
                    "severity": "warning",
                    "description": f"Crew {crew.name}: Work-rest ratio too high ({workload.work_rest_ratio:.2f})",
                    "affected_activities": [a.schedule_id for a in crew_activities],
                    "suggested_resolution": "Add more rest periods or reduce work duration",
                })
            
            # Check recovery score
            if workload.recovery_score < 70:
                violations.append({
                    "constraint_id": "recovery_score",
                    "constraint_type": "soft",
                    "severity": "warning",
                    "description": f"Crew {crew.name}: Low recovery score ({workload.recovery_score:.0f}%)",
                    "affected_activities": [a.schedule_id for a in crew_activities],
                    "suggested_resolution": "Reduce high-intensity activities or increase rest",
                })
            
            # Check total work hours
            work_hours = workload.total_work_minutes / 60
            if work_hours > 10:
                violations.append({
                    "constraint_id": "max_work_hours",
                    "constraint_type": "soft",
                    "severity": "warning",
                    "description": f"Crew {crew.name}: Work hours exceed 10h ({work_hours:.1f}h)",
                    "affected_activities": [a.schedule_id for a in crew_activities],
                    "suggested_resolution": "Redistribute workload or reduce scheduled activities",
                })
        
        return violations
    
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
    "ActivityGroup",
    "ScheduleVersion",
    # Constraints
    "HARD_CONSTRAINTS",
    "SOFT_CONSTRAINTS",
    # Engine
    "SchedulingEngine",
    # Factory
    "create_sample_crew",
]

