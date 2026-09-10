from __future__ import annotations

from domain.capacity import remaining_hours_for_skill, utilization_for_skill
from domain.dependencies import missing_assets
from domain.enums import ConflictCode
from domain.ids import new_id
from domain.models import Constraint, Evidence, ParsedRequest, ScheduleResult, WorkItem
from domain.world import World

PRIORITY_RANK = {"low": 0, "normal": 1, "high": 2, "critical": 3}


def _hours_by_skill(work_items: list[WorkItem]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in work_items:
        totals[item.skill] = totals.get(item.skill, 0.0) + item.estimated_hours
    return totals


def detect_conflicts(
    world: World,
    request: ParsedRequest,
    schedule: ScheduleResult,
    evidence: list[Evidence],
) -> list[Constraint]:
    constraints: list[Constraint] = []
    ev_by_ref = {e.source_reference: e.id for e in evidence}

    def ev(*refs: str) -> list[str]:
        ids = [ev_by_ref[r] for r in refs if r in ev_by_ref]
        return ids or [e.id for e in evidence[:1]]

    needed = _hours_by_skill(request.work_items)
    for skill, hours in needed.items():
        remaining = remaining_hours_for_skill(world, skill)
        if hours > remaining:
            constraints.append(
                Constraint(
                    id=new_id("con"),
                    code="CAPACITY_OVERALLOCATED",
                    description=(
                        f"{skill} needs {hours:.1f}h; {remaining:.1f}h remain "
                        f"({utilization_for_skill(world, skill):.0%} allocated)"
                    ),
                    evidence_ids=ev("capacity_ledger", "doc_capacity_0912"),
                    blocking=True,
                )
            )

    request_priority = 1
    if request.customer_id:
        try:
            request_priority = PRIORITY_RANK[world.client(request.customer_id).priority]
        except StopIteration:
            request_priority = 1

    for commitment in world.commitments:
        if commitment.status not in {"COMMITTED", "MONITORING", "HUMAN_REVIEW", "REVISED"}:
            continue
        if commitment.committed_deadline > request.deadline:
            continue
        try:
            client = world.client(commitment.customer_id)
        except StopIteration:
            continue
        if PRIORITY_RANK[client.priority] < request_priority:
            continue
        if remaining_hours_for_skill(world, "design") < needed.get("design", 0):
            constraints.append(
                Constraint(
                    id=new_id("con"),
                    code="EXISTING_COMMITMENT",
                    description=(
                        f"{commitment.customer_name} commitment due "
                        f"{commitment.committed_deadline.isoformat()} consumes "
                        "the remaining buffer"
                    ),
                    evidence_ids=ev(commitment.id, "prj_bloom_festive", "eml_bloom_priority"),
                    blocking=True,
                )
            )
            break

    for asset in missing_assets(world, request.work_items):
        constraints.append(
            Constraint(
                id=new_id("con"),
                code="MISSING_DEPENDENCY",
                description=f"{asset.name} has not arrived (promised {asset.promised_on})",
                evidence_ids=ev(asset.id, "eml_acme_photos", "doc_video_sop"),
                blocking=True,
            )
        )

    for item in request.work_items:
        if item.skill != "video":
            continue
        suppliers = world.suppliers_of_kind("video_editor")
        if not suppliers:
            continue
        earliest = min((s.available_from for s in suppliers if s.available_from), default=None)
        if earliest and schedule.forecast_end and schedule.forecast_end > request.deadline:
            constraints.append(
                Constraint(
                    id=new_id("con"),
                    code="SUPPLIER_WINDOW",
                    description=(
                        f"Video editor availability from {earliest.isoformat()} "
                        "creates a schedule conflict with the requested date"
                    ),
                    evidence_ids=ev("sup_frame_grain", "eml_editor_window"),
                    blocking=True,
                )
            )
            break

    if schedule.forecast_end and schedule.forecast_end > request.deadline:
        already = {c.code for c in constraints}
        if "SCHEDULE_IMPOSSIBLE" not in already:
            constraints.append(
                Constraint(
                    id=new_id("con"),
                    code="SCHEDULE_IMPOSSIBLE",
                    description=(
                        f"Critical path ends {schedule.forecast_end.isoformat()}, "
                        f"after {request.deadline.isoformat()}"
                    ),
                    evidence_ids=ev("domain_schedule"),
                    blocking=True,
                )
            )

    # Deduplicate by code — one row per conflict type for the assessment card.
    unique: list[Constraint] = []
    seen: set[ConflictCode] = set()
    for constraint in constraints:
        if constraint.code in seen:
            continue
        seen.add(constraint.code)
        unique.append(constraint)
    return unique
