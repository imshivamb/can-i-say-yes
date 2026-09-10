from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from domain.enums import (
    AlternativeKind,
    AuditResult,
    Authorization,
    CalendarKind,
    CommitmentHealth,
    CommitmentStatus,
    ConflictCode,
    DecisionOutcome,
    DecisionStatus,
    DocumentKind,
    EventType,
    EvidenceFreshness,
    EvidenceReliability,
    Priority,
    ProjectStatus,
    RequestSource,
    Severity,
    Skill,
    SourceType,
    WorkItemKind,
)


class WorkItem(BaseModel):
    id: str
    kind: WorkItemKind
    name: str
    quantity: int = 1
    estimated_hours: float
    skill: Skill
    depends_on: list[str] = Field(default_factory=list)
    required_asset_ids: list[str] = Field(default_factory=list)


class Money(BaseModel):
    currency: Literal["INR"] = "INR"
    amount: int


class TimeWindow(BaseModel):
    start: datetime
    end: datetime


class ParsedRequest(BaseModel):
    id: str
    customer_name: str
    customer_id: str | None = None
    raw_text: str
    scope_summary: str
    work_items: list[WorkItem]
    deadline: date
    budget: Money | None = None
    constraints: list[str] = Field(default_factory=list)
    source: RequestSource = "typed"
    received_at: datetime


class Evidence(BaseModel):
    id: str
    source_type: SourceType
    source_name: str
    source_reference: str
    timestamp: datetime
    as_of: datetime
    content: str
    freshness: EvidenceFreshness
    reliability: EvidenceReliability
    related_commitment_ids: list[str] = Field(default_factory=list)


class Reason(BaseModel):
    id: str
    title: str
    detail: str
    severity: Severity
    evidence_ids: list[str]
    conflict_code: ConflictCode | None = None


class Constraint(BaseModel):
    id: str
    code: ConflictCode
    description: str
    evidence_ids: list[str]
    blocking: bool


class Alternative(BaseModel):
    id: str
    kind: AlternativeKind
    title: str
    summary: str
    extra_cost: Money
    new_deadline: date | None = None
    scope_delta: str | None = None
    feasible: bool
    forecast_end: date | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    recommended: bool = False


class FeasibilityAssessment(BaseModel):
    id: str
    request_id: str
    decision: DecisionOutcome
    confidence: float
    reasons: list[Reason]
    evidence: list[Evidence]
    constraints: list[Constraint]
    alternatives: list[Alternative]
    required_human_decision: bool
    forecast_end: date | None = None
    utilization_by_skill: dict[str, float] = Field(default_factory=dict)
    created_at: datetime


class Commitment(BaseModel):
    id: str
    request_id: str
    assessment_id: str
    customer_id: str
    customer_name: str
    title: str
    scope_summary: str
    work_items: list[WorkItem]
    original_deadline: date
    committed_deadline: date
    current_forecast: date | None = None
    budget: Money | None = None
    extra_cost: Money = Field(default_factory=lambda: Money(amount=0))
    status: CommitmentStatus
    health: CommitmentHealth | None = None
    approved_alternative_id: str | None = None
    monitor_event_types: list[EventType] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DecisionOption(BaseModel):
    id: str
    title: str
    summary: str
    extra_cost: Money
    recommended: bool = False


class HumanDecision(BaseModel):
    id: str
    commitment_id: str | None = None
    request_id: str | None = None
    assessment_id: str | None = None
    reason: str
    options: list[DecisionOption]
    recommended_option_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: datetime | None = None
    status: DecisionStatus = "OPEN"
    chosen_option_id: str | None = None
    actor: str | None = None


class Person(BaseModel):
    id: str
    name: str
    role: str
    skills: list[Skill]
    weekly_hours: float
    unavailable: list[TimeWindow] = Field(default_factory=list)


class Client(BaseModel):
    id: str
    name: str
    priority: Priority


class Project(BaseModel):
    id: str
    client_id: str
    name: str
    status: ProjectStatus
    deadline: date
    priority: Priority
    assigned_person_ids: list[str]
    work_items: list[WorkItem]
    booked_hours_by_person: dict[str, float]
    dependencies: list[str] = Field(default_factory=list)
    budget: Money | None = None


class Supplier(BaseModel):
    id: str
    name: str
    kind: str
    available_from: date | None = None
    available_until: date | None = None
    daily_rate: Money | None = None
    notes: str = ""


class EmailMessage(BaseModel):
    id: str
    sent_at: datetime
    from_addr: str
    to_addr: list[str]
    subject: str
    body: str
    labels: list[str] = Field(default_factory=list)
    related_client_id: str | None = None


class Document(BaseModel):
    id: str
    title: str
    kind: DocumentKind
    created_at: datetime
    body: str
    related_client_id: str | None = None


class CalendarEvent(BaseModel):
    id: str
    person_id: str
    title: str
    start: datetime
    end: datetime
    kind: CalendarKind


class CustomerAsset(BaseModel):
    id: str
    client_id: str
    name: str
    required: bool
    received: bool
    promised_on: date | None = None
    received_on: date | None = None


class WorldEvent(BaseModel):
    id: str
    type: EventType
    occurs_at: datetime
    source_reference: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    consumed: bool = False
    related_commitment_ids: list[str] = Field(default_factory=list)


class SimulationClock(BaseModel):
    now: datetime
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"


class OutboxMessage(BaseModel):
    id: str
    commitment_id: str
    to: str
    subject: str
    body: str
    decision_id: str
    sent_at: datetime


class ActivityItem(BaseModel):
    id: str
    timestamp: datetime
    text: str
    commitment_id: str | None = None


class AuditRecord(BaseModel):
    id: str
    timestamp: datetime
    actor: str
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_status: AuditResult
    authorization: Authorization | None = None
    commitment_id: str | None = None
    request_id: str | None = None


class AgentHandoff(BaseModel):
    """Typed contract between the Investigator and Monitor agents."""

    id: str
    source_agent: Literal["investigator", "monitor"]
    target_agent: Literal["investigator", "monitor"]
    kind: Literal["feasibility", "reassessment"]
    request_id: str
    commitment_id: str | None = None
    event_id: str | None = None
    assessment_id: str | None = None
    created_at: datetime
    status: Literal["requested", "completed", "failed"] = "requested"


class ItemForecast(BaseModel):
    work_item_id: str
    start: date | None
    end: date | None
    blocked_by: list[str] = Field(default_factory=list)


class ScheduleResult(BaseModel):
    feasible_for_deadline: bool
    forecast_end: date | None
    slack_days: int
    critical_path: list[str]
    utilization_by_skill: dict[str, float]
    item_forecasts: list[ItemForecast]
    working_days_used: int = 0
