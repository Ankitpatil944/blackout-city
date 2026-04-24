from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

try:
    from openenv.core.env_server.types import Action as OpenEnvAction
    from openenv.core.env_server.types import Observation as OpenEnvObservation
    from openenv.core.env_server.types import State as OpenEnvState
except ImportError:  # pragma: no cover
    class OpenEnvAction(BaseModel):
        model_config = ConfigDict(extra="forbid")

    class OpenEnvObservation(BaseModel):
        reward: float = 0.0
        done: bool = False
        model_config = ConfigDict(extra="forbid")

    class OpenEnvState(BaseModel):
        model_config = ConfigDict(extra="forbid")


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AssetHealth(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DAMAGED = "damaged"
    UNSTABLE = "unstable"


class CriticalNodeType(str, Enum):
    HOSPITAL = "hospital"
    TELECOM = "telecom"
    WATER = "water"
    EMERGENCY = "emergency"


class ActionType(str, Enum):
    START_GENERATOR = "start_generator"
    ENERGIZE_SUBSTATION = "energize_substation"
    INSPECT_LINE = "inspect_line"
    CLOSE_LINE = "close_line"
    OPEN_LINE = "open_line"
    RESTORE_CRITICAL_NODE = "restore_critical_node"
    RESTORE_ZONE = "restore_zone"
    SHED_ZONE = "shed_zone"
    SYNC_ISLANDS = "sync_islands"
    ACTIVATE_BATTERY_SUPPORT = "activate_battery_support"
    PUBLISH_STATUS = "publish_status"


class GeneratorState(BaseModel):
    id: str
    bus: str
    online: bool = False
    blackstart_capable: bool = False
    capacity_mw: int = Field(ge=0)
    current_output_mw: int = Field(default=0, ge=0)
    startup_steps_remaining: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class SubstationState(BaseModel):
    id: str
    energized: bool = False
    island_id: str
    load_mw: int = Field(default=0, ge=0)
    damaged: bool = False

    model_config = ConfigDict(extra="forbid")


class LineState(BaseModel):
    id: str
    from_bus: str
    to_bus: str
    capacity_mw: int = Field(ge=1)
    closed: bool = False
    tripped: bool = False
    damaged: bool = False
    inspected: bool = False
    current_flow_mw: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class CriticalNodeState(BaseModel):
    id: str
    type: CriticalNodeType
    feeder_bus: str
    demand_mw: int = Field(ge=1)
    powered: bool = False
    backup_minutes_remaining: int = Field(default=0, ge=0)
    population_impact: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class ZonePriority(str, Enum):
    RESIDENTIAL = "residential"
    INDUSTRIAL = "industrial"
    CORRIDOR = "corridor"


class ZoneState(BaseModel):
    id: str
    feeder_bus: str
    priority: ZonePriority
    demand_mw: int = Field(ge=1)
    restored_pct: int = Field(default=0, ge=0, le=100)

    model_config = ConfigDict(extra="forbid")


class StatusUpdate(BaseModel):
    summary: str = Field(..., min_length=12, max_length=240)
    critical_services: str = Field(..., min_length=12, max_length=240)
    next_action: str = Field(..., min_length=12, max_length=240)
    owner: str = Field(..., min_length=3, max_length=80)

    model_config = ConfigDict(extra="forbid")


class CommandRole(str, Enum):
    GRID_OPERATOR = "grid_operator"
    EMERGENCY_COORDINATOR = "emergency_coordinator"
    PUBLIC_INFORMATION_OFFICER = "public_information_officer"
    RESOURCE_DISPATCHER = "resource_dispatcher"


class CoordinationMessage(BaseModel):
    role: CommandRole
    recipient: str
    summary: str = Field(..., min_length=8, max_length=220)
    urgency: str = Field(..., min_length=3, max_length=24)
    is_conflict: bool = Field(default=False)

    model_config = ConfigDict(extra="forbid")


class RewardBreakdown(BaseModel):
    critical_restore_reward: float = 0.0
    load_restore_reward: float = 0.0
    stability_reward: float = 0.0
    inspection_reward: float = 0.0
    communication_reward: float = 0.0
    arbitration_reward: float = 0.0
    action_penalty: float = 0.0
    catastrophe_penalty: float = 0.0
    current_score: float = 0.01

    model_config = ConfigDict(extra="forbid")


class CityTaskSpec(BaseModel):
    task_id: str
    difficulty: DifficultyLevel
    description: str
    max_steps: int

    model_config = ConfigDict(extra="forbid")


# ── Instruction-following constraints ────────────────────────────────────────

class ConstraintType(str, Enum):
    FORBIDDEN_TARGET = "forbidden_target"    # Never act on a specific asset
    CONDITIONAL_LIMIT = "conditional_limit"  # Keep zone below X MW until condition
    PRIORITY_ORDER = "priority_order"        # Must restore A before B


class Constraint(BaseModel):
    id: str
    text: str = Field(..., min_length=10, max_length=320)
    constraint_type: ConstraintType
    active: bool = True
    violated: bool = False
    # FORBIDDEN_TARGET fields
    forbidden_action_type: Optional[ActionType] = None
    forbidden_target_id: Optional[str] = None
    # CONDITIONAL_LIMIT fields
    limit_target_id: Optional[str] = None
    limit_mw: Optional[int] = Field(default=None, ge=0)
    condition_field: Optional[str] = None      # e.g. "reserve_margin_mw"
    condition_threshold: Optional[float] = None
    # PRIORITY_ORDER fields
    must_restore_first: Optional[str] = None   # critical_node id
    before_restoring: Optional[str] = None     # zone id or critical_node id

    model_config = ConfigDict(extra="forbid")


# ── Live news feed ────────────────────────────────────────────────────────────

class NewsEvent(BaseModel):
    id: str
    trigger_step: int = Field(ge=1)
    headline: str = Field(..., min_length=8, max_length=160)
    detail: str = Field(..., min_length=8, max_length=320)
    impact_level: str = Field(default="info", min_length=3, max_length=12)  # info | warning | critical
    revealed: bool = False
    # Optional world-state side-effects on reveal
    reveals_damage_on_line: Optional[str] = None
    reduces_backup_node: Optional[str] = None
    reduces_backup_by: Optional[int] = Field(default=None, ge=0)
    activates_constraint_id: Optional[str] = None
    public_trust_delta: float = Field(default=0.0, ge=-1.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


# ── Multi-dimensional rubric score ────────────────────────────────────────────

class RubricScore(BaseModel):
    safety: float = Field(default=0.0, ge=0.0, le=1.0)               # Constraint compliance + no unsafe actions
    triage_quality: float = Field(default=0.0, ge=0.0, le=1.0)       # Hospital-first ordering, critical services
    communication_clarity: float = Field(default=0.0, ge=0.0, le=1.0) # Status update relevance
    resource_efficiency: float = Field(default=0.0, ge=0.0, le=1.0)  # Step efficiency, crew use
    overall: float = Field(default=0.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class Scenario(BaseModel):
    incident_id: str
    title: str
    task: CityTaskSpec
    objective: str
    generators: list[GeneratorState]
    substations: list[SubstationState]
    lines: list[LineState]
    critical_nodes: list[CriticalNodeState]
    zones: list[ZoneState]
    initial_frequency_hz: float = 60.0
    initial_available_generation_mw: int = 0
    initial_served_load_mw: int = 0
    hidden_damaged_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    solution_actions: list[dict[str, str | int]] = Field(default_factory=list)
    status_keywords: list[str] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    news_events: list[NewsEvent] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class BlackstartAction(OpenEnvAction):
    action_type: ActionType
    target_id: Optional[str] = None
    requested_mw: Optional[int] = Field(default=None, ge=0)
    rationale: Optional[str] = Field(default=None, max_length=240)
    status_update: Optional[StatusUpdate] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_payload(self) -> "BlackstartAction":
        needs_target = {
            ActionType.START_GENERATOR,
            ActionType.ENERGIZE_SUBSTATION,
            ActionType.INSPECT_LINE,
            ActionType.CLOSE_LINE,
            ActionType.OPEN_LINE,
            ActionType.RESTORE_CRITICAL_NODE,
            ActionType.RESTORE_ZONE,
            ActionType.SHED_ZONE,
            ActionType.SYNC_ISLANDS,
            ActionType.ACTIVATE_BATTERY_SUPPORT,
        }
        if self.action_type in needs_target and not self.target_id:
            raise ValueError("target_id is required for this action type")
        if self.action_type in {ActionType.RESTORE_ZONE, ActionType.SHED_ZONE} and self.requested_mw is None:
            raise ValueError("requested_mw is required for zone load actions")
        if self.action_type == ActionType.PUBLISH_STATUS and self.status_update is None:
            raise ValueError("status_update is required for publish_status")
        return self


class ResourceState(BaseModel):
    repair_crews_total: int = Field(default=0, ge=0)
    repair_crews_available: int = Field(default=0, ge=0)
    mobile_battery_units_total: int = Field(default=0, ge=0)
    mobile_battery_units_available: int = Field(default=0, ge=0)
    telecom_support_units_total: int = Field(default=0, ge=0)
    telecom_support_units_available: int = Field(default=0, ge=0)
    dispatch_pressure: float = Field(default=0.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class CommandRecommendation(BaseModel):
    role: CommandRole
    objective: str = Field(..., min_length=8, max_length=120)
    rationale: str = Field(..., min_length=12, max_length=260)
    urgency: str = Field(..., min_length=3, max_length=24)
    proposed_action: Optional[BlackstartAction] = None

    model_config = ConfigDict(extra="forbid")


class CommandCenterState(BaseModel):
    public_trust: float = Field(default=0.5, ge=0.0, le=1.0)
    coordination_score: float = Field(default=0.5, ge=0.0, le=1.0)
    command_phase: str = Field(default="blackstart", min_length=4, max_length=64)
    unresolved_services: list[str] = Field(default_factory=list)
    resource_state: ResourceState = Field(default_factory=ResourceState)
    role_recommendations: list[CommandRecommendation] = Field(default_factory=list)
    coordination_messages: list[CoordinationMessage] = Field(default_factory=list)
    rl_proposed_action: Optional[BlackstartAction] = None

    model_config = ConfigDict(extra="forbid")


class BlackstartObservation(OpenEnvObservation):
    incident_id: str
    task_id: str
    title: str
    objective: str
    difficulty: DifficultyLevel
    step: int
    steps_remaining: int
    available_generation_mw: int
    served_load_mw: int
    reserve_margin_mw: int
    frequency_hz: float
    unstable_islands: int
    generators: list[GeneratorState]
    substations: list[SubstationState]
    lines: list[LineState]
    critical_nodes: list[CriticalNodeState]
    zones: list[ZoneState]
    warnings: list[str]
    allowed_actions: list[ActionType]
    last_action_result: Optional[str] = None
    last_action_error: Optional[str] = None
    reward_breakdown: RewardBreakdown
    command_center: CommandCenterState = Field(default_factory=CommandCenterState)
    active_constraints: list[Constraint] = Field(default_factory=list)
    news_feed: list[NewsEvent] = Field(default_factory=list)
    rubric: RubricScore = Field(default_factory=RubricScore)

    model_config = ConfigDict(extra="forbid")


class BlackstartState(OpenEnvState):
    incident_id: str
    task_id: str
    title: str
    difficulty: DifficultyLevel
    objective: str
    step_count: int
    max_steps: int
    done: bool
    generators: list[GeneratorState]
    substations: list[SubstationState]
    lines: list[LineState]
    critical_nodes: list[CriticalNodeState]
    zones: list[ZoneState]
    available_generation_mw: int
    served_load_mw: int
    reserve_margin_mw: int
    frequency_hz: float
    unstable_islands: int
    cumulative_reward: float = 0.0
    cumulative_penalty: float = 0.0
    catastrophe_triggered: bool = False
    hospital_failures: int = 0
    failed_critical_nodes: list[str] = Field(default_factory=list)
    last_action_result: Optional[str] = None
    last_action_error: Optional[str] = None
    published_status: Optional[StatusUpdate] = None
    action_history: list[str] = Field(default_factory=list)
    score: float = 0.01
    reward_breakdown: RewardBreakdown = Field(default_factory=RewardBreakdown)
    command_center: CommandCenterState = Field(default_factory=CommandCenterState)
    active_constraints: list[Constraint] = Field(default_factory=list)
    news_feed: list[NewsEvent] = Field(default_factory=list)
    constraint_violations: int = 0
    rubric: RubricScore = Field(default_factory=RubricScore)
    infeasible_emergency_streak: int = 0
    emergency_priority_active: bool = False

    model_config = ConfigDict(extra="forbid")
