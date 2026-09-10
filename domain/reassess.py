from __future__ import annotations

from datetime import date
from typing import Never

from domain.alternatives import BACKUP_EDITOR_COST
from domain.clock import add_working_days
from domain.conflicts import detect_conflicts
from domain.enums import CommitmentHealth, DecisionOutcome
from domain.escalation import should_escalate
from domain.evidence import gather_assessment_evidence
from domain.ids import new_id
from domain.models import (
    Alternative,
    Commitment,
    FeasibilityAssessment,
    Money,
    ParsedRequest,
    Reason,
)
from domain.scheduler import SKILL_TO_SUPPLIER, _supplier_for_item, calculate_schedule
from domain.state_machine import transition_commitment
from domain.world import World

# Remaining critical-path duration for a committed campaign once work is unblocked.
# Editor start Saturday 20 September + 3 working days → Wednesday 23 September.
REMAINING_VIDEO_WORKING_DAYS = 3


def forecast_commitment(world: World, commitment: Commitment) -> date:
    """Re-forecast remaining committed work. Does not re-staff the whole request from zero."""
    today = world.clock.now.date()
    start = today
    items = [item for item in commitment.work_items if item.skill in SKILL_TO_SUPPLIER]
    if not items:
        return commitment.current_forecast or commitment.committed_deadline
    for item in items:
        supplier = _supplier_for_item(world, item)
        supplier_from = supplier.available_from if supplier else None
        if supplier_from and supplier_from > start:
            start = supplier_from
        for asset_id in item.required_asset_ids:
            asset = world.asset(asset_id)
            if asset.received:
                continue
            if asset.promised_on and asset.promised_on > today:
                start = max(start, asset.promised_on)
    return add_working_days(start, REMAINING_VIDEO_WORKING_DAYS)


def _assert_never(value: Never) -> Never:
    raise ValueError(f"unhandled health: {value}")


def health_for_forecast(forecast: date, committed_deadline: date) -> CommitmentHealth:
    if forecast > committed_deadline:
        return "AT_RISK"
    return "ON_TRACK"


def _decision_for_health(health: CommitmentHealth) -> DecisionOutcome:
    match health:
        case "ON_TRACK" | "FULFILLED":
            return "SAFE"
        case "AT_RISK" | "BLOCKED" | "FAILED":
            return "UNSAFE"
        case "UNKNOWN":
            return "UNKNOWN"
        case _ as unreachable:
            return _assert_never(unreachable)


def find_recovery_alternatives(
    world: World,
    commitment: Commitment,
    forecast: date,
) -> list[Alternative]:
    backup = next((item for item in world.suppliers if item.id == "sup_cutoff"), None)
    extra = backup.daily_rate.amount if backup and backup.daily_rate else BACKUP_EDITOR_COST
    video_qty = sum(item.quantity for item in commitment.work_items if item.kind == "video") or 3
    reduced = max(1, video_qty - 1)
    return [
        Alternative(
            id="alt_backup",
            kind="extra_resource",
            title="Use backup editor",
            summary=(
                "Bring in Cutoff Edit so the committed date can hold after the "
                "Frame & Grain delay."
            ),
            extra_cost=Money(amount=extra),
            new_deadline=commitment.committed_deadline,
            feasible=True,
            forecast_end=commitment.committed_deadline,
            recommended=True,
        ),
        Alternative(
            id="alt_slip",
            kind="later_date",
            title=f"Deliver Sept {forecast.day}",
            summary="Keep full scope and accept the slipped forecast. No extra cost.",
            extra_cost=Money(amount=0),
            new_deadline=forecast,
            feasible=True,
            forecast_end=forecast,
            recommended=False,
        ),
        Alternative(
            id="alt_scope",
            kind="reduced_scope",
            title=f"Reduce to {reduced} videos by Sept {commitment.committed_deadline.day}",
            summary="Cut one video to protect the committed date without extra spend.",
            extra_cost=Money(amount=0),
            new_deadline=commitment.committed_deadline,
            scope_delta=f"Deliver {reduced} videos instead of {video_qty}",
            feasible=True,
            forecast_end=commitment.committed_deadline,
            recommended=False,
        ),
    ]


def assess_commitment(
    world: World,
    commitment: Commitment,
    request: ParsedRequest,
) -> FeasibilityAssessment:
    view = request.model_copy(update={"deadline": commitment.committed_deadline})
    schedule = calculate_schedule(world, view)
    forecast = forecast_commitment(world, commitment)
    health = health_for_forecast(forecast, commitment.committed_deadline)
    evidence = gather_assessment_evidence(world, view, schedule)
    constraints = detect_conflicts(world, view, schedule, evidence)
    alternatives = (
        find_recovery_alternatives(world, commitment, forecast) if health != "ON_TRACK" else []
    )
    decision = _decision_for_health(health)
    required = should_escalate(
        health=health,
        assessment_decision=decision,
        recovery_changes_terms=bool(alternatives),
    )
    reasons = [
        Reason(
            id=new_id("rsn"),
            title="Supplier delay" if constraint.code == "SUPPLIER_WINDOW" else constraint.code,
            detail=constraint.description,
            severity="high" if constraint.blocking else "medium",
            evidence_ids=constraint.evidence_ids,
            conflict_code=constraint.code,
        )
        for constraint in constraints
    ]
    has_schedule_miss = any(item.conflict_code == "SCHEDULE_IMPOSSIBLE" for item in reasons)
    if health == "AT_RISK" and not has_schedule_miss:
        schedule_ids = [item.id for item in evidence if item.source_reference == "domain_schedule"]
        reasons.insert(
            0,
            Reason(
                id=new_id("rsn"),
                title="Commitment at risk",
                detail=(
                    f"Forecast {forecast.isoformat()} misses committed "
                    f"{commitment.committed_deadline.isoformat()}"
                ),
                severity="high",
                evidence_ids=schedule_ids,
                conflict_code="SCHEDULE_IMPOSSIBLE",
            ),
        )
    return FeasibilityAssessment(
        id=new_id("asm"),
        request_id=request.id,
        decision=decision,
        confidence=0.88 if health == "AT_RISK" else 0.8,
        reasons=reasons,
        evidence=evidence,
        constraints=constraints,
        alternatives=alternatives,
        required_human_decision=required,
        forecast_end=forecast,
        utilization_by_skill=schedule.utilization_by_skill,
        created_at=world.clock.now,
    )


def apply_reassessment(
    world: World,
    commitment: Commitment,
    assessment: FeasibilityAssessment,
) -> Commitment:
    forecast = assessment.forecast_end or forecast_commitment(world, commitment)
    health = health_for_forecast(forecast, commitment.committed_deadline)
    updates: dict[str, object] = {
        "current_forecast": forecast,
        "health": health,
        "updated_at": world.clock.now,
    }
    if health in {"AT_RISK", "BLOCKED", "FAILED"} and commitment.status == "MONITORING":
        updates["status"] = transition_commitment(commitment.status, "HUMAN_REVIEW")
    updated = commitment.model_copy(update=updates)
    for index, item in enumerate(world.commitments):
        if item.id == commitment.id:
            world.commitments[index] = updated
            break
    return updated
