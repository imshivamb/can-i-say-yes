from typing import Literal

DecisionOutcome = Literal["SAFE", "UNSAFE", "UNKNOWN"]

CommitmentStatus = Literal[
    "DRAFT",
    "ASSESSED",
    "APPROVED",
    "REJECTED",
    "COMMITTED",
    "MONITORING",
    "HUMAN_REVIEW",
    "REVISED",
    "CANCELLED",
    "FULFILLED",
    "FAILED",
]

CommitmentHealth = Literal[
    "ON_TRACK",
    "AT_RISK",
    "BLOCKED",
    "UNKNOWN",
    "FAILED",
    "FULFILLED",
]

EvidenceFreshness = Literal["current", "stale", "superseded"]
EvidenceReliability = Literal["confirmed", "stated", "rumored", "inferred"]
SourceType = Literal[
    "email",
    "document",
    "project_plan",
    "calendar",
    "capacity_ledger",
    "supplier_record",
    "commitment",
    "customer_asset",
    "domain_calculation",
]

ConflictCode = Literal[
    "CAPACITY_OVERALLOCATED",
    "EXISTING_COMMITMENT",
    "SUPPLIER_WINDOW",
    "MISSING_DEPENDENCY",
    "CALENDAR_UNAVAILABLE",
    "BUDGET_SHORTFALL",
    "SCHEDULE_IMPOSSIBLE",
    "EVIDENCE_CONFLICT",
]

Skill = Literal["design", "development", "video", "copy", "account", "project"]
WorkItemKind = Literal[
    "social_creative",
    "landing_page",
    "video",
    "copy",
    "photography",
    "other",
]
AlternativeKind = Literal[
    "later_date",
    "reduced_scope",
    "extra_resource",
    "alternate_supplier",
    "higher_cost",
    "partial_delivery",
]
DecisionStatus = Literal["OPEN", "APPROVED", "REJECTED", "CHOSEN_OTHER", "EXPIRED"]
EventType = Literal[
    "supplier_update",
    "customer_scope_change",
    "calendar_change",
    "capacity_change",
    "asset_received",
    "asset_delayed",
    "message_received",
]
Authorization = Literal["allow", "deny", "require_human"]
Priority = Literal["low", "normal", "high", "critical"]
ProjectStatus = Literal["active", "planned", "done"]
DocumentKind = Literal["proposal", "contract", "sop", "pricing", "supplier", "plan"]
CalendarKind = Literal["ooo", "focus", "meeting", "hold"]
RequestSource = Literal["typed", "email", "demo"]
Severity = Literal["low", "medium", "high"]
AuditResult = Literal["success", "error", "denied"]
