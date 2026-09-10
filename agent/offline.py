"""Recorded investigation path: same tools, no LLM.

Used by tests and as a Bedrock-free replay of the Acme loop.
"""

from __future__ import annotations

from agent.session import AgentSession, use_session
from agent.tools import (
    calculate_schedule,
    check_conflicts,
    find_alternatives,
    get_calendar,
    get_capacity,
    get_commitments,
    get_dependencies,
    get_supplier_status,
    search_email,
)
from agent.verify import verify_assessment, verify_reassessment
from domain.fixtures import acme_campaign_request
from domain.ids import new_id
from domain.models import FeasibilityAssessment, ParsedRequest
from domain.reassess import apply_reassessment


def run_recorded_investigation(
    session: AgentSession,
    request: ParsedRequest | None = None,
) -> FeasibilityAssessment:
    request = request or acme_campaign_request()
    with use_session(session):
        session.put_request(request)
        get_commitments()
        get_capacity(
            from_date="2026-09-12",
            to_date="2026-09-22",
            skills=["design", "video", "development"],
        )
        get_supplier_status(kind="video_editor")
        get_dependencies(
            client_id=request.customer_id,
            work_item_ids=[item.id for item in request.work_items],
        )
        search_email(query=request.customer_name)
        get_calendar(from_date="2026-09-12", to_date="2026-09-22")
        calculate_schedule(request_id=request.id)
        check_conflicts(request_id=request.id)
        find_alternatives(request_id=request.id)
        proposed = FeasibilityAssessment(
            id=new_id("asm"),
            request_id=request.id,
            decision="UNKNOWN",
            confidence=0.0,
            reasons=[],
            evidence=[],
            constraints=[],
            alternatives=[],
            required_human_decision=True,
            created_at=session.world.clock.now,
        )
        assessment = verify_assessment(proposed, session.world, request, session)
        return session.put_assessment(assessment)


def run_recorded_reassessment(
    session: AgentSession,
    commitment_id: str,
    event_id: str | None = None,
) -> FeasibilityAssessment:
    commitment = next(item for item in session.world.commitments if item.id == commitment_id)
    request = session.requests.get(commitment.request_id)
    if request is None and commitment.request_id == "req_acme_001":
        request = session.put_request(acme_campaign_request())
    if request is None:
        raise ValueError(f"no stored request for commitment {commitment_id}")
    del event_id
    with use_session(session):
        session.put_request(request)
        get_supplier_status(kind="video_editor")
        search_email(query="availability")
        get_dependencies(
            client_id=request.customer_id,
            work_item_ids=[item.id for item in commitment.work_items],
        )
        calculate_schedule(
            request_id=request.id,
            deadline=commitment.committed_deadline.isoformat(),
        )
        check_conflicts(request_id=request.id)
        find_alternatives(request_id=request.id)
        proposed = FeasibilityAssessment(
            id=new_id("asm"),
            request_id=request.id,
            decision="UNKNOWN",
            confidence=0.0,
            reasons=[],
            evidence=[],
            constraints=[],
            alternatives=[],
            required_human_decision=True,
            created_at=session.world.clock.now,
        )
        assessment = verify_reassessment(proposed, session.world, commitment, request, session)
        session.put_assessment(assessment)
        apply_reassessment(session.world, commitment, assessment)
        return assessment
