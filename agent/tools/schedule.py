from __future__ import annotations

from typing import Any

from strands import tool

from agent.session import current_session
from agent.tools.common import dump, fail, ok, parse_date, safe_tool
from domain.alternatives import find_alternatives as domain_find_alternatives
from domain.conflicts import detect_conflicts
from domain.evidence import gather_assessment_evidence
from domain.models import ParsedRequest, ScheduleResult, WorkItem
from domain.scheduler import calculate_schedule as domain_calculate_schedule


def _request_from_session(request_id: str) -> ParsedRequest | None:
    return current_session().requests.get(request_id)


def _upsert_request(
    request_id: str,
    work_items: list[dict[str, Any]] | None,
    deadline: str | None,
) -> ParsedRequest | None:
    session = current_session()
    existing = session.requests.get(request_id)
    if existing is None and not work_items:
        return None
    if existing is None:
        deadline_d = parse_date(deadline)
        if deadline_d is None:
            return None
        request = ParsedRequest(
            id=request_id,
            customer_name="Unknown",
            raw_text="",
            scope_summary="",
            work_items=[WorkItem.model_validate(item) for item in work_items or []],
            deadline=deadline_d,
            received_at=session.world.clock.now,
        )
        return session.put_request(request)
    updates: dict[str, Any] = {}
    if work_items:
        updates["work_items"] = [WorkItem.model_validate(item) for item in work_items]
    if deadline:
        parsed = parse_date(deadline)
        if parsed:
            updates["deadline"] = parsed
    if updates:
        existing = existing.model_copy(update=updates)
        return session.put_request(existing)
    return existing


@tool
@safe_tool("calculate_schedule")
def calculate_schedule(
    request_id: str,
    work_items: list[dict[str, Any]] | None = None,
    deadline: str | None = None,
    allow_extra_cost: bool = False,
) -> dict:
    """Deterministically schedule the requested work against current capacity and dependencies.

    Do not estimate dates yourself. Call this after gathering evidence.

    Args:
        request_id: Id of the parsed request (req_...).
        work_items: Optional work-item dicts if not already stored.
        deadline: Optional ISO date override.
        allow_extra_cost: Unused in P0; extra cost is modeled as an alternative.
    """
    del allow_extra_cost
    request = _upsert_request(request_id, work_items, deadline)
    if request is None:
        return fail("INVALID_INPUT", f"unknown request_id {request_id}")
    session = current_session()
    schedule = domain_calculate_schedule(session.world, request)
    session.schedules[request.id] = schedule
    return ok(**dump(schedule))


@tool
@safe_tool("check_conflicts")
def check_conflicts(
    request_id: str,
    schedule: dict[str, Any] | None = None,
) -> dict:
    """Detect capacity, commitment, dependency, and supplier conflicts.

    Creates Evidence records and returns their ids on each conflict.
    Omit schedule to recompute from the stored request.

    Args:
        request_id: Id of the parsed request.
        schedule: Optional previously computed schedule payload.
    """
    session = current_session()
    request = _request_from_session(request_id)
    if request is None:
        return fail("INVALID_INPUT", f"unknown request_id {request_id}")
    computed = session.schedules.get(request_id)
    if schedule is not None:
        computed = ScheduleResult.model_validate(schedule)
    if computed is None:
        computed = domain_calculate_schedule(session.world, request)
        session.schedules[request_id] = computed
    evidence = gather_assessment_evidence(session.world, request, computed)
    session.add_evidence(evidence)
    conflicts = detect_conflicts(session.world, request, computed, evidence)
    return ok(conflicts=[dump(item) for item in conflicts])


@tool
@safe_tool("find_alternatives")
def find_alternatives(
    request_id: str,
    kinds: list[str] | None = None,
) -> dict:
    """Return scored alternatives when the requested promise is not safe.

    Default set: later date at no extra cost, extra resource, smallest scope cut.
    Feasibility of each option is computed by the domain engine.

    Args:
        request_id: Id of the parsed request.
        kinds: Optional filter (later_date, extra_resource, reduced_scope, ...).
    """
    session = current_session()
    request = _request_from_session(request_id)
    if request is None:
        return fail("INVALID_INPUT", f"unknown request_id {request_id}")
    schedule = session.schedules.get(request_id)
    if schedule is None:
        schedule = domain_calculate_schedule(session.world, request)
        session.schedules[request_id] = schedule
    alternatives = domain_find_alternatives(session.world, request, schedule)
    if kinds:
        allowed = set(kinds)
        alternatives = [item for item in alternatives if item.kind in allowed]
    return ok(alternatives=[dump(item) for item in alternatives])
