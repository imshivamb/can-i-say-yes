from __future__ import annotations

from domain.alternatives import find_alternatives
from domain.clock import DEMO_START
from domain.conflicts import detect_conflicts
from domain.enums import ConflictCode, DecisionOutcome
from domain.evidence import gather_assessment_evidence
from domain.ids import new_id
from domain.models import FeasibilityAssessment, ParsedRequest, Reason
from domain.scheduler import calculate_schedule
from domain.world import World

MATERIAL_CODES: tuple[ConflictCode, ...] = (
    "CAPACITY_OVERALLOCATED",
    "EXISTING_COMMITMENT",
    "MISSING_DEPENDENCY",
    "SUPPLIER_WINDOW",
    "SCHEDULE_IMPOSSIBLE",
    "EVIDENCE_CONFLICT",
    "BUDGET_SHORTFALL",
)

_TITLE = {
    "CAPACITY_OVERALLOCATED": "Capacity conflict",
    "EXISTING_COMMITMENT": "Existing customer commitment",
    "MISSING_DEPENDENCY": "Missing customer assets",
    "SUPPLIER_WINDOW": "Supplier availability",
    "SCHEDULE_IMPOSSIBLE": "Schedule miss",
    "CALENDAR_UNAVAILABLE": "Key person unavailable",
    "BUDGET_SHORTFALL": "Budget shortfall",
    "EVIDENCE_CONFLICT": "Conflicting evidence",
}


def _decision(codes: set[str], slack_days: int, forecast_ok: bool) -> DecisionOutcome:
    blocking = codes & set(MATERIAL_CODES)
    if blocking:
        return "UNSAFE"
    if not forecast_ok or slack_days < 1:
        return "UNSAFE"
    return "SAFE"


def assess_feasibility(world: World, request: ParsedRequest) -> FeasibilityAssessment:
    schedule = calculate_schedule(world, request)
    evidence = gather_assessment_evidence(world, request, schedule)
    constraints = detect_conflicts(world, request, schedule, evidence)
    alternatives = []
    codes = {c.code for c in constraints}
    decision = _decision(codes, schedule.slack_days, schedule.feasible_for_deadline)
    if decision != "SAFE":
        alternatives = find_alternatives(world, request, schedule)

    reasons = [
        Reason(
            id=new_id("rsn"),
            title=_TITLE.get(constraint.code, constraint.code),
            detail=constraint.description,
            severity="high" if constraint.blocking else "medium",
            evidence_ids=constraint.evidence_ids,
            conflict_code=constraint.code,
        )
        for constraint in constraints
    ]

    confidence = 0.91 if decision == "UNSAFE" and len(constraints) >= 3 else 0.7
    if decision == "SAFE":
        confidence = 0.8

    return FeasibilityAssessment(
        id=new_id("asm"),
        request_id=request.id,
        decision=decision,
        confidence=confidence,
        reasons=reasons,
        evidence=evidence,
        constraints=constraints,
        alternatives=alternatives,
        required_human_decision=True,
        forecast_end=schedule.forecast_end,
        utilization_by_skill=schedule.utilization_by_skill,
        created_at=world.clock.now if world.clock.now else DEMO_START,
    )
