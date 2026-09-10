from __future__ import annotations

from datetime import date

from agent.session import AgentSession, use_session
from agent.tools.writes import (
    create_commitment,
    monitor_commitment,
    request_human_decision,
    send_customer_message,
)
from domain.ids import new_id
from domain.models import AuditRecord, FeasibilityAssessment, HumanDecision
from domain.state_machine import transition_decision

CUSTOMER_EMAILS = {
    "cli_acme": "priya@acmefoods.example",
    "cli_nova": "ops@novahealth.example",
}


def approve_decision(
    session: AgentSession,
    decision_id: str,
    option_id: str,
    actor: str = "human",
) -> HumanDecision:
    decision = session.decisions[decision_id]
    option_ids = {item.id for item in decision.options}
    if option_id not in option_ids:
        raise ValueError(f"unknown option_id {option_id}")
    if decision.status == "APPROVED":
        if decision.chosen_option_id != option_id:
            raise ValueError("decision is already approved with another option")
        return decision
    updated = decision.model_copy(
        update={
            "status": transition_decision(decision.status, "APPROVED"),
            "chosen_option_id": option_id,
            "actor": actor,
        }
    )
    session.decisions[decision_id] = updated
    session.record_audit(
        AuditRecord(
            id=new_id("aud"),
            timestamp=session.world.clock.now,
            actor=actor,
            arguments={"decision_id": decision_id, "option_id": option_id},
            result_status="success",
            authorization="allow",
            request_id=updated.request_id,
        )
    )
    session.persist()
    return updated


def reject_decision(
    session: AgentSession,
    decision_id: str,
    actor: str = "human",
) -> HumanDecision:
    decision = session.decisions[decision_id]
    updated = decision.model_copy(
        update={
            "status": transition_decision(decision.status, "REJECTED"),
            "actor": actor,
        }
    )
    session.decisions[decision_id] = updated
    session.record_audit(
        AuditRecord(
            id=new_id("aud"),
            timestamp=session.world.clock.now,
            actor=actor,
            arguments={"decision_id": decision_id},
            result_status="success",
            authorization="allow",
            request_id=updated.request_id,
        )
    )
    session.persist()
    return updated


def open_decision(
    session: AgentSession,
    assessment: FeasibilityAssessment,
    reason: str,
    commitment_id: str | None = None,
) -> HumanDecision:
    session.put_assessment(assessment)
    recommended = next((item.id for item in assessment.alternatives if item.recommended), None)
    with use_session(session):
        result = request_human_decision(
            assessment_id=assessment.id,
            reason=reason,
            recommended_option_id=recommended,
            request_id=assessment.request_id,
            commitment_id=commitment_id,
        )
    if not result["ok"]:
        raise RuntimeError(result["message"])
    return session.decisions[result["decision"]["id"]]


def fulfill_approved_option(session: AgentSession, decision_id: str) -> HumanDecision:
    """Create, monitor, and queue the customer message for an already-approved decision."""
    decision = session.decisions[decision_id]
    if decision.status != "APPROVED" or not decision.chosen_option_id or not decision.request_id:
        raise ValueError("decision is not approved with a chosen option")
    if decision.commitment_id and any(
        item.id == decision.commitment_id for item in session.commitments()
    ):
        return decision
    if decision.assessment_id is None:
        raise ValueError("decision has no assessment_id")
    assessment = session.assessments[decision.assessment_id]
    request = session.requests[decision.request_id]
    alternative = next(
        item for item in assessment.alternatives if item.id == decision.chosen_option_id
    )
    with use_session(session):
        created = create_commitment(
            request_id=decision.request_id,
            assessment_id=assessment.id,
            decision_id=decision.id,
            alternative_id=decision.chosen_option_id,
        )
        if not created["ok"]:
            raise RuntimeError(created["message"])
        commitment_id = created["commitment_id"]
        watched = monitor_commitment(commitment_id=commitment_id)
        if not watched["ok"]:
            raise RuntimeError(watched["message"])
        message = send_customer_message(
            commitment_id=commitment_id,
            to=CUSTOMER_EMAILS.get(request.customer_id or "", "founder@northstar.example"),
            subject=f"Northstar: delivery plan for {request.customer_name}",
            body=_approved_terms_body(
                request.scope_summary,
                alternative.new_deadline,
                alternative.extra_cost.amount,
            ),
            decision_id=decision.id,
        )
        if not message["ok"]:
            raise RuntimeError(message["message"])
    return session.decisions[decision_id]


def _approved_terms_body(scope_summary: str, deadline: date | None, extra_cost: int) -> str:
    when = deadline.strftime("%d %B %Y") if deadline else "the approved date"
    if extra_cost == 0:
        cost = "There is no extra cost (₹0)."
    else:
        cost = f"Extra cost is ₹{extra_cost:,}."
    return (
        f"We can deliver the {scope_summary} by {when}. {cost}"
    )
