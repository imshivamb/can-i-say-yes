from datetime import date

from adapters.files.world import load_world
from agent.offline import run_recorded_investigation
from agent.session import AgentSession
from agent.verify import verify_assessment
from domain.fixtures import acme_campaign_request
from domain.models import FeasibilityAssessment, Money, Reason

REQUIRED_CODES = {
    "CAPACITY_OVERALLOCATED",
    "EXISTING_COMMITMENT",
    "MISSING_DEPENDENCY",
    "SUPPLIER_WINDOW",
}


def test_recorded_acme_investigation_is_unsafe() -> None:
    session = AgentSession(world=load_world())
    assessment = run_recorded_investigation(session)
    assert assessment.decision == "UNSAFE"
    codes = {item.code for item in assessment.constraints}
    assert REQUIRED_CODES <= codes
    assert [item.id for item in assessment.alternatives] == ["alt_a", "alt_b", "alt_c"]
    assert next(item for item in assessment.alternatives if item.recommended).id == "alt_a"
    known = {item.id for item in assessment.evidence}
    for reason in assessment.reasons:
        if reason.conflict_code in REQUIRED_CODES:
            assert reason.evidence_ids
            assert all(eid in known for eid in reason.evidence_ids)


def test_verify_rejects_unsupported_safe() -> None:
    session = AgentSession(world=load_world())
    request = acme_campaign_request()
    session.put_request(request)
    proposed = FeasibilityAssessment(
        id="asm_bad",
        request_id=request.id,
        decision="SAFE",
        confidence=0.99,
        reasons=[
            Reason(
                id="rsn_fake",
                title="Looks fine",
                detail="I guessed",
                severity="low",
                evidence_ids=[],
            )
        ],
        evidence=[],
        constraints=[],
        alternatives=[],
        required_human_decision=False,
        created_at=session.world.clock.now,
    )
    verified = verify_assessment(proposed, session.world, request, session)
    assert verified.decision == "UNSAFE"
    assert verified.required_human_decision is True
    assert any(item.id == "alt_a" and item.recommended for item in verified.alternatives)
    assert any(item.extra_cost == Money(amount=18000) for item in verified.alternatives)
    assert verified.forecast_end is None or verified.forecast_end >= date(2026, 9, 18)
